# Vercel evaluation deployment — 2026-09-25

## Verified links and state

| Item | Result |
| --- | --- |
| Public evaluation URL | <https://plainclause-xi.vercel.app/> |
| GitHub repository | <https://github.com/9059Rohith/plainclause> |
| Vercel project | `plainclause` in `ajeyas-projects-ac1f8c11` |
| Production deployment | `dpl_C8wzdrrQQ3fc6YAV1PoSFyHhDuD5`, reported `READY` by Vercel |
| Backend origin | Local FastAPI, SQLite, and Ollama through an ngrok HTTPS tunnel |

The production alias served the built React HTML and returned HTTP 200 from `/api/ready` through Vercel's external rewrite. The backend reported `model_available: true` for the local Ollama model. On the public Vercel alias, a fresh browser-like HTTP session then:

1. Uploaded a synthetic two-section TXT agreement (`200`, two sections).
2. Indexed both sections (`200`, `indexed: 2`, `total: 2`).
3. Asked how much the customer must pay each month (`200`, `answered`). The answer was **“The customer must pay $275 each month.”** with one citation to the exact Payment passage.
4. Deleted the session's test data (`200`, `deleted_documents: 1`).

The synthetic text contained no private customer material. The verification exercised the public Vercel URL, its API rewrite, the tunnel, the backend, local embeddings, local generation, citations, cookies, and deletion. It is an observed smoke test, not an uptime or legal-accuracy guarantee.

A headless Chromium workflow also opened the Vercel URL, uploaded a synthetic TXT agreement through the visible UI, asked the payment question, saw the `$275` source citation, and used **Delete my data** to return to the empty workspace. The [live browser capture](assets/plainclause-vercel-live.png) shows the cited answer before deletion.

## How this deployment works

`vercel.json` publishes the Vite frontend and rewrites `/api/:path*` to the HTTPS ngrok address. The frontend sends the `ngrok-skip-browser-warning` request header so API calls receive JSON instead of ngrok's first-visit page. The backend's `PLAINCLAUSE_ALLOWED_ORIGINS` setting names the Vercel aliases allowed to perform browser mutations. All other cross-origin mutation attempts remain blocked. The public status response does not include any API-key fragment.

The initial Vercel deployment uploaded the locally built static assets and an equivalent rewrite configuration through the connected Vercel deployment API. This deployment is not Git-linked; pushing GitHub commits alone does not publish later frontend changes. `vercel.json` records the source configuration for a future Git-connected deployment.

The backend, Ollama model, and SQLite database remain on the local Windows computer. If that computer, the backend process, Ollama, or the ngrok tunnel stops, the Vercel frontend may still render but document actions will fail. The tunnel URL can change. A durable cloud backend requires hosting the container and persistent `/data` volume; the [Railway report](railway-deployment.md) records the current account restriction. Do not call this an all-cloud or permanent deployment.

At the final check, the backend and tunnel were running in active command sessions after Windows scheduled task restarts stalled. The public URL answered a warmed synthetic question with one citation and deleted the test document. These command sessions and the computer must remain running for the evaluation API to work.

## Recheck after a restart

1. Confirm `http://127.0.0.1:8765/api/ready` returns `{"ready":true}` and the ngrok local API on port 4040 advertises the URL in `vercel.json`.
2. Confirm `https://plainclause-xi.vercel.app/api/ready` returns HTTP 200 and JSON, not an ngrok warning page.
3. Repeat a synthetic upload, index, cited question, and delete through the Vercel URL. Clear the test workspace afterward.
4. If the ngrok hostname changes, update `vercel.json`, redeploy Vercel, and update the backend's exact `PLAINCLAUSE_ALLOWED_ORIGINS` value if the public Vercel domain changes.
