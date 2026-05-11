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
| Export action feedback | Implemented and guarded. | #113, #115, #131. | Add row-level preview chips such as `New`, `Update`, `Blocked`, and `Preview only`. |
| Upload / extraction progress | Implemented for upload/extraction operation progress. | #118. | Expand from operation progress to full photo-stage progress: quality, parse, review, candidate, accepted/held, export ready/blocked. |
| Review status cues | Implemented for Review Queue cards. | #125. | Improve resolved/after-action feedback and keyboard next/previous cues for repeated review work. |
| Export blocker navigation | Implemented for blockers with `review_id`. | #131. | Add direct evidence links for blockers that have source photo or note-line evidence but no review item. |
| Brand and color direction | Semantic token foundation implemented for chips, status pills, selected rows/cards, disabled controls, ready/blocked states, progress, and focus rings. | #111 plus `static/index.html` and `index.html` token aliases. | Extend the same token vocabulary to future row-state chips and evidence badges as those slices land. |
| Empty/loading/error state | Implemented for read-model panels and high-traffic table empty states. | #111, #137, #140. | Extend the same state-message pattern to lower-priority settings/reference tables when those screens are next touched. |
| Evidence type badges | Documented but not fully implemented across surfaces. | #111. | Add consistent badges for source photo, OCR text, note line, Excel row, accepted event, export manifest, and validation report. |
| Keyboard and focus pass | Documented. | #111. | Run a focused keyboard traversal pass through upload, review, export blockers, and detail drawers. |

## Recommended Next Slices

1. Export preview row-state chips.
   - Scope: workbook preview rows only; no canonical editing.
   - Boundary: export or view.
   - Verification: `npm test`, `npm run test:local`, checks that final export
     remains blocked while review blockers exist.

2. Evidence badge pass.
   - Scope: Evidence Ledger, Review detail, Export log, and source photo panels.
   - Boundary: raw source, parsed/intermediate result, review item, canonical
     structured state, and export/view must remain visually separate.
   - Verification: targeted DOM checks for badge text and source links.

3. Photo-stage progress expansion.
   - Scope: visible photo-stage progress from source stored through parse,
     review, candidate preparation, accepted/held, and export ready/blocked.
   - Boundary: UI display over raw source, parsed/intermediate result, review
     item, canonical structured state, and export/view layers.
   - Verification: `npm test`, `npm run test:local`, plus browser checks that
     progress labels do not imply canonical acceptance before review.

4. Keyboard and focus pass.
   - Scope: upload, review, export blockers, and detail drawers.
   - Boundary: UI accessibility behavior only.
   - Verification: keyboard traversal check and DOM checks for focus-visible
     states and non-color-only labels.

## Current Foundation Slice

| Slice | Scope | Verification target |
| --- | --- | --- |
| Semantic color token consolidation | Adds shared CSS variables for focus, selected, processing, success, warning, danger, disabled, ready, and blocked states; rewires high-traffic status, progress, review, and export readiness styles to those variables. | `git diff --check origin/main..HEAD`, `npm test`, `npm run test:local`, and a DOM/CSS check for token-backed selected/blocked/ready/status classes. |

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
