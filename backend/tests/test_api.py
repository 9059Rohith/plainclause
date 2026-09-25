import json
import sqlite3
import base64

from fastapi.testclient import TestClient

from app.main import create_app
from app.storage import Store


def test_upload_scope_compare_and_delete(tmp_path, monkeypatch):
    async def no_model():
        return False
    monkeypatch.setattr("app.main.available", no_model)
    app = create_app(tmp_path / "test.db")
    a = TestClient(app)
    b = TestClient(app)
    headers = {"X-Requested-With": "Plainclause"}
    first = a.post("/api/documents", files={"file": ("lease.txt", b"1. Rent\nTenant must pay $1,200 each month.\n\n2. Termination\nEither party may terminate with 30 days notice.", "text/plain")}, headers=headers)
    assert first.status_code == 200, first.text
    doc_id = first.json()["id"]
    detail = a.get(f"/api/documents/{doc_id}")
    assert detail.status_code == 200
    assert any("Rent" in chunk["heading"] for chunk in detail.json()["chunks"])
    prep = a.get(f"/api/documents/{doc_id}/prepare").json()
    assert any("$1,200" in fact["excerpt"] and fact["source"] == "1. Rent" for fact in prep["facts"])
    assert any("tenant-rights" in resource for resource in prep["resources"])
    assert b.get(f"/api/documents/{doc_id}").status_code == 404
    answer = a.post("/api/ask", json={"document_id": doc_id, "question": "What is the rent payment?"}, headers=headers)
    assert answer.status_code == 200
    assert answer.json()["citations"][0]["heading"] == "1. Rent"
    urgent = a.post("/api/ask", json={"document_id": doc_id, "question": "What is my court date?"}, headers=headers)
    assert "licensed attorney" in urgent.json()["professional_note"]
    for question in ("My visa expires tomorrow; what happens?", "Could foreclosure affect this?", "What if I am arrested?"):
        urgent_variant = a.post("/api/ask", json={"document_id": doc_id, "question": question}, headers=headers)
        assert "licensed attorney" in urgent_variant.json()["professional_note"]
    assert a.post("/api/compare", json={"document_ids": [doc_id, doc_id]}, headers=headers).status_code == 422
    assert a.delete("/api/data", headers=headers).status_code == 200
    assert a.get(f"/api/documents/{doc_id}").status_code == 404


def test_index_history_and_deletion_are_session_scoped(tmp_path, monkeypatch):
    async def fake_embed(texts):
        return [[float(len(text)), 1.0] for text in texts]
    async def no_model():
        return False
    monkeypatch.setattr("app.main.embed", fake_embed)
    monkeypatch.setattr("app.main.available", no_model)
    path = tmp_path / "indexed.db"
    app = create_app(path)
    a, b = TestClient(app), TestClient(app)
    headers = {"X-Requested-With": "Plainclause"}
    text = b"1. Payment\nCustomer must pay $250 each month.\n2. Ending\nEither party may end with 20 days written notice."
    doc_id = a.post("/api/documents", files={"file": ("terms.txt", text, "text/plain")}, headers=headers).json()["id"]
    assert b.get(f"/api/documents/{doc_id}/index").status_code == 404
    indexed = a.post(f"/api/documents/{doc_id}/index?offset=0", headers=headers)
    assert indexed.status_code == 200, indexed.text
    assert indexed.json()["indexed"] == indexed.json()["total"] == 2
    assert a.post(f"/api/documents/{doc_id}/index?offset=0", headers=headers).json()["indexed"] == 2
    assert a.get(f"/api/documents/{doc_id}/history").json() == []
    answer = a.post("/api/ask", json={"document_id": doc_id, "question": "What payment is due?"}, headers=headers)
    assert answer.status_code == 200, answer.text
    history = a.get(f"/api/documents/{doc_id}/history").json()
    assert len(history) == 1 and history[0]["answer"]["citations"]
    assert b.get(f"/api/documents/{doc_id}/history").status_code == 404
    assert b.get(f"/api/documents/{doc_id}/summaries").status_code == 404
    with sqlite3.connect(path) as db:
        event = db.execute("SELECT operation,chunk_ids,status FROM audit_events").fetchone()
        assert event and event[0] == "ask"
        assert "What payment" not in str(event) and "Customer must" not in str(event)
    assert a.delete("/api/data", headers=headers).json()["deleted_documents"] == 1
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM summaries").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 0
    assert b"Customer must pay $250" not in path.read_bytes()


def test_streaming_withholds_draft_until_grounded_result(tmp_path, monkeypatch):
    async def model_ready():
        return True
    async def fake_stream(question, passages):
        yield {"type": "progress", "characters": 15}
        yield {"type": "complete", "output": {"answer": "The payment is $250 each month.", "citation_ids": [passages[0]["id"]]}}
    monkeypatch.setattr("app.main.available", model_ready)
    monkeypatch.setattr("app.main.generate_stream", fake_stream)
    client = TestClient(create_app(tmp_path / "stream.db"))
    headers = {"X-Requested-With": "Plainclause"}
    doc_id = client.post("/api/documents", files={"file": ("payment.txt", b"1. Payment\nCustomer must pay $250 each month.", "text/plain")}, headers=headers).json()["id"]
    response = client.post("/api/ask/stream", json={"document_id": doc_id, "question": "What payment is due?"}, headers=headers)
    events = [json.loads(line) for line in response.text.splitlines()]
    assert response.status_code == 200
    assert all("The payment" not in json.dumps(event) for event in events[:-1])
    assert events[-1]["type"] == "result"
    assert events[-1]["answer"]["status"] == "answered"
    assert len(client.get(f"/api/documents/{doc_id}/history").json()) == 1
    async def must_not_generate(question, passages):
        raise AssertionError("A verified repeated answer should use the local cache")
        yield
    monkeypatch.setattr("app.main.generate_stream", must_not_generate)
    repeated = client.post("/api/ask/stream", json={"document_id": doc_id, "question": "What payment is due?"}, headers=headers)
    assert [json.loads(line) for line in repeated.text.splitlines()][-1]["answer"]["status"] == "answered"
    assert len(client.get(f"/api/documents/{doc_id}/history").json()) == 2
    async def bad_stream(question, passages):
        yield {"type": "progress", "characters": 80}
        yield {"type": "complete", "output": {"answer": "The payment is $9,999 each month.", "citation_ids": [passages[0]["id"]]}}
    monkeypatch.setattr("app.main.generate_stream", bad_stream)
    rejected = client.post("/api/ask/stream", json={"document_id": doc_id, "question": "How much must the customer pay each month?"}, headers=headers)
    rejected_events = [json.loads(line) for line in rejected.text.splitlines()]
    assert rejected_events[-1]["answer"]["status"] == "source_only"
    assert "$9,999" not in rejected.text


def test_upload_rejects_bad_pdf(tmp_path):
    a = TestClient(create_app(tmp_path / "test.db"))
    response = a.post("/api/documents", files={"file": ("bad.pdf", b"hello", "application/pdf")}, headers={"X-Requested-With": "Plainclause"})
    assert response.status_code == 422
    assert "valid PDF" in response.json()["detail"]
    mismatched = a.post("/api/documents", files={"file": ("terms.txt", b"This is an ordinary text agreement.", "image/png")}, headers={"X-Requested-With": "Plainclause"})
    assert mismatched.status_code == 422


def test_recent_document_order_is_stable_for_same_second_uploads(tmp_path):
    client = TestClient(create_app(tmp_path / "order.db"))
    headers = {"X-Requested-With": "Plainclause"}
    first = client.post("/api/documents", files={"file": ("first.txt", b"This is the first legal document with enough text.", "text/plain")}, headers=headers).json()["id"]
    second = client.post("/api/documents", files={"file": ("second.txt", b"This is the second legal document with enough text.", "text/plain")}, headers=headers).json()["id"]
    assert [item["id"] for item in client.get("/api/documents").json()] == [second, first]


def test_local_request_cap_and_workspace_reset(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.time.time", lambda: 1200.0)
    store = Store(tmp_path / "limits.db")
    assert [store.allow_request("session", "upload", 2) for _ in range(3)] == [True, True, False]
    store.delete_all("session")
    assert store.allow_request("session", "upload", 2)


def test_mutation_rejects_cross_origin_and_missing_client_header(tmp_path):
    client = TestClient(create_app(tmp_path / "csrf.db"))
    payload = {"file": ("terms.txt", b"This agreement requires payment every month.", "text/plain")}
    assert client.post("/api/documents", files=payload).status_code == 403
    headers = {"X-Requested-With": "Plainclause", "Origin": "https://example.invalid"}
    assert client.post("/api/documents", files=payload, headers=headers).status_code == 403
    headers = {"X-Requested-With": "Plainclause", "Sec-Fetch-Site": "cross-site"}
    assert client.post("/api/documents", files=payload, headers=headers).status_code == 403
    headers = {"X-Requested-With": "Plainclause", "Host": "public.example.test", "Origin": "https://public.example.test"}
    assert client.post("/api/documents", files=payload, headers=headers).status_code == 200


def test_optional_preview_password_protects_ui_and_api(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAINCLAUSE_ACCESS_PASSWORD", "preview-secret")
    client = TestClient(create_app(tmp_path / "preview.db"))
    assert client.get("/api/status").status_code == 401
    assert client.get("/api/status", headers={"Authorization": "Basic malformed"}).status_code == 401
    wrong = base64.b64encode(b"plainclause:wrong").decode()
    assert client.get("/api/status", headers={"Authorization": f"Basic {wrong}"}).status_code == 401
    valid = base64.b64encode(b"plainclause:preview-secret").decode()
    assert client.get("/api/status", headers={"Authorization": f"Basic {valid}"}).status_code == 200
    headers = {"Authorization": f"Basic {valid}", "X-Requested-With": "Plainclause"}
    upload = client.post("/api/documents", files={"file": ("terms.txt", b"1. Terms\nThe customer must pay rent each month.", "text/plain")}, headers=headers)
    assert upload.status_code == 200
    assert client.get(f"/api/documents/{upload.json()['id']}").status_code == 401
    assert client.get(f"/api/documents/{upload.json()['id']}", headers=headers).status_code == 200


def test_hosted_service_status_and_readiness(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAINCLAUSE_HOSTED_SERVICE", "1")

    async def ready_model():
        return True

    monkeypatch.setattr("app.main.available", ready_model)
    client = TestClient(create_app(tmp_path / "hosted.db"))
    response = client.get("/api/status")
    assert response.json()["hosted_service"] is True
    assert response.json()["hosted_preview"] is False
    assert "Secure" in response.headers["set-cookie"]
    assert client.get("/api/ready").json() == {"ready": True}

    async def unavailable_model():
        return False

    monkeypatch.setattr("app.main.available", unavailable_model)
    assert client.get("/api/ready").status_code == 503

    monkeypatch.setenv("PLAINCLAUSE_ACCESS_PASSWORD", "secret")
    protected_client = TestClient(create_app(tmp_path / "protected-hosted.db"))
    assert protected_client.get("/api/ready").status_code == 503
    assert protected_client.get("/api/status").status_code == 401


def test_large_financial_amount_prompts_professional_attention(tmp_path, monkeypatch):
    async def no_model():
        return False

    monkeypatch.setattr("app.main.available", no_model)
    client = TestClient(create_app(tmp_path / "high-value.db"))
    headers = {"X-Requested-With": "Plainclause"}
    document_id = client.post("/api/documents", files={"file": ("sale.txt", b"1. Purchase price\nThe buyer agrees to pay $250,000 for the property.", "text/plain")}, headers=headers).json()["id"]
    answer = client.post("/api/ask", json={"document_id": document_id, "question": "What purchase price is stated?"}, headers=headers)
    assert answer.status_code == 200
    assert "licensed attorney" in answer.json()["professional_note"]


def test_summary_states_coverage_and_never_claims_unread_sections(tmp_path, monkeypatch):
    async def no_model():
        return False
    monkeypatch.setattr("app.main.available", no_model)
    client = TestClient(create_app(tmp_path / "summary.db"))
    headers = {"X-Requested-With": "Plainclause"}
    text = "\n\n".join(f"{i}. Clause {i}\nParty must review term {i} before signing." for i in range(1, 9))
    upload = client.post("/api/documents", files={"file": ("long.txt", text.encode(), "text/plain")}, headers=headers)
    assert upload.status_code == 200
    response = client.post(f"/api/documents/{upload.json()['id']}/summary", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result["coverage_count"] == 6
    assert result["total_sections"] == 8
    assert result["status"] == "source_only"
    assert "jurisdiction" in result["jurisdiction_note"].lower()
    assert len(result["uncited_headings"]) == 4
    remainder = client.post(f"/api/documents/{upload.json()['id']}/summary?offset=6", headers=headers)
    assert remainder.status_code == 200
    assert remainder.json()["coverage_count"] == 2
    assert remainder.json()["start_offset"] == 6
    saved = client.get(f"/api/documents/{upload.json()['id']}/summaries")
    assert [part["start_offset"] for part in saved.json()] == [0, 6]
    detailed = client.post(f"/api/documents/{upload.json()['id']}/summary?offset=0&level=detailed", headers=headers)
    assert detailed.json()["level"] == "detailed"
    assert [part["level"] for part in client.get(f"/api/documents/{upload.json()['id']}/summaries?level=detailed").json()] == ["detailed"]
    assert client.get(f"/api/documents/{upload.json()['id']}/summaries?level=simple").json() == []
    assert client.post(f"/api/documents/{upload.json()['id']}/summary?level=advanced", headers=headers).status_code == 422
