# Verification report — 2026-09-25

## Environment and scope

Tests ran on Windows 11 with Python 3.12 and the repository's pinned Python environment, Node.js tooling from `package-lock.json`, Chrome for Playwright, and local Ollama for the browser workflow. The final backend run occurred after the SQLite connection-lifecycle fix. These are local results; they do not prove the Railway image or service runs.

| Gate | Command | Observed result |
| --- | --- | --- |
| Backend/API | `$env:PYTHONPATH='backend'; .venv\Scripts\python.exe -m pytest backend/tests -q` | **36 passed**, 2 upstream test-client deprecation warnings, 61.30 s |
| Frontend typecheck | `npm run typecheck` | Passed |
| Frontend lint | `npm run lint` | Passed |
| Production UI build | `npm run build` | Passed; Vite built 1,585 transformed modules |
| Browser workflows | `npm run test:e2e` | **4 passed** in 2.6 min using Chrome |
| JavaScript dependency advisory check | `npm audit --audit-level=high` | **0 vulnerabilities** reported |
| Installed Python dependency consistency | `.venv\Scripts\python.exe -m pip check` | **No broken requirements** |
| Pinned Python dependency advisory check | `.venv\Scripts\python.exe -m pip_audit -r backend/requirements.lock.txt --no-deps --disable-pip` | **No known vulnerabilities found**; auditor warned the lockfile has no hashes |
| SQLite handle regression | `python -m pytest backend/tests/test_storage.py -q` | 1 passed; included in the 36-test backend total |

The full `scripts/verify.ps1` run completed with exit code 0 for its configured gates. It does not invoke `pip-audit`; that scan was run separately. The initial backend stage of the script ran before the new SQLite regression test was added (35 passed); a separate full backend rerun after the fix passed all 36 tests.

## What the tests cover

| Area | Representative checks |
| --- | --- |
| Input boundaries | Empty and wrong-signature files, invalid PDFs, 200-page PDF boundary, DOCX table order and expansion controls, image-only PDF OCR |
| Source structure | Numbered operative clauses, full cited passages, long paragraph bounds, page references |
| Retrieval and grounding | Exact and semantic retrieval, absent evidence, citation IDs, unsupported amounts, directive filtering, prompt-injection filtering |
| API and storage | Session-scoped upload/index/history/deletion, eight concurrent isolated workspaces, request caps, origin/client-header enforcement, optional Basic auth |
| Generated views | Overview coverage and uncited sections, streaming that withholds unverified draft prose, hosted preview and service status/readiness |
| Browser experience | Desktop upload through ask/compare/prepare/export/delete, mobile overflow, hosted-preview notice, hosted-service disclosure |

## External smoke evidence

The [temporary HTTPS preview](https://bee-nonintersecting-overwarily.ngrok-free.dev/) previously returned HTTP 200 for the app and `/api/status` with the local model available. A synthetic payment clause was uploaded, queried with one citation, and deleted; the preview database returned to zero documents. This demonstrates the tunnel at the time of the check, not future availability or cloud durability. See [submission report](submission-report-2026-09-25.md).

## Gaps

- No Linux CI workflow, Python coverage percentage, formal accessibility audit, or load test is reported.
- The Docker image and Railway health check could not be exercised remotely because Railway rejected source upload before build.
- The security and dependency checks are bounded scans; they do not establish legal accuracy or vulnerability-free operation.
