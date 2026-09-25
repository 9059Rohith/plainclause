# Local latency measurement — 2026-09-25

## Method

Ran `.venv\Scripts\python.exe scripts/measure_latency.py` on Windows 11 (build 26200), Python 3.12, Intel Core Ultra 7 155H (16 cores, 22 logical processors), 31.4 GB RAM. The script creates a fresh temporary SQLite database, uses two synthetic three-section TXT agreements, and calls the real FastAPI app through its in-process `TestClient`. Local Ollama was already running with `qwen2.5:1.5b`; the first answer was uncached and returned `answered`. The temporary database was removed successfully after the SQLite connection-lifecycle fix.

The values below are wall-clock times measured around each request. `p95` is the nearest-rank value in each small sample. The measurement excludes network transport, browser rendering, PDF/DOCX/OCR cost, cold model download/startup, concurrent public traffic, and hosted infrastructure. It is **not** a production latency guarantee or load benchmark.

| Operation | Runs | Median | p95 | Min–max |
| --- | ---: | ---: | ---: | ---: |
| `GET /api/status` including provider probe | 10 | 30.2 ms | 63.0 ms | 23.4–63.0 ms |
| `GET /api/documents` empty session | 30 | 6.0 ms | 12.2 ms | 4.6–27.4 ms |
| `GET /api/documents/{id}` with three sections | 30 | 8.8 ms | 37.8 ms | 6.2–43.0 ms |
| `GET /api/documents/{id}/prepare` | 30 | 8.7 ms | 41.2 ms | 5.9–46.1 ms |
| `POST /api/compare` on two three-section documents | 10 | 37.4 ms | 122.4 ms | 24.0–122.4 ms |

The two TXT uploads took **35.2 ms** and **35.7 ms**. One uncached `POST /api/ask` call with local Ollama took **7,200.4 ms** and returned an `answered` result. A single model call has no meaningful percentile; its latency varies with model warm state, prompt length, hardware, and system load.

## Reproduce

```powershell
.venv\Scripts\python.exe scripts/measure_latency.py
```

The script prints JSON with the timestamp, platform, sample counts, median, nearest-rank p95, min/max, and answer status. It uses only synthetic clauses and an isolated temporary database. The result above was recorded at `2026-09-25T05:02:27Z`. The earlier first run was excluded because other suites were running and its temporary database cleanup failed; that exposed the SQLite handle bug fixed before this recorded run.

## Retrieval optimization check

The prior implementation fit a TF-IDF matrix over every section for every question and repeated that work in lexical fallback paths. The updated code first selects sections containing at least one meaningful question term, fits the matrix on those candidates, and reuses the resulting lexical ranking in hybrid fallbacks. A synthetic 400-section corpus, five calls per question, and the same Python process compared the previous committed implementation with the updated working tree. The relevant payment question returned section `317` in both versions.

| Question | Previous median | Updated median | Result |
| --- | ---: | ---: | --- |
| “What is the monthly payment?” | 563.0 ms | 50.8 ms | No lexical match in either version |
| “How much must the customer pay each month?” | 603.8 ms | 64.4 ms | Payment section `317` first in both versions |

Run `python scripts/benchmark_retrieval.py` to measure the current implementation on the same synthetic corpus. A separate current-only run measured 35.2 ms and 50.1 ms medians, respectively. These are function timings on synthetic text, not end-to-end model or hosted latency. The first question still needs semantic matching or more natural lexical normalization to find the differently worded payment clause.

## Interpretation

These numbers show that deterministic operations on tiny local documents complete quickly on this machine, while generation is the dominant cost. They do not establish a throughput target, behavior on 200-page documents, OCR latency, or performance on Railway hardware. A hosted load test and representative-document benchmark remain open release gates.
