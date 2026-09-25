# Security and privacy review — 2026-09-25

## Scope

This is a code-backed review of the repository and its local test results. It is not a penetration test, formal threat model, certification, or approval to process confidential client documents on a public service. The evaluated local configuration uses Ollama on loopback. Hosted and optional OpenAI modes have different data flows.

| Area | Implemented control | Evidence | Residual risk |
| --- | --- | --- | --- |
| Session boundaries | `main.py` sets a random 256-bit HttpOnly, SameSite=Strict cookie; all document operations query the matching session | API isolation tests and eight-concurrent-workspace test | No accounts, recovery, or user identity; cookie loss makes old data inaccessible |
| Mutation protection | `X-Requested-With: Plainclause`, origin and cross-site checks on POST/PUT/PATCH/DELETE | `test_mutation_rejects_cross_origin_and_missing_client_header` | A malicious same-origin script would bypass this boundary; CSP reduces but does not remove that risk |
| Preview gate | Optional `PLAINCLAUSE_ACCESS_PASSWORD` protects UI and API with Basic auth | `test_optional_preview_password_protects_ui_and_api` | Evaluation tunnel leaves this unset; URL holders can access the service |
| Upload handling | Extension/MIME/content checks; 10 MB size, 200 PDF pages, 50 OCR pages, 600,000 text characters, 30 MB DOCX expansion; active PDF and embedded DOCX content rejected | Invalid-upload, parser-boundary, OCR, and 200-page tests | Malformed files and OCR model vulnerabilities need external assessment; unusual layouts can misparse |
| Model egress | Ollama URL accepts numeric loopback addresses; default answer and embedding providers are local | `test_model_endpoint_cannot_send_documents_to_remote_host` | Explicit OpenAI mode sends retrieved excerpts and questions to its endpoint |
| Prompt injection | Retrieved document content is isolated from the system instruction; obvious instruction lines are stripped | Prompt-injection tests in `test_pipeline.py` | Heuristic filtering cannot guarantee resistance to every injection |
| Answer grounding | Citation IDs, numeric claims, and definitive directives checked; failed drafts become source-only responses | Grounding tests and streamed-answer test | Valid citations can still accompany mistaken interpretations |
| Response headers | No-store, content-type protection, referrer policy, CSP, frame denial, permissions policy, and HSTS when hosted/HTTPS | Middleware in `backend/app/main.py` | Browser or proxy configuration may affect final headers; cloud deployment is unverified |
| Abuse limits | Session-scoped one-minute caps for uploads, indexing, generation, and other mutations | `test_local_request_cap_and_workspace_reset` | No network-wide or account-wide quota for an exposed public service |
| Deletion | Cascade removal across sections, vectors, summaries, messages, audit events; SQLite `secure_delete=ON` | API deletion and on-disk checks in the existing test suite | OS snapshots, backups, tunnel/provider copies, and lost cookies are outside SQLite deletion |
| Secrets | OpenAI key read from environment; no credential committed in documented configuration | Source inspection; repository text scan | Environment and hosting settings still require operator protection |

## Data flow and retention

The upload is parsed in memory and its original binary is discarded. Extracted sections, embeddings, saved Q&A, overview batches, and source-ID-only audit events are stored in SQLite under a browser session. Local Ollama processes selected passages on the same computer. A Railway deployment would keep SQLite on the `/data` volume and process excerpts on Railway compute. The temporary ngrok preview sends web traffic through its tunnel provider before reaching the local app. Optional `PLAINCLAUSE_PROVIDER=openai` sends retrieved excerpts and user questions to the configured cloud endpoint; embeddings remain local.

**Delete my data** removes the current session's database rows and clears preparation goals in the current browser tab. It does not erase provider logs, snapshots, or backups. A user should delete data before clearing the browser cookie.

## Release gates

- Local upload, session, model-endpoint, injection, grounding, and delete tests passed in the documented environment.
- Dependency scans and code-quality checks are reported separately in [code-quality-report.md](code-quality-report.md).
- Public multi-user production operation requires account-based authorization, network-wide abuse controls, external security and load assessment, and a verified deployment. None is claimed complete.
- Legal interpretations need independent licensed-attorney evaluation on representative documents before professional reliance.
