# Engineering and design review

The starting workspace had no application files or Git history. The attached product specification was used as the feature checklist. This review records the final implementation and its remaining limits.

| Area | Requirement | Starting state | Priority | Implemented and checked |
| --- | --- | --- | --- | --- |
| Legal framing | Interpretation must not look like legal advice | Absent | Critical | Persistent footer, per-answer disclaimer, high-stakes professional prompt, jurisdiction caveat, directive filter; backend tests and browser flow |
| Privacy | Keep documents local and delete them | Absent | Critical | Numeric-loopback-only model URL, session-scoped SQLite, no binary storage, secure-delete, cascading delete of vectors/history/summaries/audit, request caps; API isolation/delete and on-disk text check |
| Ingestion | PDF, DOCX, TXT with limits and source structure | Absent | High | Extension/MIME/signature and size checks, 200-page cap, 50-page OCR cap, DOCX expansion cap, in-order table extraction, bounded sections and page labels; parser and 200-page tests |
| Grounding | Answer from actual document with source | Absent | Critical | Persisted local dense embeddings plus TF-IDF reranking, selected-document scope, citation IDs, full source excerpts, numeric/directive checks, source-only fallback; retrieval and live-model checks |
| Simplification | Plain-language summaries without silent omission | Absent | High | Simple/detailed per-section explanation and full-document batch overview with saved/resumable progress, uncited-section notices, source-only failure state; API and browser tests |
| Review | Clauses, risks, deadlines | Absent | High | Heuristic category/review signals and date/period extraction with exact source; unit tests |
| Comparison | Added, removed, modified terms across 2+ documents | Absent | High | Heading and occurrence alignment, side-by-side text, exact money/period change labels, up to five docs; unit and browser tests |
| Actions | Preparation sheet and exports | Absent | High | Source-linked questions, user-entered goals, checklist, Markdown, clipboard, browser PDF/print; browser tests |
| Accessibility | Keyboard, focus, mobile, semantic states | Absent | Medium | Semantic controls, focus ring, live status/errors, reduced motion, mobile overview and comparison; browser tests and screenshots |
| Scanned PDFs | OCR | Absent | Stretch | Local RapidOCR processes up to 50 scanned pages per PDF; every OCR-derived section is marked for verification; real image-only PDF test |
| Semantic retrieval | Dense local embeddings | Absent | Medium | Local all-minilm vectors persist in SQLite; batch progress and lexical fallback; stored-vector and live-similarity checks |
| Conversation | Saved Q&A and response streaming | Absent | Medium | Session/document-scoped history; streamed model progress with final verified answer only; API and browser checks |
| Performance | Avoid redundant work and heavy initial rendering | Absent | Medium | Persisted vectors and exact verified-answer cache, lazy Compare/Prepare modules, off-screen section layout skipping, debounced document search; build and browser checks |
| Hosted multiuser service | Accounts and public rate limiting | Absent | Outside local scope | Public evaluation preview has session isolation and request caps, but no account-based identity; use only synthetic/nonconfidential documents |

## Verification evidence (2026-09-14)

The later [2026-09-25 test report](test-report-2026-09-25.md) supersedes the counts below: 36 backend tests, 4 local browser workflows, and a public Vercel browser smoke test passed. The [Vercel deployment report](vercel-deployment.md) records the live evaluation link and its local-backend dependency; the [latency report](latency-report-2026-09-25.md) records the retrieval optimization benchmark.

- Clean Windows/Python 3.12 virtual environment installed from 56 pinned packages in `backend/requirements.lock.txt`; `pip check` found no broken requirements.
- Backend: 32 tests passed, including a regression for numbered operative clauses, eight simultaneous isolated workspaces, a clearly large financial amount that prompts professional attention, and an optional preview password gate. The only warnings came from upstream Starlette/AnyIO test-client deprecations.
- Browser: 3 Playwright tests passed against that same environment, covering desktop upload through delete, mobile comparison without horizontal overflow, and accurate hosted-preview disclosure. The desktop test also reloaded saved overview and Q&A history. A separate browser run over the public HTTPS evaluation preview verified direct access without credentials, upload, cited Q&A, and deletion.
- `npm run typecheck`, `npm run lint`, and `npm run build` passed. `npm audit --audit-level=high` reported zero vulnerabilities. `pip-audit` of the complete pinned Python environment reported no known vulnerabilities. Bandit scanned 836 backend source lines with zero findings. Automated scans do not replace an independent security review.
- Live local-model QA answered synthetic NDA and terms-of-service questions with the correct cited clauses. The [Luton Council sample tenancy PDF](https://www.luton.gov.uk/sites/default/files/2026-07/assured-shorthold-tenancy-agreement.pdf) parsed into 72 sections across 10 pages; local-model answers correctly cited the clauses for weekly rent-payment day, notice forwarding period, and pet consent, and declined an absent arbitration-fee question. The PDF exposed a numbered-clause parsing issue that was fixed and regression-tested. A synthetic 200-page text PDF parsed into 200 source-referenced sections in 0.15 seconds on this machine. That timing is not a benchmark for complex scans or full-model summarization.
- The live server is bound to `127.0.0.1:8765` with the configured local Ollama model available; the default workspace held zero documents at verification.

## Visual fidelity ledger

Concept: `C:\Users\BhaviChasvi\.codex\generated_images\01a0a02a-126d-71e2-96bc-ab9d4da0154d\exec-a3acdfa8-c126-436a-870a-deefc049b786.png`. Browser render was captured with Playwright Chromium at 1586 × 992, plus 1440 × 900 and 390 × 844. Both concept and latest screenshots were inspected with `view_image`.

| Point | Concept evidence | Render result / resolution |
| --- | --- | --- |
| Header | Quiet brand left, local status and data deletion right | Same hierarchy; local AI status reflects the real model rather than a fixed badge |
| Layout | Upload/document rail, central work area, right review rail | Same three-column desktop anatomy; mobile stacks and keeps a horizontal document switcher |
| Navigation | Overview, Ask, Compare, Prepare under selected document | Same labels, order, selected state, and functioning route-local tabs |
| Typography/palette | Serif headings, dark navy, restrained teal and amber | Repeated serif/sans hierarchy and semantic colors; system fallbacks are used to avoid remote font requests |
| Sources/review | Source-related explanation and visible review/deadline items | Source quotes, headings, pages, full section text, and clickable review/deadline navigation are present |
| Responsive | The concept implies a usable compact continuation | Browser-checked mobile overview and comparison have no horizontal overflow |

Intentional content differences: the concept depicts fictitious uploaded employment documents, a generated summary, and legal risk levels. The real application opens empty and only shows text and signals derived from documents the user uploads. The overview is on demand, reports batch progress, and names uncited sections. Fixed visual issues included a squeezed mobile upload note and a hidden mobile document switcher. The concept's layout and visual language were followed; the fictitious content was deliberately not reproduced.

## Hostile review notes

- **Hallucination:** A local model can still misread a clause. Citation-ID, numeric-claim, and directive checks reject some bad output, then show source-only text. They do not prove full legal accuracy.
- **Advice confusion:** Every interpretation has its own disclaimer and source. The app avoids legal verdicts and flags time-sensitive/high-stakes questions for a professional.
- **Prompt injection:** Uploaded text is passed as untrusted data; obvious instruction lines are stripped from model context. No raw file is executed or rendered as HTML.
- **Data egress:** Model requests are restricted to loopback; no paid or hosted provider is used. Extracted text remains in SQLite until deleted.
- **Long/scanned files:** A 200-page text PDF passed the boundary test. OCR is limited to 50 pages per file; poor scans can still fail or misread names, dates, and amounts and must be checked against the original.
- **Lawyer scrutiny:** Rule-based review signals and summaries can miss nuance. The UI keeps the original language visible, highlights uncited sections, and does not claim jurisdiction-specific validity.
- **Independent review:** No licensed attorney has reviewed generated interpretations or risk signals. The local engineering checks do not establish legal correctness for arbitrary documents.
- **Release gate:** A public or professionally relied-on service still needs independent attorney review on representative documents, an external security/load assessment, and account-based authorization. Those have not occurred and must not be reported as passed.
- **Temporary preview:** An ngrok HTTPS tunnel provides a live evaluation of the local app. The current evaluation preview is intentionally not password-gated, so anyone with the URL can access it. It is not permanent hosting: the URL and uptime depend on the tunnel session and this computer, and document traffic passes through the tunnel provider. The preview uses an isolated `.runtime/preview.db` database. Ngrok may show first-time visitors a one-time safety page.
