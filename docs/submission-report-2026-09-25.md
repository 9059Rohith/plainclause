# Plainclause submission report — 2026-09-25

## Product

Plainclause reads English PDF, DOCX, and TXT legal documents. It extracts source sections, gives cited answers and explanations, flags terms for review, compares documents, and prepares source linked questions for a lawyer. It provides legal information, not legal advice.

The default AI provider is local Ollama. The OpenAI path requires an explicit `PLAINCLAUSE_PROVIDER=openai` setting and an API key; that setting sends retrieved excerpts and questions to the configured cloud endpoint. The evaluation preview uses the local provider.

## Verification on Windows / Python 3.12

| Check | Result |
| --- | --- |
| Backend pytest suite | 35 passed, 2 upstream test-client deprecation warnings |
| Playwright Chrome workflows | 4 passed: full desktop workflow, mobile overflow, temporary preview notice, hosted-service notice |
| TypeScript | Passed |
| ESLint | Passed |
| Vite production build | Passed |
| `npm audit --audit-level=high` | Zero vulnerabilities reported |
| `pip check` | No broken requirements |
| `pip-audit` on the pinned Windows environment | No known vulnerabilities found |

The test suite covers upload validation, document parsing, OCR, clause analysis, retrieval and citation checks, session isolation, comparison, answer streaming, deletion, hosted-service readiness, and browser interaction. Run `scripts/verify.ps1` on the documented Windows setup to repeat the local checks. Linux CI and the Docker image are not yet verified.

## Review evidence

- [Engineering and design review](quality-gate.md): requirements matrix, architecture choices, and visual fidelity ledger.
- [Earlier evaluation snapshot](evaluation-2026-09-16.md): task specific evaluation and remaining limits.
- [Deployment design](superpowers/specs/2026-09-15-protected-preview-deployment-design.md) and [implementation record](superpowers/plans/2026-09-15-protected-preview-deployment.md): preview architecture and prior rollout checks.
- [Railway deployment runbook](railway-deployment.md): container configuration, rollout checks, and current resource blocker.

## Live preview check

On 2026-09-25, the [HTTPS preview](https://bee-nonintersecting-overwarily.ngrok-free.dev/) returned HTTP 200 for the app and status endpoint, with the local `qwen2.5:1.5b` model available. A synthetic agreement was uploaded through the public URL, its `$275 each month` clause was extracted, and the question “What is the monthly payment?” returned an `answered` result with one citation. The test document was deleted; the isolated preview database then contained zero documents. The backend and tunnel scheduled tasks were running after the check.

After restarting the local preview server later that day, the public `/api/status` endpoint again reported `model_available: true` and `hosted_preview: true`. This confirms the preview link at that check, not future uptime.

## Release limitations

The Railway deployment has not occurred. The signed-in Railway workspace's Free plan rejected project creation with `Free plan resource provision limit exceeded. Please upgrade to provision more resources!` The proposed Docker image has not been built because the Docker Desktop engine is unavailable locally. A paid workspace with sufficient memory, a persistent `/data` volume, a successful image build, and public smoke tests are required before a durable live link can be claimed.

The HTTPS evaluation preview is an ngrok tunnel to the local Windows service. It is available only while this computer, Ollama, backend, and tunnel are running. The free ngrok domain may display a first visit warning. Upload traffic reaches the tunnel provider before local processing. The preview has no account authentication; each browser receives a session scoped workspace. Do not use it for confidential documents or as a production legal service.

There has been no independent attorney review, accessibility audit, or production load/security assessment. A percentile claim such as “top 1%” cannot be substantiated without the judging rubric and comparative submissions; this report provides repeatable evidence instead.
