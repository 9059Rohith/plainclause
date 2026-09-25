"""Thin API for private, local document assistance."""
from pathlib import Path
import base64
import binascii
import hmac
import json
import os
import re
import secrets

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .analysis import analyze_chunk, compare_chunks
from .ingest import MAX_FILE_BYTES, Section, UploadError, parse_upload
from .model import EMBED_MODEL, available, embed, generate, generate_stream, masked_key, provider_name
from .rag import DISCLAIMER, grounded_answer, retrieve_hybrid
from .storage import Store

DATA_PATH = Path(os.getenv("PLAINCLAUSE_DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "plainclause.db")))
HIGH_STAKES = re.compile(r"\b(?:criminal|arrest\w*|court date|hearing|lawsuit|litigation|deport\w*|visa expir\w*|immigration deadline|evict\w*|foreclos\w*|bankrupt\w*|life savings|large (?:amount|sum)|significant debt|high financial stakes|six figures|million\w*)\b", re.I)
LARGE_CURRENCY_AMOUNT = re.compile(r"[$£€]\s*(\d[\d,]*(?:\.\d{1,2})?)")


def needs_professional_attention(text: str) -> bool:
    if HIGH_STAKES.search(text):
        return True
    return any(float(match.group(1).replace(",", "")) >= 100_000 for match in LARGE_CURRENCY_AMOUNT.finditer(text))


class AskRequest(BaseModel):
    document_id: str
    question: str = Field(min_length=4, max_length=1000)


class CompareRequest(BaseModel):
    document_ids: list[str] = Field(min_length=2, max_length=5)


class SimplifyRequest(BaseModel):
    chunk_id: str
    level: str = Field(pattern="^(simple|detailed)$")


def create_app(db_path: Path = DATA_PATH) -> FastAPI:
    app = FastAPI(title="Plainclause local API", docs_url=None, redoc_url=None)
    store = Store(db_path)
    access_password = os.getenv("PLAINCLAUSE_ACCESS_PASSWORD", "")
    hosted_preview = os.getenv("PLAINCLAUSE_HOSTED_PREVIEW") == "1"
    hosted_service = os.getenv("PLAINCLAUSE_HOSTED_SERVICE") == "1"

    @app.middleware("http")
    async def session_and_security(request: Request, call_next):
        if access_password and request.url.path != "/api/ready":
            authorization = request.headers.get("authorization", "")
            try:
                scheme, encoded = authorization.split(" ", 1)
                credentials = base64.b64decode(encoded, validate=True).decode("utf-8") if scheme.lower() == "basic" else ""
                username, supplied_password = credentials.split(":", 1)
            except (ValueError, UnicodeDecodeError, binascii.Error):
                username, supplied_password = "", ""
            if not (hmac.compare_digest(username, "plainclause") and hmac.compare_digest(supplied_password, access_password)):
                return JSONResponse({"detail": "Preview access requires a password."}, status_code=401,
                                    headers={"WWW-Authenticate": 'Basic realm="Plainclause preview"', "Cache-Control": "no-store"})
        token = request.cookies.get("pc_session", "")
        if not re.fullmatch(r"[a-f0-9]{64}", token):
            token = secrets.token_hex(32)
        request.state.session = token
        if request.url.path.startswith("/api/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if request.headers.get("x-requested-with") != "Plainclause":
                return JSONResponse({"detail": "This request needs the Plainclause client header."}, status_code=403)
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "Cross-site requests are blocked."}, status_code=403)
            origin = request.headers.get("origin")
            host = request.headers.get("host", "")
            if origin and origin not in {f"{request.url.scheme}://{host}", f"https://{host}"}:
                return JSONResponse({"detail": "Cross-origin requests are blocked."}, status_code=403)
            if request.url.path == "/api/documents" and not request.headers.get("content-length"):
                return JSONResponse({"detail": "Upload requests require a known size."}, status_code=411)
            try:
                if int(request.headers.get("content-length", "0")) > MAX_FILE_BYTES + 200_000:
                    return JSONResponse({"detail": "Request exceeds the 10 MB file limit."}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "Invalid request size."}, status_code=400)
            kind = "upload" if request.url.path == "/api/documents" else "index" if request.url.path.endswith("/index") else "generation" if any(part in request.url.path for part in ("/ask", "/summary", "/simplify")) else "mutation"
            cap = {"upload": 12, "index": 120, "generation": 60, "mutation": 120}[kind]
            if not store.allow_request(token, kind, cap):
                return JSONResponse({"detail": "Too many local requests. Try again in about a minute."}, status_code=429)
        response = await call_next(request)
        if request.cookies.get("pc_session") != token:
            response.set_cookie("pc_session", token, httponly=True, samesite="strict",
                                secure=request.url.scheme == "https" or hosted_preview or hosted_service,
                                max_age=60 * 60 * 24 * 30)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        if request.url.scheme == "https" or hosted_preview or hosted_service:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

    def document(request: Request, document_id: str) -> dict:
        found = store.get(request.state.session, document_id)
        if not found:
            raise HTTPException(404, "Document not found in this workspace.")
        return found

    @app.get("/api/status")
    async def status():
        return {"model_available": await available(), "model": provider_name(),
                "provider_key": masked_key(), "disclaimer": DISCLAIMER,
                "hosted_preview": hosted_preview, "hosted_service": hosted_service}

    @app.get("/api/ready")
    async def ready():
        if not await available():
            raise HTTPException(503, "The local AI model is not ready.")
        return {"ready": True}

    @app.get("/api/documents")
    async def documents(request: Request):
        return store.list(request.state.session)

    @app.post("/api/documents")
    async def upload(request: Request, file: UploadFile = File(...)):
        name = Path(file.filename or "").name[:180]
        if not name:
            raise HTTPException(422, "Choose a file to upload.")
        suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        allowed_mime = {
            "pdf": {"application/pdf", "application/octet-stream"},
            "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"},
            "txt": {"text/plain", "application/octet-stream"},
        }
        content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
        if suffix not in allowed_mime or content_type not in allowed_mime[suffix]:
            raise HTTPException(422, "File type and content type do not match PDF, DOCX, or TXT.")
        data = await file.read(MAX_FILE_BYTES + 1)
        await file.close()
        try:
            sections = await run_in_threadpool(parse_upload, name, data)
        except UploadError as exc:
            raise HTTPException(422, str(exc)) from exc
        document_id = store.add(request.state.session, name, name.rsplit(".", 1)[-1].lower(), sections)
        return {"id": document_id, "name": name, "section_count": len(sections)}

    @app.get("/api/documents/{document_id}")
    async def get_document(request: Request, document_id: str):
        found = document(request, document_id)
        found["chunks"] = [{**chunk, **analyze_chunk(chunk["text"])} for chunk in found["chunks"]]
        return found

    @app.get("/api/documents/{document_id}/index")
    async def index_status(request: Request, document_id: str):
        found = document(request, document_id)
        return {"indexed": len(store.vectors(request.state.session, document_id, EMBED_MODEL)),
                "total": len(found["chunks"]), "model": EMBED_MODEL}

    @app.post("/api/documents/{document_id}/index")
    async def index_document(request: Request, document_id: str, offset: int = Query(default=0, ge=0)):
        document(request, document_id)
        total, batch = store.index_batch(request.state.session, document_id, EMBED_MODEL, offset)
        if offset >= total:
            return {"processed": total, "total": total, "indexed": total}
        missing = [row for row in batch if row['vector'] is None]
        if missing:
            vectors = await embed([f"{row['heading']}\n{row['text']}" for row in missing])
            if vectors is None:
                raise HTTPException(503, "The local embedding model is unavailable. Run: ollama pull all-minilm")
            store.save_embeddings(request.state.session, document_id, EMBED_MODEL,
                                  [(row['id'], vector) for row, vector in zip(missing, vectors)])
        return {"processed": min(offset + len(batch), total), "total": total,
                "indexed": len(store.vectors(request.state.session, document_id, EMBED_MODEL))}

    @app.get("/api/documents/{document_id}/history")
    async def history(request: Request, document_id: str):
        document(request, document_id)
        return store.history(request.state.session, document_id)

    @app.delete("/api/documents/{document_id}")
    async def delete_document(request: Request, document_id: str):
        if not store.delete(request.state.session, document_id):
            raise HTTPException(404, "Document not found in this workspace.")
        return {"deleted": True}

    @app.delete("/api/data")
    async def delete_all(request: Request):
        return {"deleted_documents": store.delete_all(request.state.session)}

    @app.post("/api/ask")
    async def ask(request: Request, body: AskRequest):
        found = document(request, body.document_id)
        cached = store.cached_answer(request.state.session, body.document_id, body.question)
        if cached:
            store.add_message(request.state.session, body.document_id, body.question, cached)
            store.log_event(request.state.session, body.document_id, "ask_cached", [citation['id'] for citation in cached['citations']], cached['status'])
            return cached
        indexed = store.vectors(request.state.session, body.document_id, EMBED_MODEL)
        query_vector = (await embed([body.question]) or [None])[0] if indexed else None
        hits = retrieve_hybrid(found["chunks"], body.question, query_vector, indexed)
        output = await generate(body.question, hits) if hits and await available() else None
        result = answer_with_notes(body.question, hits, output)
        store.add_message(request.state.session, body.document_id, body.question, result)
        store.log_event(request.state.session, body.document_id, "ask", [hit['id'] for hit in hits], result['status'])
        return result

    def answer_with_notes(question: str, hits: list[dict], output: dict | None) -> dict:
        result = grounded_answer(question, hits, output)
        if needs_professional_attention(question + " " + " ".join(hit['text'] for hit in hits)):
            result["professional_note"] = "This may be time-sensitive or high stakes. Consider speaking with a licensed attorney promptly."
        result["jurisdiction_note"] = "Legal meaning can vary by jurisdiction; this document alone may not establish the applicable law."
        return result

    @app.post("/api/ask/stream")
    async def ask_stream(request: Request, body: AskRequest):
        found = document(request, body.document_id)

        async def events():
            yield json.dumps({"type": "status", "message": "Finding source passages"}) + "\n"
            cached = store.cached_answer(request.state.session, body.document_id, body.question)
            if cached:
                store.add_message(request.state.session, body.document_id, body.question, cached)
                store.log_event(request.state.session, body.document_id, "ask_cached", [citation['id'] for citation in cached['citations']], cached['status'])
                yield json.dumps({"type": "result", "answer": cached}) + "\n"
                return
            indexed = store.vectors(request.state.session, body.document_id, EMBED_MODEL)
            query_vector = (await embed([body.question]) or [None])[0] if indexed else None
            hits = retrieve_hybrid(found["chunks"], body.question, query_vector, indexed)
            output = None
            if hits and await available():
                yield json.dumps({"type": "status", "message": "Checking a local AI draft against the sources"}) + "\n"
                async for item in generate_stream(body.question, hits):
                    if item["type"] == "progress":
                        yield json.dumps({"type": "progress", "characters": item["characters"]}) + "\n"
                    elif item["type"] == "complete":
                        output = item["output"]
            result = answer_with_notes(body.question, hits, output)
            store.add_message(request.state.session, body.document_id, body.question, result)
            store.log_event(request.state.session, body.document_id, "ask_stream", [hit['id'] for hit in hits], result['status'])
            yield json.dumps({"type": "result", "answer": result}) + "\n"

        return StreamingResponse(events(), media_type="application/x-ndjson", headers={"X-Accel-Buffering": "no"})

    @app.post("/api/documents/{document_id}/summary")
    async def summary(request: Request, document_id: str, offset: int = Query(default=0, ge=0), level: str = Query(default="simple", pattern="^(simple|detailed)$")):
        found = document(request, document_id)
        if offset >= len(found["chunks"]):
            raise HTTPException(422, "No sections remain at this offset.")
        passages = found["chunks"][offset:offset + 6]
        reading_style = "brief, everyday language that a non-lawyer can scan" if level == "simple" else "careful plain language with more detail about conditions, exceptions, obligations, and rights"
        question = f"Summarize the supplied sections in {reading_style}. Include each material obligation, right, amount, and deadline visible in these sections. Do not claim to summarize sections that were not supplied. Note uncertainty and cite all substantive points."
        output = await generate(question, passages) if await available() else None
        result = answer_with_notes(question, passages, output)
        result["start_offset"] = offset
        result["coverage_count"] = len(passages)
        result["total_sections"] = len(found["chunks"])
        result["level"] = level
        cited_ids = {citation["id"] for citation in result["citations"]}
        result["uncited_headings"] = [passage["heading"] for passage in passages if passage["id"] not in cited_ids]
        store.save_summary(request.state.session, document_id, offset, result)
        store.log_event(request.state.session, document_id, "summary", [passage['id'] for passage in passages], result['status'])
        return result

    @app.get("/api/documents/{document_id}/summaries")
    async def summaries(request: Request, document_id: str, level: str = Query(default="simple", pattern="^(simple|detailed)$")):
        document(request, document_id)
        return store.summaries(request.state.session, document_id, level)

    @app.delete("/api/documents/{document_id}/summaries")
    async def clear_summaries(request: Request, document_id: str):
        document(request, document_id)
        store.clear_summaries(request.state.session, document_id)
        return {"deleted": True}

    @app.post("/api/documents/{document_id}/simplify")
    async def simplify(request: Request, document_id: str, body: SimplifyRequest):
        found = document(request, document_id)
        chunk = next((c for c in found["chunks"] if c["id"] == body.chunk_id), None)
        if not chunk:
            raise HTTPException(404, "Section not found in this document.")
        question = f"Explain this section in {'plain everyday language in 2-3 sentences' if body.level == 'simple' else 'careful plain language with obligations, rights, and uncertainties'}. Do not omit material obligations or rights."
        output = await generate(question, [chunk]) if await available() else None
        result = answer_with_notes(question, [chunk], output)
        result["section_id"] = chunk["id"]
        store.log_event(request.state.session, document_id, "simplify", [chunk['id']], result['status'])
        return result

    @app.post("/api/compare")
    async def compare(request: Request, body: CompareRequest):
        if len(set(body.document_ids)) != len(body.document_ids):
            raise HTTPException(422, "Choose different documents to compare.")
        docs = [document(request, doc_id) for doc_id in body.document_ids]
        base = [Section(c["heading"], c["text"], c["page"]) for c in docs[0]["chunks"]]
        return {"base": docs[0]["name"], "comparisons": [{"name": other["name"], "rows": compare_chunks(base, [Section(c["heading"], c["text"], c["page"]) for c in other["chunks"]])} for other in docs[1:]], "disclaimer": DISCLAIMER}

    @app.get("/api/documents/{document_id}/prepare")
    async def prepare(request: Request, document_id: str):
        found = document(request, document_id)
        review = []
        deadlines = []
        facts = []
        for chunk in found["chunks"]:
            signals = analyze_chunk(chunk["text"])
            if signals["categories"] and len(facts) < 12:
                facts.append({"source": chunk["heading"], "page": chunk["page"],
                              "excerpt": chunk["text"][:400], "chunk_id": chunk["id"]})
            for reason in signals["review_reasons"]:
                review.append({"question": f"How does {chunk['heading']} affect my situation? {reason}", "source": chunk["heading"], "chunk_id": chunk["id"]})
            for date in signals["deadlines"]:
                deadlines.append({"text": date, "source": chunk["heading"], "chunk_id": chunk["id"]})
        full_text = " ".join(chunk["text"] for chunk in found["chunks"]).lower()
        resources = ["A local legal-aid organization or licensed lawyer referral service may help you find professional advice in your jurisdiction."]
        if re.search(r"\b(tenant|landlord|lease|rent)\b", full_text):
            resources.append("A local tenant-rights or housing-support organization may offer general information about rental documents.")
        if re.search(r"\b(employee|employer|employment|wages?)\b", full_text):
            resources.append("A local worker-rights or employment-support organization may offer general information about work agreements.")
        return {"document": found["name"], "facts": facts, "questions": review, "deadlines": deadlines,
                "resources": resources,
                "checklist": ["Verify names, dates, amounts, and the final version with the other party.", "Read every obligation and exception in the original document.", "Ask for unclear terms or promises in writing.", "Bring the passages below and your goals to a licensed professional when stakes are high."],
                "disclaimer": DISCLAIMER}

    dist = Path(__file__).resolve().parents[2] / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")

    return app


app = create_app()
