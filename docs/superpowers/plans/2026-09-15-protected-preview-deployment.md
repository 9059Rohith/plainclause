# Plainclause Evaluation Preview Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify Plainclause and deliver a directly accessible public HTTPS evaluation link.

**Architecture:** The existing Vite production build is served by the existing FastAPI process on loopback port 8765. An ngrok HTTPS tunnel exposes that single origin without enabling the optional Basic-auth gate; the hosted-preview notice, isolated SQLite database, and local Ollama preserve the application's documented preview model. Windows Task Scheduler keeps both runtime processes independent of the command session.

**Tech Stack:** React 19, Vite 6, TypeScript 5.7, FastAPI, SQLite, Ollama, Playwright, ngrok

**Spec:** `docs/superpowers/specs/2026-09-15-protected-preview-deployment-design.md`

## Global Constraints

- Bind FastAPI only to `127.0.0.1:8765`.
- Set `PLAINCLAUSE_HOSTED_PREVIEW=1`.
- Store preview data only in `.runtime/preview.db`.
- Leave `PLAINCLAUSE_ACCESS_PASSWORD` unset so evaluators can open the application directly.
- Do not claim durable production hosting; the link depends on this computer and its local processes remaining online.
- Do not expose the preview until the complete verification suite passes.
- This workspace has no Git repository, so no worktree or commits can be created; execution stays in the current isolated project folder.

---

### Task 1: Verify the application

**Files:**
- Read: `package.json`
- Read: `backend/requirements.lock.txt`
- Test: `backend/tests/`
- Test: `tests/e2e/workflow.spec.ts`
- Generate: `dist/`

**Interfaces:**
- Consumes: the existing source tree and installed `.venv` and `node_modules` dependencies
- Produces: a verified production frontend in `dist/`

- [x] **Step 1: Run backend tests**

Run: `$env:PYTHONPATH='backend'; .venv\Scripts\python.exe -m pytest backend/tests -q`

Expected: exit code 0 and all backend tests pass.

- [x] **Step 2: Run frontend static checks and build**

Run: `npm run typecheck`, `npm run lint`, and `npm run build`

Expected: each command exits with code 0 and `dist/index.html` exists.

- [x] **Step 3: Run browser workflow tests**

Run: `npm run test:e2e`

Expected: exit code 0 with desktop and mobile workflows passing.

### Task 2: Start the evaluation production service

**Files:**
- Read: `backend/app/main.py`
- Runtime: `.runtime/preview.db`
- Runtime: `.runtime/backend.stdout.log`
- Runtime: `.runtime/backend.stderr.log`

**Interfaces:**
- Consumes: `dist/`, local Ollama at `127.0.0.1:11434`, and the FastAPI app factory
- Produces: evaluator-accessible HTTP service at `http://127.0.0.1:8765`

- [x] **Step 1: Configure direct evaluator access**

Run: ensure the persistent backend launcher does not set `PLAINCLAUSE_ACCESS_PASSWORD`.

Expected: the backend process starts without the optional Basic-auth gate.

- [x] **Step 2: Start FastAPI in the background**

Run: launch `.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8765` with the hosted-preview and database environment variables, hidden window style, and separate stdout/stderr logs.

Expected: the process stays running and owns loopback port 8765.

- [x] **Step 3: Verify anonymous access and model readiness locally**

Run: request `/api/status` without credentials.

Expected: status is 200 and reports the local model available.

### Task 3: Expose and verify the HTTPS preview

**Files:**
- Runtime: `.runtime/ngrok.log`
- Runtime: `.runtime/preview-url.txt`

**Interfaces:**
- Consumes: the evaluation service at `http://127.0.0.1:8765`
- Produces: a public `https://*.ngrok-free.dev` URL

- [x] **Step 1: Start a persistent ngrok tunnel**

Run: launch ngrok for `http://127.0.0.1:8765` from a restartable Windows scheduled task with separate logs.

Expected: the local ngrok API returns one generated `https://*.ngrok-free.dev` URL; save it to `.runtime/preview-url.txt`.

- [x] **Step 2: Verify direct public access**

Run: request the public `/api/status` without credentials.

Expected: status is 200 and model readiness is true.

- [x] **Step 3: Verify the public core workflow**

Run: use one cookie-preserving HTTP session with Basic auth and `X-Requested-With: Plainclause` to upload a synthetic TXT agreement, fetch its extracted sections, ask what payment is due, verify the answer cites the uploaded section, then call `DELETE /api/data`.

Expected: upload returns 200; sections contain `$275 each month`; answer contains at least one citation; deletion returns 200.

- [x] **Step 4: Verify cleanup and availability**

Run: query `.runtime/preview.db` for document count and request the public anonymous `/api/status` again.

Expected: document count is zero and public status remains 200.

### Task 4: Deliver the deployment

**Files:**
- Read: `.runtime/preview-url.txt`

**Interfaces:**
- Consumes: fresh public verification evidence
- Produces: the URL and credentials delivered to the user

- [x] **Step 1: Confirm runtime processes remain healthy**

Run: confirm the FastAPI and ngrok scheduled tasks are running and the public anonymous status request returns 200.

Expected: both processes are running and the endpoint is healthy.

- [x] **Step 2: Report verified scope precisely**

Deliver the URL, verification summary, and the limitation that the temporary link works only while this computer and the runtime processes remain online.
