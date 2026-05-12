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

## Brand, Color, And Visual Identity

MouseDB should feel like a calm lab workbench for evidence review, not a
playful animal app, marketing dashboard, or broad analytics suite. The brand
signal should come from precision, traceability, low-fatigue review, and safe
export gating.

Brand traits:

- quiet and clinical;
- evidence-first and audit-friendly;
- dense enough for repeated lab work;
- warm enough to reduce review fatigue;
- careful about uncertainty, inferred biology, and canonical writes.

Avoid:

- mascot-led or cute animal branding that competes with real cage-card photos;
- decorative gradients, oversized hero graphics, or glossy dashboard effects;
- making clean metrics look more authoritative than unresolved evidence;
- using green checkmarks where the state is only parsed, selected, or verified
  but not yet accepted.

### Color Roles

Use a neutral workbench base with restrained semantic accents.

| Role | Use | Notes |
| --- | --- | --- |
| Canvas | Main working surface | White or near-white; keep dense data readable. |
| Soft panel | Grouped review/export/evidence sections | Subtle contrast only; avoid nested-card depth. |
| Hairline | Dividers, tables, input borders | Prefer 1px borders over shadows. |
| Focus accent | Current selection, keyboard focus, active navigation | Use narrowly; do not imply success. |
| Red / danger | Must Review blockers, unsafe canonical apply, blocked final export | Pair with text and warning icon. |
| Amber / warning | Quick Check, stale export, low confidence, pending attention | Actionable but not alarming. |
| Green / success | Accepted, export-ready, completed canonical-safe action | Use only after the relevant reviewed path succeeds. |
| Teal / verified | Verified field, linked evidence, user-corrected value | Keep distinct from canonical accepted state. |
| Gray / neutral | Raw source, trace-only, disabled, processing | Avoid making Trace Only look like workload. |

Suggested implementation tokens:

| Token | Role |
| --- | --- |
| `--canvas` | Primary work surface. |
| `--panel` | Section and inspector surfaces. |
| `--panel-soft` | Quiet grouped content background. |
| `--line` | Hairline divider and table border. |
| `--text` | Primary operational text. |
| `--muted` | Secondary explanatory text. |
| `--accent` | Focus and selected state. |
| `--accent-soft` | Selected-row or active-nav background. |
| `--danger` | Must Review and blocking states. |
| `--warning` | Quick Check, stale, low-confidence states. |
| `--success` | Accepted and export-ready states. |
| `--verified` | Verified or linked evidence states. |
| `--processing-bg`, `--processing-ink` | Upload, parse, or extraction in progress. |
| `--success-bg`, `--success-line`, `--success` | Completed or accepted-safe states after the relevant reviewed path. |
| `--warning-bg`, `--warning-line`, `--warning` | Quick Check, low-confidence, or stale states. |
| `--danger-bg`, `--danger-line`, `--danger` | Must Review, unsafe apply, or blocked final export. |
| `--neutral-bg`, `--neutral-line` | Raw source, trace-only, empty, disabled, or quiet state containers. |
| `--disabled-bg`, `--disabled-line`, `--disabled-ink` | Disabled controls with visible explanation nearby. |
| `--selected-bg`, `--selected-line` | Current selection without implying success. |
| `--ready-bg`, `--ready-line`, `--ready-ink` | Export-ready or action-ready surfaces. |
| `--blocked-bg`, `--blocked-line`, `--blocked-ink` | Blocked final export or unresolved high-risk review surfaces. |
| `--focus-ring` | Keyboard focus and progressbar focus outline. |

Visual asset rules:

- real source photos always outrank illustration, icon, and chart content;
- section-level illustrations are acceptable for orientation and empty states;
- repeated table rows should use text, chips, icons, and compact source links,
  not decorative image assets;
- generated bitmap illustrations must never represent real colony evidence;
- source-photo overlays should help inspect handwriting and must not distort
  evidence color or obscure note lines.

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

## Pattern Decision Matrix

Use this matrix when deciding how much UI feedback a state deserves.

| Situation | Preferred pattern | Avoid |
| --- | --- | --- |
| User selects a photo, row, review item, evidence item, or export row | Selected-row accent, stable detail drawer title, source/evidence context | Green success state or automatic scrolling that hides the source item |
| A field is parsed but not reviewed | Neutral `Parsed` chip, raw-vs-normalized display, confidence | Accepted styling or replacing raw text |
| A short user confirmation is needed | Amber `Quick Check` chip, inline bounded selector, concise reason | Modal unless the consequence is high-risk |
| Canonical write or final export is blocked | Red/amber blocker chip, disabled action reason, direct Focus Review link | Silent disabled button |
| A high-risk correction may change mouse identity, status, genotype, mating, litter, or death state | Before/after preview plus explicit confirmation step | Single-click apply or vague `Approve` button |
| Long-running upload, parse, AI draft, or export generation | Progress bar or stepper with current stage and partial success | Spinner with no detail |
| Known-shape content is loading | Skeleton matching final dimensions | Layout jump or empty white panel |
| Optional explanation is useful but not required | Tooltip, disclosure, or drawer | Permanent paragraph repeated on every row |
| User action succeeds but does not create canonical state | Short `Saved`, `Verified`, or `Draft updated` status | `Accepted` or green check without qualifying text |
| User action creates accepted canonical state | `Accepted` chip, action log/evidence link, updated counts | Hiding the before/after trail |

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
- photo-stage progress chips must not mark `Accepted/Held` or `Export` as
  complete until the reviewed canonical/apply path has actually succeeded.

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
- workbook preview rows should show text-backed row-state chips such as
  `Preview only`, `Ready`, `Blocked`, and source-trace labels without writing
  those UI labels into the exported workbook schema.

## Screen Acceptance Criteria

Use these checks when reviewing UI implementation.

Photo Review passes when:

- source photo or selected photo preview is visually primary;
- upload and parse progress show current stage and partial failures;
- raw values, normalized suggestions, confidence, and review state are visible
  together where decisions happen;
- external AI/OCR state is labeled as local-only, approval-needed, approved, or
  failed.

Focus Review passes when:

- every blocking item shows source evidence, issue, suggested value, and likely
  consequence;
- selected row state is distinct from verified or accepted state;
- resolving an item updates visible counts and leaves unresolved sibling items
  discoverable;
- high-risk corrections show before/after and require a deliberate apply step.

Evidence Ledger passes when:

- source photo, OCR text, note line, Excel row, review decision, accepted event,
  and export manifest are visually distinguishable;
- imported Excel rows are labeled as import/export views;
- evidence type is scannable before reading the full detail;
- source photos remain the strongest visual evidence for photo-derived values.
- evidence badges use text labels such as `Source photo`, `OCR text`,
  `Note line`, `Review item`, `Export manifest`, and `Validation report`;
- badge labels are UI cues only and must not be written into canonical records
  or exported workbook schemas.

Mouse Detail and Colony State pass when:

- accepted values are shown with source/evidence links;
- accepted-state pages do not contain detailed review decision controls;
- anomaly badges link to Focus Review instead of duplicating blocker detail;
- raw OCR and parser diagnostics are collapsed by default.

Excel Export passes when:

- readiness is shown before download actions;
- disabled final export actions explain why they are disabled;
- blocked rows link to the responsible review surface;
- preview grids look like export/views, not canonical editing tables;
- stale export state is visible before the user downloads.

## Accessibility And Safety

- Do not rely on color alone.
- Icon-only controls need accessible names and tooltips.
- Status changes should be screen-reader discoverable where practical.
- Avoid animations that obscure source evidence or delay repeated review work.

## Microcopy Rules

Use lab workflow language and describe consequence precisely. Prefer short,
actionable text over generic system language.

| Avoid | Prefer |
| --- | --- |
| `Approve` | `Save verified correction` |
| `Auto Fix` | `Apply suggested correction` |
| `Ignore` | `Dismiss with reason` |
| `Editable export` | `Preview only` |
| `Error` | `Needs review because...` |
| `Done` | `Saved draft`, `Verified`, or `Accepted` |
| `Artifact` | `Source photo`, `Evidence`, `Export file`, or `Validation report` |
| `Low risk` | `Needs quick confirmation` |
| `No problem` | `No Focus Review blockers` |
| `Ready` | `Export ready` or `Ready for review`, depending on consequence |

Rules:

- state what changed, what remains blocked, and where to act next;
- never imply inferred biological state is certain before review;
- mention `source photo`, `note line`, `mouse ID`, `mating`, `litter`,
  `genotype`, `review`, and `Excel export` in user-facing places where those
  terms match the lab workflow;
- avoid internal IDs unless the user opens diagnostics;
- use `Accepted` only when canonical state changed through the reviewed path.

## Implementation Slice Roadmap

Apply this guidance in small, reviewable slices.

1. Export action feedback: disabled final export buttons explain blockers or
   missing accepted export rows before the user clicks.
2. Review Queue selection feedback: selected item, detail drawer, next/previous
   controls, and resolve status update without implying acceptance.
3. Photo Review progress: batch/photo stepper for upload, quality, parse, review,
   candidate, accepted/held, and export readiness.
4. Export row state chips: `New`, `Update`, `No change`, `Blocked`, `Preview
   Only`, and stale export indicators in workbook previews.
5. Evidence type badges: source photo, OCR text, note line, Excel row, accepted
   event, and export manifest badges across Evidence Ledger and detail drawers.
6. Keyboard and focus pass: visible focus, icon labels, tooltip coverage, and
   reduced-motion checks for dense review workflows.

Each slice should include:

- the UI states changed;
- the data boundary shown by each new visual cue;
- the verification command or browser check used;
- screenshots only as generated verification artifacts unless explicitly
  adopted as documentation.

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
| `docs/ui_ux_implementation_tracker_2026-05-11.md` | Merged UI/UX slices, verification evidence, remaining gaps, and recommended next implementation slices. |
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
