# Plainclause Evaluation Preview Deployment Design

## Goal

Deliver the existing Plainclause application through a directly accessible HTTPS evaluation link while preserving its local-first document processing and avoiding a misleading claim of durable production hosting.

## Chosen approach

Run the production frontend through the existing FastAPI application on this Windows computer, backed by local Ollama and an isolated SQLite preview database. Leave the optional Basic-auth environment variable unset for evaluator access, then expose only the loopback FastAPI port through an ngrok HTTPS tunnel.

This is a temporary hosted preview. It remains available only while this computer, Ollama, the FastAPI process, and the tunnel process are running. Uploaded traffic passes through ngrok before reaching this computer. The application must display its hosted-preview privacy notice.

## Components and data flow

1. Build the React/Vite frontend into `dist/`.
2. Start FastAPI on `127.0.0.1:8765` with:
   - `PLAINCLAUSE_HOSTED_PREVIEW=1`
   - no `PLAINCLAUSE_ACCESS_PASSWORD` in the direct-access evaluation preview
   - `PLAINCLAUSE_DB_PATH` pointing to `.runtime/preview.db`
3. FastAPI serves the production frontend and `/api` routes from one origin.
4. Ngrok creates an HTTPS tunnel to `http://127.0.0.1:8765`.
5. Evaluators access the preview without application credentials; anyone with the URL can use it.
6. Documents are extracted locally, source text is stored only in the isolated preview database, and AI calls go only to local Ollama.

## Completion and verification

- Run backend tests, frontend typecheck, lint, production build, and Playwright browser tests.
- Verify the local production health endpoint succeeds without credentials.
- Verify the public HTTPS endpoint succeeds without credentials.
- Exercise the public core path with a synthetic document: upload, view extracted sections, ask a grounded question, and delete all preview data.
- Confirm the isolated preview database contains zero documents after verification.
- Deliver the HTTPS URL and temporary-hosting limitations.

## Failure handling

- Fix application or test failures before deployment.
- If Ollama is unavailable, restore it before public verification; do not present source-only fallback as full hosted readiness.
- Run the backend and tunnel as restartable Windows scheduled tasks so they are not tied to a transient command session.
- If the tunnel hostname cannot be established or reached, retry with a fresh tunnel process and URL.
- Keep runtime logs under `.runtime/` and do not expose secrets in the repository or final documentation.

## Scope boundary

This deployment does not create durable multi-user production hosting, accounts, a managed database, cloud object storage, or a hosted model. Those require a separate architecture and security review.
