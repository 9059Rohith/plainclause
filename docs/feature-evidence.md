# Feature evidence and implementation map

This document maps advertised behavior to code and checks in the repository. "Passed" refers to the local automated suite on Windows/Python 3.12; it does not certify legal accuracy for arbitrary documents.

| Capability | Implementation | Verification | Boundary |
| --- | --- | --- | --- |
| PDF, DOCX, TXT upload | `backend/app/main.py` validates multipart uploads; `backend/app/ingest.py` parses formats and rejects invalid content | `test_upload_rejects_bad_pdf`, `test_rejects_wrong_signature_and_empty_file`, `test_docx_and_pdf_extraction_preserve_content_and_page` | 10 MB/file; English UTF-8 text |
| Clause structure and citations | `ingest.py` makes bounded sections with headings and PDF pages | Numbered-clause, long-paragraph, DOCX table, and page-reference tests in `test_pipeline.py` | Complex layouts can split incorrectly |
| Scanned PDF OCR | `ingest.py` uses local RapidOCR and labels transcriptions | `test_image_only_pdf_uses_local_ocr_and_labels_transcription` | 50 scanned pages/file; verify names, numbers, and dates |
| Section explanations | `/api/documents/{id}/simplify` sends one section with simple/detailed instruction through `model.py`, then `rag.py` checks grounding | Backend summary and grounding tests; desktop Playwright flow | Model interpretation can still be wrong |
| Full overview | `/api/documents/{id}/summary` processes six sections per call and `storage.py` saves completed batches | `test_summary_states_coverage_and_never_claims_unread_sections`; browser refresh workflow | Long documents can take minutes; uncited sections require review |
| Semantic index | `storage.py` persists `all-minilm` embeddings in batches of 16 | `test_index_history_and_deletion_are_session_scoped`; semantic-retrieval pipeline test | Embedding service may be unavailable; lexical fallback remains |
| Grounded Q&A | `rag.py` combines dense and lexical retrieval; `/api/ask` and `/api/ask/stream` return cited or source-only results | Retrieval, citation-ID, unsupported-claim, streaming, and browser tests | Citations are evidence to inspect, not proof of legal correctness |
| Review signals and dates | `analysis.py` uses text rules for categories, clauses, and dates | `test_risks_and_deadlines_are_traceable` | Rules can miss unusual wording; no legal risk verdict |
| Comparison | `analysis.py` aligns repeated headings and marks added/removed/modified terms; `/api/compare` accepts 2–5 IDs | `test_comparison_reports_modified_term`, `test_comparison_preserves_repeated_headings`, desktop browser flow | Alignment can miss semantic changes; no legal materiality judgment |
| Lawyer preparation | `/api/documents/{id}/prepare`, `src/Prepare.tsx`, and `src/export.ts` build source-linked questions and exports | Desktop browser flow covers preparation and Markdown download; print/PDF control is present in source | Browser-generated PDF output is not separately asserted; general resource categories are not verified local referrals |
| Session isolation and deletion | Cookie middleware in `main.py`; cascading rows and secure-delete in `storage.py` | `test_upload_scope_compare_and_delete`, concurrent-session and deletion tests | No account login; browser cookie loss makes old workspace inaccessible |
| Hosted disclosures | `PLAINCLAUSE_HOSTED_PREVIEW` and `PLAINCLAUSE_HOSTED_SERVICE` switch copy and secure cookies | Two dedicated Playwright flows and `test_hosted_service_status_and_readiness` | Hosted mode has no public multi-user identity system |

## User journey

1. Open the empty workspace and upload a supported document. The API validates type, signature, size, and parser limits before storing extracted sections. Original binary bytes are discarded.
2. Read the sections and source pages in **Overview**. The UI indexes local embeddings in the background and shows real progress. Ask for an explanation of one section or request a whole-document overview at the selected reading level.
3. In **Ask**, enter a question. Retrieval stays within the selected document, and the answer includes citations or a source-only fallback. The result is saved in document-specific history.
4. In **Compare**, choose two to five documents. Added, removed, and changed wording is displayed side by side, including highlighted amount and period changes.
5. In **Prepare**, collect review questions, dates, and excerpts; add personal goals; export Markdown or use browser print to make a PDF.
6. Use **Delete my data** to remove the current session's stored documents and related records.

## Data model

`backend/app/storage.py` defines `documents`, `chunks`, `embeddings`, `messages`, `summaries`, `audit_events`, and `request_limits`. Chunks and downstream records reference documents with cascading deletion. `session_id` limits reads and mutations to the browser's cookie. Embeddings are keyed by section and model, so a saved index can be reused. Audit events store operation names, source IDs, and result status rather than document text.

## Evidence links

- [Backend tests](../backend/tests), [browser workflow](../tests/e2e/workflow.spec.ts), and [submission report](submission-report-2026-09-25.md).
- [Security review](security-review.md), [code quality report](code-quality-report.md), [test report](test-report-2026-09-25.md), and [latency report](latency-report-2026-09-25.md).
