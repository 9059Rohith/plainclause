# Railway deployment status and runbook — 2026-09-25

## Status

The repository is configured for a single Railway Docker service with a bundled frontend, FastAPI backend, and local Ollama models (`qwen2.5:1.5b` and `all-minilm`). It has **not** been deployed. The signed-in Railway workspace is on the Free plan, and project creation returned `Free plan resource provision limit exceeded. Please upgrade to provision more resources!` The local Docker Desktop engine was also unavailable, so there is no verified container build or permanent live URL yet.

Railway's Hobby plan starts at $5/month and resource usage is billed separately. Obtain account-owner approval for the recurring plan and expected compute/storage charges before upgrading. The local 1.5B model needs substantially more memory than the Free plan's 0.5 GB limit.

## Deploy after the workspace has capacity

1. In the Railway account, upgrade the workspace plan and confirm a suitable spending limit. Use the `plainclause` project name in the existing workspace.
2. From this repository, run `railway up --new --name plainclause --workspace <workspace-id> -y --detach`. This uploads the repository and creates a service using the root `Dockerfile` and `railway.json`. The build downloads Ollama and both models, so expect a large image and a slow first build.
3. Attach a persistent volume before evaluators upload documents: `railway volume add --service <service-id> --mount-path /data --json`. Confirm `PLAINCLAUSE_DB_PATH=/data/plainclause.db` and `OLLAMA_MODELS=/opt/ollama-models` in the service. The bundled models live in the image; only SQLite data belongs on the volume.
4. Set a Railway service domain with `railway domain` and wait for the `/api/ready` health check to pass. The app should report `hosted_service: true` and `model_available: true` at `/api/status`.
5. Run a public synthetic-document smoke test: upload a small document, verify extraction, ask a grounded question, inspect its citation, compare a second document, export a preparation sheet, and delete the test data. Confirm the deleted workspace has no documents, then record the live URL and deployment ID in the submission report.

The Docker image serves on Railway's `PORT`, uses Secure session cookies and hosted-service copy, and keeps Ollama on loopback. The service is intended for evaluation. A public production legal service needs account authentication, independent attorney review, and security/load assessment.

## Rollback and operations

Railway can redeploy the previous image if a deployment fails. Keep the `/data` volume attached when redeploying; detaching or replacing it loses the working SQLite database. Watch the health check, deployment logs, disk use, and resource costs. Do not create the domain or publish it as a permanent link until the full smoke test passes.
