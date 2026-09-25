# Submission readiness matrix — 2026-09-25

## Decision

**Repository and public evaluation flow: ready for technical review. Durable hosted submission: pending.** The [Vercel evaluation URL](https://plainclause-xi.vercel.app/) completed a synthetic upload, index, cited answer, and deletion on 2026-09-25. Its API still depends on the local computer and ngrok tunnel. Railway rejects source uploads because its workspace is restricted. Therefore a claim that *all* submission parameters or the whole project are "100% submission ready" would be inaccurate.

The actual judging rubric has not been provided, so this matrix evaluates only requirements evidenced by the repository and the user's stated request. It does not infer a percentile rank or legal accuracy score.

| Parameter | Status | Evidence | Remaining step |
| --- | --- | --- | --- |
| Clear product purpose and legal-information boundary | Passed | README, user-facing disclaimer, backend policy tests | Independent legal review for professional use |
| Repository and poster | Passed | Public GitHub repository; hero at top of README | None for local review |
| Supported upload formats and OCR | Passed locally | Parser and API tests; [feature map](feature-evidence.md) | Check representative real-world scans |
| Grounded answers, explanations, and overview | Passed locally | Grounding, streaming, summary, and browser tests | Attorney evaluation of interpretation quality |
| Comparison, preparation, Markdown export | Passed locally | Analysis tests and desktop browser workflow | Browser PDF/print output not separately asserted; human review of semantic changes |
| Data isolation and deletion | Passed locally | Session, concurrency, deletion, and security tests | Add identity and abuse controls for public hosting |
| Typecheck, lint, build, automated tests | Passed on documented Windows setup | [test report](test-report-2026-09-25.md) | Add Linux CI and coverage if required by rubric |
| Dependency advisories | No known high-severity npm issue / no known pinned Python issue at scan time | [code quality report](code-quality-report.md) | Re-run before later releases |
| Latency evidence | Measured local synthetic workload | [latency report](latency-report-2026-09-25.md) | Cloud and load benchmarks remain unmeasured |
| Temporary evaluation preview | Passed at last HTTP/model check | [submission report](submission-report-2026-09-25.md) | Depends on local computer and tunnel |
| Vercel frontend and public API flow | **Passed at recorded check** | [Vercel deployment report](vercel-deployment.md): upload, index, cited answer, delete | Keep local backend and tunnel running; reconnect after tunnel URL changes |
| Durable public Railway deployment | **Blocked** | [Railway runbook](railway-deployment.md): upload rejection before build | Railway account owner resolves workspace restriction; then build and smoke-test |
| Docker image build and cloud smoke test | **Not verified** | Docker daemon unavailable locally; Railway upload blocked | Build and test remotely after restriction clears |
| Independent legal, accessibility, load, and security review | **Not verified** | No third-party assessment report | Required before professional/public production claims |

## What "passed" means

Automated checks ran on the documented machine and configuration. They establish specific observed behavior, not full correctness for every input or environment. The performance report is a small synthetic local measurement, not a service-level objective. Security controls reduce risk but have not undergone penetration testing. The Vercel frontend proxies to a test tunnel and does not satisfy durable backend hosting.

## Final cloud release gate

After Railway lifts the workspace restriction, deploy the existing service with its `/data` volume, wait for `/api/ready`, and run the public synthetic upload, citation, comparison, export, and delete smoke test in the [runbook](railway-deployment.md). Record the deployment ID and verified live URL in the [submission report](submission-report-2026-09-25.md). Only then mark the hosted-delivery parameter passed.
