# Plainclause submission report — 2026-09-25

## Product

Plainclause reads English PDF, DOCX, and TXT legal documents. It extracts source sections, gives cited answers and explanations, flags terms for review, compares documents, and prepares source linked questions for a lawyer. It provides legal information, not legal advice.

The default AI provider is local Ollama. The OpenAI path requires an explicit `PLAINCLAUSE_PROVIDER=openai` setting and an API key; that setting sends retrieved excerpts and questions to the configured cloud endpoint. The evaluation preview uses the local provider.

## Verification on Windows / Python 3.12

| Check | Result |
| --- | --- |
| Backend pytest suite after SQLite resource fix | 36 passed, 2 upstream test-client deprecation warnings |
| Playwright Chrome workflows | 4 passed: full desktop workflow, mobile overflow, temporary preview notice, hosted-service notice |
| TypeScript | Passed |
| ESLint | Passed |
| Vite production build | Passed |
| `npm audit --audit-level=high` | Zero vulnerabilities reported |
| `pip check` | No broken requirements |
| `pip-audit` on the pinned Windows environment | No known vulnerabilities found |

The test suite covers upload validation, document parsing, OCR, clause analysis, retrieval and citation checks, session isolation, comparison, answer streaming, deletion, hosted-service readiness, and browser interaction. Run `scripts/verify.ps1` on the documented Windows setup to repeat the local checks. Linux CI and the Docker image are not yet verified.

The final backend run after the storage change passed 36 tests. The full verification script passed all of its configured gates; the pinned Python advisory scan was run separately and found no known vulnerabilities. The local synthetic latency probe recorded 6.0 ms median for an empty document list (30 runs) and 7.2 seconds for one uncached local-model answer. These are in-process local observations, not cloud performance claims.

## Review evidence

- [Engineering and design review](quality-gate.md): requirements matrix, architecture choices, and visual fidelity ledger.
- [Earlier evaluation snapshot](evaluation-2026-09-16.md): task specific evaluation and remaining limits.
- [Deployment design](superpowers/specs/2026-09-15-protected-preview-deployment-design.md) and [implementation record](superpowers/plans/2026-09-15-protected-preview-deployment.md): preview architecture and prior rollout checks.
- [Railway deployment runbook](railway-deployment.md): container configuration, rollout checks, and current resource blocker.
- [Feature evidence](feature-evidence.md), [code quality](code-quality-report.md), [security review](security-review.md), [test report](test-report-2026-09-25.md), [latency report](latency-report-2026-09-25.md), and [accessibility review](accessibility-review.md): implementation and measured evidence.
- [Submission readiness matrix](submission-readiness.md): passed local parameters and open cloud/independent-review gates.

## Live preview check

On 2026-09-25, the [HTTPS preview](https://bee-nonintersecting-overwarily.ngrok-free.dev/) returned HTTP 200 for the app and status endpoint, with the local `qwen2.5:1.5b` model available. A synthetic agreement was uploaded through the public URL, its `$275 each month` clause was extracted, and the question “What is the monthly payment?” returned an `answered` result with one citation. The test document was deleted; the isolated preview database then contained zero documents. The backend and tunnel scheduled tasks were running after the check.

After restarting the local preview server later that day, the public `/api/status` endpoint again reported `model_available: true` and `hosted_preview: true`. This confirms the preview link at that check, not future uptime.

## Release limitations

The Railway deployment has not occurred. The original account's Free plan rejected project creation. Under the new account, the Railway project, service, `/data` volume, and domain were created, but both source uploads failed before build with `Your workspace has been restricted. Please attach a payment method or contact support to resolve this.` Direct GitHub connection also failed because that Railway account lacks access to this repository. The reserved domain `https://plainclause-production.up.railway.app` is **not live**. The Docker image has not been built because Docker Desktop is unavailable locally and Railway blocked the remote build. Account restriction resolution, a successful image build, and public smoke tests remain required before a durable live link can be claimed. See the [Railway runbook](railway-deployment.md).

The HTTPS evaluation preview is an ngrok tunnel to the local Windows service. It is available only while this computer, Ollama, backend, and tunnel are running. The free ngrok domain may display a first visit warning. Upload traffic reaches the tunnel provider before local processing. The preview has no account authentication; each browser receives a session scoped workspace. Do not use it for confidential documents or as a production legal service.

There has been no independent attorney review, accessibility audit, or production load/security assessment. A percentile claim such as “top 1%” cannot be substantiated without the judging rubric and comparative submissions; this report provides repeatable evidence instead.
