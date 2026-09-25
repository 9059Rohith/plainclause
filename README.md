# Plainclause

Plainclause is an AI-powered legal document assistant that simplifies, compares, analyzes, and explains legal information while helping users identify key clauses, risks, and next steps. It extracts PDF, DOCX, and UTF-8 TXT files; preserves clause headings and PDF page references; highlights terms worth reviewing; answers questions using passages from the selected document; compares clause wording across documents; and prepares a checklist and questions for a lawyer. It provides **legal information, not legal advice**.

## Features

- **Document Upload & Parsing** — PDF, DOCX, and TXT with structure-preserving extraction, clause boundaries, page references, and OCR for scanned PDFs
- **Plain-Language Explanations** — Simple and detailed reading levels for every section, with on-demand full-document overview
- **Source-Grounded Q&A** — Ask questions and get answers backed by cited passages from your document, with streaming progress
- **Smart Review Signals** — Automatic detection of clauses worth reviewing: auto-renewals, indemnification, liability caps, penalties, and more
- **Document Comparison** — Side-by-side clause comparison across 2–5 documents with highlighted money/period changes
- **Lawyer Preparation Sheet** — Source-linked checklist, questions, and talking points exportable as Markdown or PDF
- **Privacy-First Architecture** — Local processing by default with an explicit cloud provider opt-in; session-scoped SQLite storage with secure-delete
- **Hallucination Guardrails** — Citation-ID checks, numeric-claim verification, directive filtering, and source-only fallback

## Run locally

Requirements: Python 3.12 on Windows for the verified lockfile, Node.js 20+, and [Ollama](https://ollama.com/) for AI explanations. No account, API key, credit card, or paid service is required.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.lock.txt
npm install
ollama pull qwen2.5:1.5b
ollama pull all-minilm
npm run build
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. For frontend development, run `npm run dev` in another terminal and open <http://127.0.0.1:5173>; Vite proxies `/api` to port 8000. The backend serves the built UI from `dist` if present. Ollama must be running locally for generated explanations and semantic retrieval; precise-word retrieval and deterministic review/compare/prep still work if it is unavailable. `PLAINCLAUSE_MODEL` defaults to `qwen2.5:1.5b`, `PLAINCLAUSE_EMBED_MODEL` to `all-minilm`, and `PLAINCLAUSE_OLLAMA_URL` to `http://127.0.0.1:11434`. Model requests are restricted to loopback URLs.
If port 8000 is occupied, use `--port 8765` in the backend command and open <http://127.0.0.1:8765>.
`PLAINCLAUSE_DB_PATH` can point to a different local SQLite file; browser tests use an isolated file under `test-results`. `backend/requirements.lock.txt` records the 56-package Windows/Python 3.12 environment verified for this build; `backend/requirements.txt` lists supported package ranges for other setups.

Ollama is the default answer provider. To opt into cloud answers, set `PLAINCLAUSE_PROVIDER=openai` and `OPENAI_API_KEY` before starting the backend. In that mode, retrieved document excerpts and questions are sent to the configured OpenAI endpoint; the local-only privacy statements below apply only with the default Ollama provider. Embeddings remain local. The UI status reports provider availability, not the provider name.

## Temporary online preview

An optional `PLAINCLAUSE_ACCESS_PASSWORD` environment variable enables a Basic-auth password gate across the UI and API (username `plainclause`). The evaluation preview leaves this variable unset so evaluators can open the link directly; anyone who obtains the URL can therefore access the service. Set `PLAINCLAUSE_HOSTED_PREVIEW=1` to show the in-app tunnel/privacy notice and use Secure session cookies. The current preview runs the same backend and local Ollama model on this computer through an ngrok HTTPS tunnel; its URL changes or expires, and it only works while the computer, backend, and tunnel stay running. This is a test preview, not durable cloud hosting. Uploaded document traffic passes through ngrok before reaching this computer. Preview data uses an isolated SQLite database under `.runtime/`; `.runtime/` is ignored by Git. Delete your workspace data after testing. Do not treat a free tunnel as a production deployment or upload documents you cannot share with its tunnel provider. Ngrok may show first-time visitors a one-time safety page before the application.

## Railway deployment

The repository includes a Docker image and Railway configuration for a single service containing the frontend, FastAPI, and local Ollama models. The image sets `PLAINCLAUSE_HOSTED_SERVICE=1`; the app then describes hosted processing and storage accurately. The database path is `/data/plainclause.db`, so a persistent Railway volume must be mounted at `/data` before use. Railway checks `/api/ready` and only routes traffic when the model is available. See [Railway deployment steps and current status](docs/railway-deployment.md).

This deployment is **prepared but not live** as of 2026-09-25. Railway rejected project creation with `Free plan resource provision limit exceeded`; the workspace must be upgraded and a volume provisioned before the image can be built and verified remotely. The Docker image has not been built locally because the Docker Desktop engine is unavailable in this environment. Do not use the temporary tunnel as proof of a durable deployment.

## How it works

The FastAPI backend validates and extracts document text in memory. It stores extracted sections, local embeddings, saved summaries, Q&A history, and source-ID-only audit events in `backend/data/plainclause.db` (SQLite); original binary uploads are discarded. Numbered headings, numbered operative clauses, uppercase headings, and PDF page references form bounded sections; the full wording of a numbered sentence stays in its cited passage. Image-only PDF pages are transcribed with local RapidOCR ONNX models, and each OCR-derived section carries a verification notice. OCR is limited to 50 pages per file; unreadable pages are rejected instead of silently skipped. Clause categories, review signals, and date/period extraction use transparent text rules. These are prompts to review, not risk verdicts or legal conclusions.

After upload, the UI indexes sections in batches of 16 with the local `all-minilm` model and shows the actual indexed count. Vectors persist in SQLite and are reused. Question answering combines cosine similarity and TF-IDF term overlap to retrieve up to five sections from the selected document. If embeddings are unavailable, it falls back to precise-word retrieval. Retrieved sections, as untrusted data, are sent only to the local Ollama model with a separate system instruction. Obvious prompt-injection lines are removed from model context. A generated answer is accepted only if it names supplied passage IDs and does not introduce unsupported amounts/periods or certain definitive legal directives. Otherwise the app shows source passages without an AI interpretation. This is a conservative guardrail, not a formal proof of factual accuracy. Temperature is zero for consistency. Q&A streams status and model-output progress but withholds draft legal prose until the full response passes citation and directive checks. Answers and citations remain in document-specific history across refreshes.

The simple/detailed reading level applies to both section explanations and the document overview. Explanations are requested one section at a time so skipped clauses are visible rather than silently omitted. The on-demand overview processes six sections per model call, reports exact section progress, and can cover the whole document without sending it all in one context. Completed batches and the selected reading level persist across refreshes and can be resumed. It names sections that received no citation. If a batch cannot be verified, it stops and shows source passages; the UI marks remaining sections as unprocessed.

Comparison aligns sections by heading and reports added, removed, or modified text, highlighting exact money-amount and time-period changes. It does not determine legal materiality. The preparation sheet gathers rule-detected review signals and time expressions into source-linked questions, lets the user add goals and context, then offers Markdown and browser print/PDF export. Q&A and section explanations also export to Markdown.

The preparation sheet includes exact key passages and general types of local legal or community help where the document suggests a rental or employment context; it makes no claim that any particular service exists in the user's location.

Verified answers to exact repeated questions are reused from document-scoped history, avoiding another model call. Source-only and not-found responses are regenerated so a newly available model can still help.

## Privacy and security

The server binds to `127.0.0.1` in the documented local command; the Railway container binds to its assigned service port. A random 256-bit, HttpOnly, SameSite cookie scopes every document operation. The browser sends a custom request header on mutations, and the backend blocks cross-origin/cross-site requests. Session-scoped request caps bound uploads, indexing, and model calls. Document content is not logged; audit events contain only operation names, source IDs, and result status. With the default local setup, document content stays on the user's computer. A hosted evaluation deploy stores extracted content on the cloud provider's volume, and the temporary preview routes uploads through its tunnel provider. The Ollama model URL is restricted to numeric loopback addresses. The app applies a 10 MB upload limit, a 200-page PDF limit, a 50-page OCR limit, text and DOCX expansion limits, extension/MIME/content checks, active-PDF-content rejection, safe errors, and restrictive response headers. Delete my data removes all current-workspace rows, including sections, embeddings, summaries, Q&A history, audit events, and rate-limit counters, and clears saved prep goals in the current browser tab. SQLite secure-delete is enabled to overwrite deleted rows; disk snapshots and backups may retain older copies. If you clear the browser cookie without deleting, the old workspace becomes inaccessible; for sensitive use, delete data before clearing cookies. This is a single-user tool with session isolation, not a multi-user hosted authentication system.

## Legal-information policy

Generated interpretations carry a visible disclaimer and source excerpts. The app declines questions without retrieved evidence, cautions that legal meaning varies by jurisdiction, and highlights questions mentioning criminal exposure, litigation, immigration deadlines, eviction, foreclosure, bankruptcy, or clearly large financial amounts for prompt professional help. It does not verify statutes or case law. A licensed attorney can assess the full document and your circumstances.

## Tests and checks

See the [current submission report](docs/submission-report-2026-09-25.md), [engineering and design review](docs/quality-gate.md), and [evaluation snapshot](docs/evaluation-2026-09-16.md) for verification evidence and known limits.
On the documented Windows setup, `scripts/verify.ps1` runs the core checks in sequence.

```powershell
$env:PYTHONPATH='backend'; python -m pytest backend/tests -q
npm run typecheck
npm run lint
npm run build
npm run test:e2e
npm audit --audit-level=high
python -m pip_audit -r backend/requirements.lock.txt --no-deps --disable-pip
```

`pip_audit` requires the separate free `pip-audit` package; if it is not installed, run `python -m pip install pip-audit`. Browser tests start a temporary backend on port 8766 and require Google Chrome because the Playwright config uses its installed `chrome` channel. Tests cover parsing boundaries, OCR, a 200-page PDF, lease/NDA/ToS retrieval, classification and deadlines, prompt-injection filtering, grounded retrieval, comparison, session isolation, persisted index/history/summary deletion, streamed answer validation, and invalid uploads.

## Limits and troubleshooting

- English documents are supported. OCR quality varies with scan clarity; verify every name, number, date, and clause against the original scan. PDFs with more than 50 scanned pages need splitting.
- Heading detection and review signals are heuristic. Unusual layouts, tables, or phrasing can be missed. The original text remains visible.
- Semantic search improves synonym matching, but can still retrieve the wrong passage or miss context across distant clauses. Ask precise questions and check all cited text.
- The 1.5B local model can misinterpret legal language. Even cited output needs human review. When Ollama is missing, the app shows sourced text instead of pretending to explain it.
- This repository has automated and live-model checks, but no independent licensed-attorney review of explanations or review signals. It is not validated for professional legal use or public multi-user deployment.
- Long-document overview generation can take many minutes because every six sections require a separate local model call. The app reports and saves batch progress, lets you stop after the current batch, and resumes completed batches after refresh; review any remaining sections individually.
- For a PDF parsing error, verify that the file opens normally, is not encrypted, and has no active content. For model unavailability, run `ollama list`, pull both configured models, and confirm Ollama is running on port 11434.
- The documented local workspace should not be exposed directly to a public network. The ungated evaluation tunnel above is a temporary preview; it has session isolation and basic per-session request caps, but no account authentication or network-wide abuse protection suitable for public production use.

Comparison and preparation UI modules load on demand. Long section lists use browser content-visibility to avoid laying out off-screen rows, and document-list search is debounced.

## Architecture

`src/` contains the React/Vite interface and export helpers. `backend/app/ingest.py` parses, OCRs, and chunks documents, `analysis.py` produces review signals and comparison rows, `rag.py` retrieves and checks answer grounding, `model.py` talks to local Ollama, `storage.py` owns SQLite, and `main.py` exposes validated API routes. The default local setup runs on the user's computer without billing activation; the optional Railway image runs those same components on paid cloud infrastructure.

## License

MIT
