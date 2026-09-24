# Plainclause evaluation snapshot — 2026-09-16

Plainclause is an English-language legal-document reading aid. It offers information with cited source passages, not legal advice. The public link is a temporary preview of the local FastAPI, SQLite, and Ollama service, not durable cloud hosting.

| Evaluation area | Evidence | Limit |
| --- | --- | --- |
| Document understanding | PDF, DOCX, TXT, OCR, clause boundaries, page references, and size/error cases covered in backend tests | OCR and unusual layouts can misread or split text |
| Answer grounding | Retrieved passages, exact citation IDs, source excerpts, numeric-claim and directive checks; live HTTPS question returned an `answered` response with one citation | Citation checks do not prove every nonnumeric statement is correct |
| Hallucination resistance | Invented amounts and dates, unsupported questions, and unsafe directives have regression tests and source-only fallback | A small local model may still produce an inaccurate interpretation |
| Prompt injection | Document text is marked untrusted and instruction-bearing lines are filtered from model context | Filtering is heuristic |
| Comparison and actionability | Added/removed/changed clauses, amounts and periods, preparation checklist, and exports covered by browser workflow tests | Changes are not legal materiality judgments |
| Privacy and isolation | Session-scoped storage, loopback-only Ollama endpoint, delete flow, and isolated preview database; test uploads deleted after live check | HTTPS tunnel provider handles upload traffic; preview has no account authentication |
| Accessibility and usability | Desktop/mobile Playwright workflows, no mobile horizontal overflow, keyboard controls and visible status | No independent accessibility audit |
| Verification | 34 backend tests, 3 browser tests, TypeScript check, ESLint, production build, live public UI and API checks; npm audit found zero vulnerabilities and pip-audit found no known vulnerabilities | No licensed-attorney review or external security/load test |

The live preview returned `Local AI ready`, extracted a synthetic payment clause, answered “What is the monthly payment?” with “The cited passage states: $275 each month.” and one citation, then deleted the test document. The preview database had zero documents after testing.

No percentage score is claimed for legal accuracy. Professional review on representative documents and deployment changes would be needed before public production use.
