# Accessibility and responsive review — 2026-09-25

## Observed implementation

The UI uses semantic form controls, labeled upload and question inputs, visible focus styling, live status/error messaging, and reduced-motion styles. The mobile layout stacks the desktop workspace and preserves navigation to Overview, Ask, Compare, and Prepare. The repository contains real desktop and mobile screenshots under `docs/assets/`; the browser suite checks that the mobile empty view and comparison do not overflow horizontally.

| Check | Evidence | Result |
| --- | --- | --- |
| Desktop core workflow | `tests/e2e/workflow.spec.ts` uploads, asks, compares, prepares, exports, and deletes | Passed in Chrome |
| Mobile empty state | 390 px viewport and horizontal-overflow assertion | Passed in Chrome |
| Mobile comparison | Included in browser workflow with overflow check | Passed in Chrome |
| Visible focus and reduced motion | `src/styles.css` rules and keyboard-capable controls | Present in source; not independently audited |
| Dynamic status | React UI status/error copy and live region patterns | Present in source; screen-reader behavior not independently tested |

No independent accessibility audit, screen-reader test across assistive technologies, color-contrast certification, or WCAG conformance claim has been completed. These remain release gates for a professionally relied-on public service.
