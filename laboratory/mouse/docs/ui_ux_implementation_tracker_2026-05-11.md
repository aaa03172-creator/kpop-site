# UI/UX Implementation Tracker

Layer classification: design guidance / non-canonical project tracking documentation.

Canonical: false.

This tracker connects the UI/UX guidance in `design.md` and
`docs/ui_interaction_visual_feedback_direction_2026-05-11_ko.md` to merged
implementation slices. It does not define product behavior, database schema,
API response shape, export schema, or lab workflow policy. When this tracker
disagrees with `AGENTS.md`, `final_mouse_colony_prd.md`, committed tests, or
runtime code, those sources win.

## Boundary Rules

- Source photos, note lines, Excel rows, review decisions, accepted events, and
  export manifests must remain visually distinguishable.
- UI cues may summarize review state, but they must not imply uncertain OCR,
  inferred biology, genotype interpretation, or colony state is accepted.
- Excel previews and export blockers remain `export or view` surfaces, not
  canonical editing surfaces.
- Review Queue and Focus Review cues remain review-item surfaces until a
  reviewed apply path changes canonical structured state.
- Generated screenshots, temporary logs, and local browser artifacts remain
  generated artifacts unless explicitly adopted as documentation.

## Merged UI/UX Slices

| Slice | Guidance covered | Merged PR | Verification captured |
| --- | --- | --- | --- |
| Interaction and visual feedback direction | Defines icons/chips/progress/status-cue guidance, brand/color direction, tools, and acceptance criteria. | [#111](https://github.com/aaa03172-creator/mouse-colony/pull/111) | Documentation links in `design.md`, `docs/DOCUMENTATION_MAP.md`, and `final_mouse_colony_prd.md`. |
| Disabled final export feedback | Final export actions explain blockers or missing accepted source-backed rows before download. | [#113](https://github.com/aaa03172-creator/mouse-colony/pull/113) | `npm test`, `npm run test:local`, browser check of disabled buttons and `aria-describedby`. |
| Disabled export feedback contract | Guards the export disabled-reason contract after #113. | [#115](https://github.com/aaa03172-creator/mouse-colony/pull/115) | `scripts/verify-mvp.js` checks disabled reason, ARIA link, and accepted-row guidance. |
| Upload and extraction progress feedback | Shows batch/photo operation progress as visible progressbar, percent, and state-specific cues. | [#118](https://github.com/aaa03172-creator/mouse-colony/pull/118) | `npm test`, `npm run test:local`, Playwright DOM check for progressbar role, percent, and queued/extracting cues. |
| Review Queue status cues | Adds non-color-only symbols and consequence copy for Focus Review, quick confirmation, trace-only, and fallback states. | [#125](https://github.com/aaa03172-creator/mouse-colony/pull/125) | `npm test`, `npm run test:local`, Playwright DOM check for symbol, `aria-hidden`, consequence copy, and attention class. |
| Export blocker review links | Links source-backed Export Center blockers back to the responsible Review Queue item. | [#131](https://github.com/aaa03172-creator/mouse-colony/pull/131) | `npm test`, `npm run test:local`, Playwright DOM check for blocker buttons and Review Queue navigation. |

## Current Coverage By Guidance Area

| Guidance area | Current status | Evidence | Remaining gap |
| --- | --- | --- | --- |
| Export action feedback | Implemented and guarded, with row-level preview chips, direct evidence links for blockers without review items, and row-level anchors for preview evidence links. | #113, #115, #131 plus export preview row-state chip, direct evidence-link, and row-anchor implementations. | Add anchors for future tables when their backend payloads expose durable IDs. |
| Upload / extraction progress | Implemented for upload/extraction operation progress and visible photo-stage progress from source stored through export ready/blocked. | #118 plus photo-stage progress UI implementation. | Add later quality/OCR confidence sub-stages if the parse pipeline exposes stable quality signals. |
| Review status cues | Implemented for Review Queue cards and after-action follow-through when a review is resolved. | #125 plus resolved review follow-through implementation. | Keep expanding repeated-review ergonomics when new review actions are introduced. |
| Export blocker navigation | Implemented for blockers with `review_id`, and for blocker warnings that only expose source photo, note-line, or artifact evidence. | #131 plus direct evidence-link UI implementation. | Extend link targeting if future blocker payloads add stable row-level anchors inside note/evidence tables. |
| Brand and color direction | Semantic token foundation implemented for chips, status pills, selected rows/cards, disabled controls, ready/blocked states, progress, and focus rings. | #111 plus `static/index.html` and `index.html` token aliases. | Extend the same token vocabulary to future row-state chips and evidence badges as those slices land. |
| Empty/loading/error state | Implemented for read-model panels, high-traffic table empty states, and lower-priority settings/reference/audit tables. | #111, #137, #140 plus audit/detail table polish. | Extend the same state-message pattern to any newly added tables when those screens are introduced. |
| Evidence type badges | Implemented for Evidence Ledger cards, Focus Review detail source panels, Export Log artifact cells, and audit trace evidence cells, with row anchors for note and ledger evidence. | #111 plus evidence badge UI, audit/detail table polish, and row-anchor implementations. | Add anchors for future audit payloads when stable deep-link targets exist. |
| Keyboard and focus pass | Implemented for high-traffic photo review, Review Queue, export blockers, and export artifact controls. | #111 plus keyboard/focus UI implementation. | Extend the same contract to lower-priority settings/reference tables when those screens are next touched. |

## Recommended Next Slices

1. Evidence anchor expansion.
   - Scope: add the same anchor contract to future audit/detail rows when those
     payloads expose durable IDs.
   - Boundary: export or view navigation only.
   - Verification: DOM checks that anchors highlight rows without changing
     canonical state.

2. Review completion summaries.
   - Scope: aggregate session-level review completion summaries by source photo,
     role, or blocker type after multiple review actions.
   - Boundary: review-item UI summary behavior only.
   - Verification: DOM checks that summaries use accepted review action logs
     and do not imply canonical writes before apply.

## Current Foundation Slice

| Slice | Scope | Verification target |
| --- | --- | --- |
| Semantic color token consolidation | Adds shared CSS variables for focus, selected, processing, success, warning, danger, disabled, ready, and blocked states; rewires high-traffic status, progress, review, and export readiness styles to those variables. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and a DOM/CSS check for token-backed selected/blocked/ready/status classes. |
| Export preview row-state chips | Adds text-backed chips such as `Preview only`, `Ready` or `Blocked`, and source trace indicators to workbook preview rows without changing export schemas or canonical records. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and DOM checks that preview chips render while final export gating remains enforced. |
| Evidence badge pass | Adds consistent text-backed badges for source photo, OCR text, note line, review item, export manifest, and validation report evidence in high-traffic review/export surfaces. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and DOM checks for badge text in Evidence Ledger, Focus Review detail, and Export Log. |
| Photo-stage progress expansion | Adds per-photo stage chips for `Uploaded`, `Parse/OCR`, `Review`, `Candidate`, `Accepted/Held`, and `Export`, using blocked/held states without implying canonical acceptance early. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and DOM checks for stage labels and blocked/held/done classes. |
| Keyboard and focus pass | Adds consistent focus-visible treatment, `aria-current` state, and specific accessible names for high-traffic photo review, Review Queue, export blocker, and artifact preview actions. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and Playwright DOM checks for focus-within/current-state/action-name contracts. |
| Export blocker evidence links | Adds source photo, parsed note, and artifact preview actions for Export Center blockers that do not have a Focus Review `review_id`, while keeping final export gating unchanged. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and Playwright DOM checks for evidence-link navigation and artifact preview loading. |
| Audit/detail table polish | Extends structured empty states to lower-priority settings, reference, correction, audit, action log, genotype, parsed evidence, snapshot, and event tables; adds badge-backed audit trace evidence cells. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and DOM checks for structured empty states plus audit trace badge contracts. |
| Row-level evidence anchors | Adds stable DOM anchors for parsed note evidence, Evidence Ledger cards, and export preview rows; export preview trace links can highlight note or ledger evidence without mutating data. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and Playwright DOM checks for hash navigation, view switching, and anchor targets. |
| Resolved review follow-through | Adds a live after-action status after review resolution that names the resolved item, next review item, and source-evidence context while keeping the Review Queue filter state intact. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and DOM checks for success status, next-item context, and backend guard failure behavior. |

## Verification Commands To Prefer

- `git diff --check origin/main..HEAD`
- `npm test`
- `npm run test:local`
- `npm run verify` when the slice touches broader runtime behavior.
- A local Playwright or browser check when visible UI behavior changes.

## PR Hygiene Checklist

- Classify any new file, table, artifact, or response shape before changing it.
- Keep source photos and note-line evidence traceable from UI actions.
- Avoid final-export actions that are enabled without accepted source-backed rows.
- Never make Excel preview rows look like canonical editable records.
- Stage only files that belong to the current slice.
- Delete disposable screenshots, logs, `node_modules/`, and other generated
  verification artifacts before commit.
