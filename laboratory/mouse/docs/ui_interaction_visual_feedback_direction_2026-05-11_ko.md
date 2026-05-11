# UI Interaction And Visual Feedback Direction

Layer classification: design guidance / non-canonical product documentation.
Canonical status: non-canonical. This document does not define database tables,
API response shapes, export schemas, or lab policy. If it conflicts with
`AGENTS.md`, `final_mouse_colony_prd.md`, accepted tests, or implementation,
call out the mismatch and use the adopted source first.

Date: 2026-05-11

## Purpose

MouseDB users repeatedly inspect cage-card photos, mouse IDs, mating/litter
state, genotype results, review blockers, and Excel export readiness. The UI
should show state and next actions through visual feedback, not long explanatory
text alone.

Goals:

- make status visible before explanation;
- keep real source photos visually primary over decorative media;
- show immediate feedback for selection, correction, review resolution, apply,
  and export readiness;
- show progress for upload, parse/OCR, review, candidate preparation, apply, and
  export generation;
- distinguish raw source, parsed/intermediate state, review items, canonical
  structured state, and export/view state;
- never use color alone to communicate status.

## Evidence-First UI Rules

- Source photos and ROI crops are evidence, not decoration.
- OCR, AI parse, and manual transcription drafts are parsed/intermediate state.
- Review decisions are review items or audit evidence.
- Accepted mouse, event, mating, litter, and genotype rows are canonical state
  only after the reviewed apply path succeeds.
- Excel preview/export is an export/view, not a source of truth.

## Common Status Cues

Use chips, icons, labels, progress steps, selected-row accents, evidence badges,
confidence meters, blocker counts, and detail drawers. Prefer compact visible
state plus expandable details over long text blocks.

Suggested statuses:

| Status | Meaning |
| --- | --- |
| Raw Source | Original photo, workbook, or note source. |
| Parsing | OCR, ROI, or local processing is running. |
| Parsed | Intermediate fields exist but are not accepted. |
| Must Review | Canonical write or final export is blocked. |
| Quick Check | Short user confirmation is needed. |
| Trace Only | Retained for audit, not daily workload. |
| User Corrected | User changed interpreted or normalized value. |
| Verified | Reviewed value confirmed. |
| Accepted | Canonical state updated through reviewed path. |
| Blocked | Action unavailable until issue is resolved. |
| Export Ready | Accepted state can generate export. |
| Preview Only | File or grid is review-only. |
| Stale | Export/view is older than accepted corrections. |

Rules:

- Chips must include text, not only color.
- `Verified` and `Accepted` are different states.
- `Trace Only` should not inflate workload counts.
- Green success indicators must not appear before the relevant reviewed or
  canonical step actually completes.

## Interaction Feedback

Selection:

- highlight the selected photo, row, review item, or evidence record;
- update the detail panel title and evidence context;
- do not imply review resolution or canonical acceptance.

Hover and focus:

- keep required actions visible without hover;
- make keyboard focus visible;
- add tooltips for icon-only controls, confidence meters, and compact badges.

Corrections and review resolution:

- show short saved/verified feedback in place;
- update counts and blockers immediately;
- preserve before/after values in the review detail or correction history;
- keep unresolved sibling items visible unless filtered.

Blocked actions:

- disabled export should show blocker count and a Focus Review link;
- disabled canonical apply should list unresolved high-risk fields;
- disabled external parse assist should explain approval or local-only mode;
- disabled review resolve should show missing resolution note or required value.

## Progress Guidance

Use progress at three levels:

- batch progress for multi-photo uploads;
- photo progress for upload, quality, parse, review, candidate, accepted/held,
  and export readiness;
- operation progress for save, parse, apply, and export generation.

Photo workflow stages:

1. Uploaded
2. Quality Check
3. Parse/OCR
4. Review
5. Candidate Prepared
6. Accepted or Held
7. Export Ready or Blocked

Rules:

- a failed parse should say source stored, extraction failed;
- low-confidence parsing should complete parse but mark review required;
- held cards remain visible and traceable.

## View-Specific Notes

Upload and photo review:

- show raw source photo, crop previews, confidence, and review state together;
- separate source stored, extraction failed, and review pending states.

Focus Review:

- show source evidence and proposed value before action controls;
- use blocker categories and concise labels;
- preserve links to photo evidence, note line, and correction history.

Canonical candidate apply:

- show affected mouse IDs, source evidence, duplicate risk, unresolved review,
  and missing evidence blockers before apply.

Excel export:

- show export readiness as a view over accepted state;
- show stale/export-blocked state with source blockers;
- never style Excel as the canonical editing surface.

## Accessibility And Safety

- Do not rely on color alone.
- Icon-only controls need accessible names and tooltips.
- Status changes should be screen-reader discoverable where practical.
- Avoid animations that obscure source evidence or delay repeated review work.

## References And Tools

This section lists references and tool candidates for design and verification.
Listing a tool here does not adopt it as a MouseDB runtime dependency. Before
adding any new package or external workflow, re-check stack fit, license,
maintenance risk, privacy boundary, generated artifacts, and test cost.

### Project-Local References

Use local project guidance first because it already reflects MouseDB's
evidence-first constraints.

| Reference | Use |
| --- | --- |
| `design.md` | Main UI/workflow direction and product tone. |
| `docs/ui_references.md` | Developer-only UI reference policy and Lazyweb safety rules. |
| `docs/superpowers/specs/2026-05-09-low-fatigue-colony-ui-design.md` | Low-fatigue screen responsibilities, state cues, and visual QA checklist. |
| `ui_image_usage_improvement_plan_ko.md` | Rules for reducing decorative image noise. |
| `review_burden_reduction_plan_ko.md` | Focus Review, Quick Check, and Trace Only workload split. |
| `selective_normalization_controls_plan_ko.md` | Raw-vs-normalized bounded selection controls. |
| `final_mouse_colony_prd.md` | Adopted product behavior and evidence boundaries. |

### Design Research Tools

| Tool or source | Use | MouseDB boundary |
| --- | --- | --- |
| Lazyweb | Find reference patterns for review queues, OCR correction, evidence inspectors, and export previews. | Developer-only research with fake data only. Never send real lab photos, mouse IDs, workbook rows, genotype results, or colony records. |
| Browser screenshots | Compare actual local UI at desktop/mobile sizes. | Generated verification artifacts; do not commit disposable screenshots unless explicitly adopted. |
| Wireframes | Explore interaction alternatives before implementation. | Design guidance only, not product truth. |

Lazyweb use must follow `docs/ui_references.md`.

### Interaction And Visual QA Tools

| Tool | Use | Adoption note |
| --- | --- | --- |
| [Playwright](https://playwright.dev/) | Browser flow checks, screenshots, visual comparison, and responsive QA. | Already present as a dev dependency in this repo; keep generated screenshots out of commits unless adopted. |
| Playwright with axe-core | Accessibility smoke checks for contrast, labels, roles, and landmark regressions. | Optional test enhancement; does not replace manual keyboard and screen review. |
| [Storybook](https://storybook.js.org/docs/essentials/interactions) | Component states for chips, buttons, progress, drawers, tables, and loading skeletons. | Optional if the UI becomes componentized; avoid adding only for documentation theater. |
| [Testing Library user-event](https://testing-library.com/docs/user-event/intro/) | Interaction tests that simulate user behavior such as selection, keyboard review, and correction. | Optional if the frontend stack moves toward component or unit tests. |

Suggested checks:

- Photo Review desktop and mobile screenshot.
- Review Queue selected-row, hover, focus, and resolve feedback.
- Export Center blocked, preview-only, stale, and ready states.
- Keyboard traversal through review rows and detail drawers.
- Check that source photo remains visually primary.
- Check that disabled final export explains the blocker.

### Accessibility References

| Reference | Use |
| --- | --- |
| [WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Baseline accessibility requirements for contrast, keyboard access, focus, status messaging, target size, and reduced motion. |
| [MDN ARIA guidance](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA) | Native HTML first; add ARIA only when native semantics are insufficient. |
| [axe DevTools or axe-core](https://www.deque.com/axe/devtools/) | Automated accessibility issue detection during local or browser checks. |

MouseDB-specific accessibility priorities:

- review and export actions must be reachable by keyboard;
- focus state must be visible in dense tables;
- icon-only controls need labels and tooltips;
- status must not rely on color alone;
- progress and blocked states should be visible as text, not motion only.

### Icon And Visual Asset References

| Reference | Use | Boundary |
| --- | --- | --- |
| [Lucide-style icon set](https://lucide.dev/) | Candidate icon vocabulary for photo, crop, scan, warning, check, history, export, and settings actions. | UI implementation detail; choose only if it fits the stack and bundle constraints. |
| Existing `static/assets/` illustrations | Section-level orientation or empty states. | Keep secondary to source photos; avoid repeated row-level decoration. |
| Generated bitmap illustrations | Optional section or empty-state support. | Never represent real colony evidence; never outrank actual cage-card photos. |

### Tool Adoption Rules

- Prefer existing repo scripts before adding new tools: `npm test`,
  `npm run test:local`, `npm run verify`, and targeted browser checks.
- Do not add a new UI library, icon package, test runner, or screenshot service
  only because this document names it.
- Do not send real lab data to external design research, visual QA, or AI tools.
- Keep tool outputs classified: screenshots and local reports are generated
  artifacts unless explicitly adopted as documentation.
- If a tool repeatedly creates local artifacts, add a narrow `.gitignore` rule
  before committing.
- Every new tool should support evidence-first review, traceability,
  accessibility, or verification. Otherwise, leave it out.
