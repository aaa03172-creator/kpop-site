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
| Export action feedback | Implemented and guarded, with row-level preview chips for workbook preview state. | #113, #115, #131 plus export preview row-state chip implementation. | Add direct evidence links for blockers that have source photo or note-line evidence but no review item. |
| Upload / extraction progress | Implemented for upload/extraction operation progress and visible photo-stage progress from source stored through export ready/blocked. | #118 plus photo-stage progress UI implementation. | Add later quality/OCR confidence sub-stages if the parse pipeline exposes stable quality signals. |
| Review status cues | Implemented for Review Queue cards. | #125. | Improve resolved/after-action feedback and keyboard next/previous cues for repeated review work. |
| Export blocker navigation | Implemented for blockers with `review_id`. | #131. | Add direct evidence links for blockers that have source photo or note-line evidence but no review item. |
| Brand and color direction | Semantic token foundation implemented for chips, status pills, selected rows/cards, disabled controls, ready/blocked states, progress, and focus rings. | #111 plus `static/index.html` and `index.html` token aliases. | Extend the same token vocabulary to future row-state chips and evidence badges as those slices land. |
| Empty/loading/error state | Implemented for read-model panels and high-traffic table empty states. | #111, #137, #140. | Extend the same state-message pattern to lower-priority settings/reference tables when those screens are next touched. |
| Evidence type badges | Implemented for Evidence Ledger cards, Focus Review detail source panels, and Export Log artifact cells. | #111 plus evidence badge UI implementation. | Extend badges to lower-priority audit/detail tables when those screens are next touched. |
| Keyboard and focus pass | Implemented for high-traffic photo review, Review Queue, export blockers, and export artifact controls. | #111 plus keyboard/focus UI implementation. | Extend the same contract to lower-priority settings/reference tables when those screens are next touched. |

## Recommended Next Slices

1. Direct evidence links for export blockers without `review_id`.
   - Scope: Export Center blockers that still have source photo, note-line, or
     artifact evidence but no Focus Review item.
   - Boundary: export or view navigation only.
   - Verification: DOM checks that the links preserve traceability and do not
     enable final export actions.

2. Lower-priority audit/detail table polish.
   - Scope: settings/reference/audit tables that were intentionally left out
     of the high-traffic UI pass.
   - Boundary: UI readability and accessibility behavior only.
   - Verification: DOM checks for state messages, evidence badges, and
     focus-visible controls where rows have actions.

## Current Foundation Slice

| Slice | Scope | Verification target |
| --- | --- | --- |
| Semantic color token consolidation | Adds shared CSS variables for focus, selected, processing, success, warning, danger, disabled, ready, and blocked states; rewires high-traffic status, progress, review, and export readiness styles to those variables. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and a DOM/CSS check for token-backed selected/blocked/ready/status classes. |
| Export preview row-state chips | Adds text-backed chips such as `Preview only`, `Ready` or `Blocked`, and source trace indicators to workbook preview rows without changing export schemas or canonical records. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and DOM checks that preview chips render while final export gating remains enforced. |
| Evidence badge pass | Adds consistent text-backed badges for source photo, OCR text, note line, review item, export manifest, and validation report evidence in high-traffic review/export surfaces. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and DOM checks for badge text in Evidence Ledger, Focus Review detail, and Export Log. |
| Photo-stage progress expansion | Adds per-photo stage chips for `Uploaded`, `Parse/OCR`, `Review`, `Candidate`, `Accepted/Held`, and `Export`, using blocked/held states without implying canonical acceptance early. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and DOM checks for stage labels and blocked/held/done classes. |
| Keyboard and focus pass | Adds consistent focus-visible treatment, `aria-current` state, and specific accessible names for high-traffic photo review, Review Queue, export blocker, and artifact preview actions. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and Playwright DOM checks for focus-within/current-state/action-name contracts. |

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
