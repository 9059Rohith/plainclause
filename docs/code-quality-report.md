# Code quality report — 2026-09-25

## Scope and method

The repository was inspected across `src/`, `backend/app/`, tests, build configuration, and deployment files. The automated gates are TypeScript typecheck, ESLint, Vite build, backend pytest, Playwright Chrome workflows, `npm audit --audit-level=high`, `pip check`, and `pip-audit` on the pinned Python environment. Results are tied to the documented Windows/Python 3.12 setup and the commit cited in the [submission report](submission-report-2026-09-25.md).

| Gate | Command | Result / interpretation |
| --- | --- | --- |
| Type safety | `npm run typecheck` | Passed; checks TypeScript source, not Python types. |
| Frontend lint | `npm run lint` | Passed; ESLint is scoped to `src/`. |
| Production frontend build | `npm run build` | Passed; TypeScript build and Vite asset bundling complete. |
| Backend/API behavior | `python -m pytest backend/tests -q` | 36 passed, 2 upstream test-client deprecation warnings. |
| Browser behavior | `npm run test:e2e` | 4 Chrome flows passed for desktop, mobile, and hosted disclosures. |
| JavaScript dependencies | `npm audit --audit-level=high` | 0 vulnerabilities reported; audit is advisory data, not a security certification. |
| Python dependencies | `python -m pip check` and `python -m pip_audit -r backend/requirements.lock.txt --no-deps --disable-pip` | `pip-audit` reported no known vulnerabilities on 2026-09-25; the pinned lockfile has no hashes. |

The frontend separates API communication (`src/api.ts`), views (`App.tsx`, `Compare.tsx`, `Prepare.tsx`), types, and exports. The backend separates ingestion, deterministic analysis, retrieval and grounding, model access, SQLite, and HTTP routes. Comparison and preparation UI modules load on demand. The Dockerfile uses separate Node and Python build stages and excludes tests, runtime files, and documentation from the image context.

A repository text scan for common private-key, GitHub token, OpenAI-style key, and AWS access-key patterns found no matching credentials. This is a narrow pattern check, not a complete secret scan. The generated poster and screenshots contain synthetic or empty UI content.

## Resource lifecycle fix

While adding a reproducible latency probe, the isolated SQLite file remained locked on Windows after requests. `sqlite3.Connection` used as a context manager commits or rolls back but does not explicitly close the handle. `Store.connect()` now wraps transactions in a context manager that always closes the connection. `test_store_closes_connection_after_transaction` checks that the handle is unusable after the transaction and that its file can be removed. The full backend suite passed after this change, and the probe completed with exit code 0 and cleaned up its temporary database.

## Limits of the quality claim

- No Python static type checker, format gate, code-coverage percentage, or Linux CI workflow is configured. None is reported as passed.
- A clean Docker image build and remote startup have not completed because Docker Desktop is unavailable locally and Railway blocks upload.
- Automated checks do not validate arbitrary legal interpretations, runtime scale, accessibility, or security against an external attacker.

The [feature evidence](feature-evidence.md), [security review](security-review.md), [latency report](latency-report-2026-09-25.md), and [readiness matrix](submission-readiness.md) show what each result supports.
