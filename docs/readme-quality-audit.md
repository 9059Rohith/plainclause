# README quality audit — 2026-09-25

| Check | Result | Evidence / limit |
| --- | --- | --- |
| Repository inspected | Yes | Frontend, backend, tests, Docker, Railway configuration, scripts, reports, and assets inspected. |
| Architecture and data flow | Yes | Mermaid diagrams map the implemented React, FastAPI, SQLite, retrieval, and model paths. |
| Installation | Partly | Commands match the tested Windows/Python 3.12 setup; a clean clone has not been repeated after the README edit. |
| Environment variables | Yes | Names and defaults checked against `backend/app/main.py`, `backend/app/model.py`, and `Dockerfile`. |
| API documentation | Yes | Route table checked against `backend/app/main.py`; generated OpenAPI pages are disabled. |
| Testing | Yes | Commands checked against package scripts and `scripts/verify.ps1`; 36 backend and 4 browser tests in the current test report. |
| Latency | Measured locally | Synthetic in-process probe, sample counts, and limits in the latency report; no cloud/load benchmark. |
| Docker | Yes, unverified build | `Dockerfile` and entrypoint documented; no local or remote image build has completed. |
| Deployment | Accurate blocker | Railway resources exist but the workspace rejects uploads before build. Reserved domain is identified as not live. |
| Security and limitations | Yes | Session isolation, validation, hosted data flow, and review gaps disclosed. |
| Roadmap and contributing | Yes | Completed workflows and remaining release gates separated. |
| Links | Local links checked | Repository and temporary preview links are documented; the preview can expire. Railway domain is not presented as live. |
| Secrets exposed | No known secrets | README and reports contain no API key or payment credential. |
| Fabricated claims | None found | No accuracy, uptime, scale, certification, or percentile claim. |

## Missing or not verified

- A working durable cloud deployment and live domain.
- A successful Docker image build on Railway or the local computer.
- Linux CI, hosted load benchmarks, and independent legal/security/accessibility reviews.
- Long-term availability of the temporary ngrok preview.

This audit checks documentation against the repository and recorded local tests. It does not certify production operation.
