"""Measure representative local API calls with synthetic text and an isolated DB.

Run: .venv/Scripts/python.exe scripts/measure_latency.py
The in-process TestClient excludes browser rendering and network latency.
"""

import json
import math
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import create_app  # noqa: E402


def measure(client: TestClient, method: str, path: str, repetitions: int, **kwargs):
    durations = []
    last = None
    for _ in range(repetitions):
        started = time.perf_counter()
        last = client.request(method, path, **kwargs)
        durations.append((time.perf_counter() - started) * 1000)
        last.raise_for_status()
    ordered = sorted(durations)
    return {
        "runs": repetitions,
        "median_ms": round(statistics.median(durations), 1),
        "p95_ms": round(ordered[math.ceil(0.95 * repetitions) - 1], 1),
        "min_ms": round(ordered[0], 1),
        "max_ms": round(ordered[-1], 1),
    }, last


def main():
    headers = {"X-Requested-With": "Plainclause"}
    first = (
        "1. Rent\nThe tenant pays $275 each month on the first day.\n\n"
        "2. Termination\nEither party may end the lease with 30 days written notice.\n\n"
        "3. Governing Law\nThe agreement is governed by local law.\n"
    )
    second = first.replace("$275", "$300").replace("30 days", "60 days")
    with tempfile.TemporaryDirectory(prefix="plainclause-latency-") as directory:
        with TestClient(create_app(Path(directory) / "latency.db")) as client:
            status = client.get("/api/status")
            status.raise_for_status()
            model_available = status.json()["model_available"]
            results = {}
            results["status"], _ = measure(client, "GET", "/api/status", 10)
            results["empty_list"], _ = measure(client, "GET", "/api/documents", 30)
            uploads = []
            ids = []
            for name, content in (("lease-a.txt", first), ("lease-b.txt", second)):
                started = time.perf_counter()
                response = client.post(
                    "/api/documents",
                    files={"file": (name, content.encode("utf-8"), "text/plain")},
                    headers=headers,
                )
                uploads.append(round((time.perf_counter() - started) * 1000, 1))
                response.raise_for_status()
                ids.append(response.json()["id"])
            results["upload_ms_each"] = uploads
            results["document_read"], _ = measure(client, "GET", f"/api/documents/{ids[0]}", 30)
            results["prepare"], _ = measure(client, "GET", f"/api/documents/{ids[0]}/prepare", 30)
            results["compare"], _ = measure(
                client, "POST", "/api/compare", 10,
                json={"document_ids": ids}, headers=headers,
            )
            if model_available:
                started = time.perf_counter()
                answer = client.post(
                    "/api/ask",
                    json={"document_id": ids[0], "question": "What is the monthly rent?"},
                    headers=headers,
                )
                results["first_model_answer_ms"] = round((time.perf_counter() - started) * 1000, 1)
                answer.raise_for_status()
                results["first_model_answer_status"] = answer.json()["status"]
            print(json.dumps({
                "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "platform": platform.platform(),
                "python": platform.python_version(),
                "method": "FastAPI TestClient in process; isolated SQLite; synthetic 3-section TXT files",
                "model_available": model_available,
                "results": results,
            }, indent=2))


if __name__ == "__main__":
    main()
