# Reference review: Contextualis

The user supplied [pavanravindrakumar/contextualis](https://github.com/pavanravindrakumar/contextualis) as a 99%-scoring example. That score is user-reported; the evaluator rubric, run, and result are not available for independent verification. This review uses the public repository and the supplied ZIP, not its claimed score as proof of correctness.

| Topic | Contextualis | Plainclause |
| --- | --- | --- |
| Hosting shape | Static Vite UI plus one stateless Vercel Gemini function | Vercel UI plus local FastAPI/Ollama/SQLite through HTTPS proxy |
| Document input | PDF with Gemini native document input and local PDF.js extraction | PDF, DOCX, TXT; local parsing and OCR for image-only PDF pages |
| Evidence check | Client-side exact/fuzzy quote matching with an explicit unverified state | Selected-document citations, citation-ID checks, numeric-claim checks, and source-only fallback |
| State | Ephemeral browser and function state, no database | Session-scoped SQLite, saved summaries/history, and deletion |
| Distinctive workflow | Role/concern prioritization and PDF highlights | Full-document overview, multi-document comparison, lawyer preparation, local AI default |
| Verification | Vitest, typecheck, lint, schema and prompt-injection tests, live validation scripts | Pytest API/pipeline, Playwright workflows, typecheck, lint, build, dependency review, public smoke test |

The strongest transferable practices are: independent evidence checking, strict validation of model output, a clear unverified fallback, runnable verification commands, explicit risk limits, and a public deployment that has been exercised end to end. Plainclause already enforces citation IDs, supported numeric claims, and source-only fallback. The Vercel evaluation deployment and public synthetic smoke test close the immediate link gap. Retrieval now skips unrelated sections before TF-IDF fitting, with a benchmark reported separately.

A future improvement is stronger verification of **nonnumeric** generated claims against cited text; an attached citation alone cannot prove every paraphrase. A permanent, independently hosted backend with persistent storage is also still required for durable availability. Copying the reference's stateless architecture wholesale would remove Plainclause's saved workspace and local-model privacy option, so the products need not share identical infrastructure to meet the same user goal.

No repository structure or documentation can guarantee a 100% evaluator score. A score increase must be checked by rerunning the actual evaluator against the deployed version and reviewing its detailed feedback.
