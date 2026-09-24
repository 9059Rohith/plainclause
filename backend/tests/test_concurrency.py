"""Concurrent local workspaces must not mix source passages or metadata."""
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import create_app


def test_eight_concurrent_uploads_stay_in_their_own_sessions(tmp_path, monkeypatch):
    async def no_model():
        return False

    monkeypatch.setattr("app.main.available", no_model)
    app = create_app(tmp_path / "concurrent.db")
    clients = [TestClient(app) for _ in range(8)]
    headers = {"X-Requested-With": "Plainclause"}

    def upload_and_ask(item):
        index, client = item
        marker = f"PRIVATE_MARKER_{index}"
        content = f"1. Payment\nCustomer {marker} must pay ${100 + index} each month.".encode()
        uploaded = client.post("/api/documents", files={"file": (f"terms-{index}.txt", content, "text/plain")}, headers=headers)
        assert uploaded.status_code == 200, uploaded.text
        document_id = uploaded.json()["id"]
        answer = client.post("/api/ask", json={"document_id": document_id, "question": "What payment is due?"}, headers=headers)
        assert answer.status_code == 200, answer.text
        assert marker in answer.json()["citations"][0]["quote"]
        return document_id

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(upload_and_ask, enumerate(clients)))

    assert len(set(ids)) == len(clients)
    for index, client in enumerate(clients):
        assert [row["id"] for row in client.get("/api/documents").json()] == [ids[index]]
        assert client.get(f"/api/documents/{ids[(index + 1) % len(ids)]}").status_code == 404
