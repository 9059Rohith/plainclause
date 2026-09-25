# Railway deployment status and runbook — 2026-09-25

## Status

The repository is configured for a single Railway Docker service with a bundled frontend, FastAPI backend, and local Ollama models (`qwen2.5:1.5b` and `all-minilm`). It has **not** been deployed. The original Railway account's Free plan rejected project creation. The newly signed-in account successfully created the project, service, and persistent volume, but Railway rejected both code uploads with `Your workspace has been restricted. Please attach a payment method or contact support to resolve this.` The Railway account also lacks access to the GitHub repository, so direct source connection returned `User does not have access to the repo`. The local Docker Desktop engine remains unavailable; there is no verified container build or permanent live URL.

| Railway resource | ID / status |
| --- | --- |
| Workspace | `c5cb55bf-43e2-49cd-9131-7a9558bfa78b` — trial credit visible, billing state `INACTIVE` |
| Project | `e2f97b54-27dc-4ba0-84e3-8919f71f87af` |
| Production service | `55ae07bd-1624-42c1-be17-488354f6d078` — latest deployment failed before build |
| Persistent `/data` volume | `0cbe36bf-e8c0-417f-9ec3-4f9fbaa6478c` |
| Reserved domain | `https://plainclause-production.up.railway.app` — **not live** |

Railway's rejection explicitly requires attaching a payment method or contacting its support team to resolve the workspace restriction. This is an account-level action; another code upload produces the same rejection. Railway's [free-trial documentation](https://docs.railway.com/pricing/free-trial) describes verification and trial limits, but it does not establish that this particular restriction can be removed by connecting GitHub. Do not assume a card will remove it automatically. Do not add a paid plan or payment method without account-owner action.

Railway's Hobby plan starts at $5/month and resource usage is billed separately. Obtain account-owner approval for the recurring plan and expected compute/storage charges before upgrading. The local 1.5B model needs substantially more memory than the Free plan's 0.5 GB limit.

## Deploy after the workspace has capacity

1. Resolve the workspace restriction in the signed-in Railway account through the payment-method or support path Railway specifies. Confirm any billing terms and a suitable spending limit before activating a paid service.
2. From this repository, run `railway link -p e2f97b54-27dc-4ba0-84e3-8919f71f87af -e production -s 55ae07bd-1624-42c1-be17-488354f6d078 --json`, then `railway up --detach --json`. The existing project, service, volume, and domain do not need to be recreated. The build downloads Ollama and both models, so expect a large image and a slow first build.
3. Confirm the `/data` volume remains attached, with `PLAINCLAUSE_DB_PATH=/data/plainclause.db` and `OLLAMA_MODELS=/opt/ollama-models` in the image. The bundled models live in the image; SQLite data belongs on the volume.
4. Wait for `/api/ready` to return 200 on the reserved domain. The app should report `hosted_service: true` and `model_available: true` at `/api/status`.
5. Run a public synthetic-document smoke test: upload a small document, verify extraction, ask a grounded question, inspect its citation, compare a second document, export a preparation sheet, and delete the test data. Confirm the deleted workspace has no documents, then record the live URL and deployment ID in the submission report.

The Docker image serves on Railway's `PORT`, uses Secure session cookies and hosted-service copy, and keeps Ollama on loopback. The service is intended for evaluation. A public production legal service needs account authentication, independent attorney review, and security/load assessment.

## Rollback and operations

Railway can redeploy the previous image if a deployment fails. Keep the `/data` volume attached when redeploying; detaching or replacing it loses the working SQLite database. Watch the health check, deployment logs, disk use, and resource costs. Do not create the domain or publish it as a permanent link until the full smoke test passes.
