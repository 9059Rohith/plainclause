"""Measure lexical fallback on synthetic long-document sections."""
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.rag import retrieve_hybrid  # noqa: E402


def main() -> None:
    chunks = []
    for index in range(400):
        passage = (f"Section {index}. The parties shall maintain records for schedule {index} "
                   "and submit written reports each quarter. ") * 5
        if index == 317:
            passage = "The customer must pay $275 each month. " + passage
        chunks.append({"id": str(index), "heading": f"Clause {index}", "text": passage})

    results = []
    for question in ("What is the monthly payment?", "How much must the customer pay each month?"):
        samples = []
        hits = []
        for _ in range(5):
            started = time.perf_counter()
            hits = retrieve_hybrid(chunks, question, None, {})
            samples.append((time.perf_counter() - started) * 1000)
        results.append({"question": question, "sections": len(chunks), "runs": len(samples),
                        "median_ms": round(statistics.median(samples), 2),
                        "top_id": hits[0]["id"] if hits else None})
    print(json.dumps(results))


if __name__ == "__main__":
    main()
