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
