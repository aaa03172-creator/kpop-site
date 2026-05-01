# Mouse Colony LIMS Design Notes

## Document Status

Layer classification: design guidance / non-canonical product documentation.

This document summarizes the proposed UI direction for the mouse colony management system. It does not define canonical database tables or final response shapes. Canonical product behavior should continue to follow `final_mouse_colony_prd.md` and adopted project documents.

Related non-canonical reference note:

- `reference_adoption_notes.md` summarizes development, design, and external tooling references that can inform implementation without replacing the PRD.

## Design Intent

The product should feel like a careful lab workflow tool, not a generic analytics dashboard. The main job is to preserve handwritten cage card evidence, turn clear values into structured records, and route uncertain or conflicting values to review.

The UI should reinforce these principles:

- handwritten cage card photos are raw evidence;
- OCR and AI output are parsed or intermediate results;
- accepted records are canonical structured state;
- uncertain, conflicting, or biologically unlikely items are review items;
- Excel files are exports or views;
- every important value should be traceable back to a photo, note line, or imported Excel row.

## Primary Workflows

### 1. Photo Upload And Processing

Goal: let the user upload cage card photos after normal animal facility work.

Expected UI:

- upload entry point in the top bar or Photo Inbox;
- processing status per photo;
- quality indicators such as blurry, cropped, glare, low confidence, or missing note area;
- source photo retained even when parsing quality is poor;
- parsing status shown separately from review status.

Recommended states:

| State | Meaning |
| --- | --- |
| Uploaded | Raw source photo is stored. |
| Processing | OCR/ROI extraction is running. |
| Parsed | Fields were extracted into intermediate results. |
| Auto-filled | Clear fields were inserted into draft or structured records. |
| Needs Review | Low-confidence or conflicting values require user action. |
| User Corrected | User changed an extracted or normalized value. |
| Verified | User confirmed a reviewed value. |

### 2. Photo Inbox

Goal: show recently parsed card photos and make raw/normalized values easy to compare.

Recommended layout:

- dense table on the left;
- card preview and extracted fields on the right;
- raw field values and normalized suggestions shown side by side;
- confidence shown per parsed field, not only per photo;
- proposed actions shown as suggestions, not silent changes.

Important columns:

- source photo thumbnail;
- uploaded or captured time;
- inferred card type;
- raw strain text;
- matched strain;
- DOB raw or normalized DOB range;
- sex/count;
- note-line status;
- confidence;
- review status;
- issue count.

Use explicit labels:

- `Raw Text`
- `Matched Strain`
- `Normalized DOB`
- `Parsed Note Lines`
- `Proposed Actions`
- `Source Photo`

Avoid presenting inferred values as final unless they are verified or clearly auto-filled with high confidence.

### 3. Review Queue

Goal: resolve only the items that are low-confidence, conflicting, or high-risk.

Recommended layout:

- source image pane with ROI highlight;
- issue summary pane;
- extracted value, current canonical value, and suggested value;
- before/after preview before applying a correction;
- queue progress and next/previous controls.

High-priority review examples:

- duplicate active mouse ID;
- dead mouse appears active again;
- count mismatch between sex/count and active note lines;
- genotype outside configured categories;
- raw strain not found in strain master;
- biologically unlikely date.

Button language should be careful:

| Avoid | Prefer |
| --- | --- |
| Approve & Execute | Apply Reviewed Changes |
| Mark as Verified | Save Verified Correction |
| Ignore Issue | Dismiss With Reason |
| Auto Fix | Apply Suggested Correction |

The UI should not pressure the user to accept inferred biological or colony-state data without review.

### 4. Colony Records

Goal: manage canonical mouse and card snapshot records while keeping traceability visible.

Recommended layout:

- dense mouse table;
- side drawer for selected mouse;
- source card/photo link visible in both table and drawer;
- status, genotype status, current card snapshot, and last action;
- history shown as event timeline.

Important distinction:

- Mouse records are durable canonical state.
- Card records are snapshots.
- Note item rows are line-level parsed evidence from source photos.
- Movement, death, mating assignment, litter, and genotype changes are events.

Avoid making internal IDs prominent. User-facing continuity should be based on:

- mouse display ID;
- note-line evidence;
- source card photo;
- strain;
- DOB range;
- ear label raw notation and normalized code;
- current card snapshot.

### 5. Record Detail / Source Evidence

Goal: let the user audit why a record exists and where its values came from.

Recommended layout:

- source photo with ROI overlays;
- parsed text lines;
- structured fields;
- audit trail;
- related mating/litter/genotyping records;
- export preview where useful.

Each important structured field should show at least one trace indicator:

- source photo;
- parsed field or ROI;
- note line;
- confidence;
- last user correction;
- last action log event.

### 6. Export Center

Goal: generate familiar Excel outputs from structured records.

Expected export types:

- separation workbook;
- animalsheet;
- handoff or dashboard summary;
- future custom views.

Export cards should show:

- readiness;
- blocked review item count;
- record count;
- last generated time;
- template or format name;
- preview action;
- generate action.

Excel exports must be framed as views, not the source of truth. Export history should be visible and stale or failed exports should be obvious.

### 7. Settings

Goal: configure strain, genotype, OCR alias, and management rules without hard-coding domain logic.

Recommended sections:

- Strain Master;
- OCR Aliases;
- Genotype Categories;
- Management Rules;
- Ear Label Normalization;
- Status Mapping;
- Card Type Rules;
- Export Templates.

Settings should make it clear that strain names, genotype categories, date rules, ear label aliases, and protocols are configurable. Unknown parsed values should create review items instead of silently becoming new canonical values. Ear label settings should preserve the lab's handwritten symbols as raw evidence while mapping accepted forms to explicit codes such as `R_PRIME`, `R_CIRCLE`, and `NONE`.

### 8. Mating & Litters

Goal: represent breeding history as events, not as static cage rows.

Recommended layout:

- mating card list grouped by strain or active card snapshot;
- parent IDs, mating date, litter note lines, pup counts, and separation/death status;
- timeline of litter events parsed from note lines;
- source photo and note-line links for each event;
- review indicators for missing parent IDs, unlikely dates, or count mismatches.

Important design rule:

- A mating card is a source snapshot.
- A litter line is structured evidence.
- A litter, separation, death, or movement is an event.

Avoid turning `F1`, `F2`, pup-count rows, or crossed-out note lines into independent mouse records unless the source evidence supports that interpretation.

### 9. Genotyping

Goal: connect genotyping sheets and results to mouse IDs without forcing uncertain matches.

Recommended layout:

- post-separation genotyping workflow cards;
- not sampled / awaiting result / ambiguous / target confirmed / non-target / review needed counts;
- sample/result table;
- mouse ID matching status;
- ear label and DOB context beside mouse ID candidates;
- configured genotype category;
- strain target genotype setting;
- raw band/result text;
- final interpreted genotype;
- suggested use category and next action;
- source sheet or photo link;
- unmatched sample review queue.

Genotype results should show whether they are:

- pending;
- matched to a mouse;
- confirmed;
- user corrected;
- outside configured categories;
- blocked by missing mouse ID.

When a genotype result is outside the configured categories for a strain, the UI should send it to review and offer a path to add a legitimate category in Settings.

The UI should suggest maintenance, mating, experiment, backup, cleanup, or review categories from strain-level target genotype settings, but the suggestion must not override human judgment. Mouse detail and the genotyping worklist should keep sample ID, ear label, genotype result, target match, and next action visible together.

## Navigation

Recommended top-level navigation:

- Dashboard
- Photo Inbox
- Review Queue
- Colony Records
- Mating & Litters
- Genotyping
- Exports
- Settings

For MVP, prioritize:

1. Photo Inbox
2. Review Queue
3. Colony Records
4. Exports
5. Settings
6. Mating & Litters
7. Genotyping
8. Dashboard

Dashboard is still part of MVP, but it should support work rather than drive the information architecture. Prefer review and workflow metrics over broad analytics.

## Dashboard Direction

Dashboard should summarize operational workload:

- photos uploaded today/recently;
- auto-filled records;
- pending review;
- high-severity conflicts;
- age warnings from configured rules;
- genotype pending or unknown;
- blocked exports;
- open mating/litter events.

Charts such as active mice by strain are useful, but should not dominate the MVP. The first screen should help the user decide what needs attention now.

## Visual System

The proposed visual direction is appropriate:

- dense operational layout;
- restrained clinical palette;
- compact tables;
- right-side evidence/review drawers;
- minimal rounded corners;
- clear status badges;
- source image thumbnails and ROI overlays.

Recommended tone:

- quiet;
- precise;
- evidence-oriented;
- low decoration;
- optimized for scanning and repeated daily use.

Status colors should be consistent:

| Status Type | Suggested Treatment |
| --- | --- |
| Auto-filled / valid | muted green or teal |
| Needs review / warning | amber or tertiary |
| High severity / conflict | red |
| Processing / neutral | gray or surface variant |
| Verified | teal with check icon |

Use icons for compact repeated actions:

- upload;
- export/download;
- review;
- source photo;
- history;
- settings;
- warning;
- verified;
- edit.

## Data Boundary Labels

Where space allows, screens should label the layer being shown:

| UI Area | Data Boundary |
| --- | --- |
| Source photo viewer | Raw source |
| OCR text and ROI fields | Parsed or intermediate result |
| Mouse table and record detail | Canonical structured state |
| Review queue item | Review item |
| Excel preview/export center | Export or view |
| Search results or derived summaries | Cache or view, unless defined otherwise |

These labels do not need to be large. Small chips or section captions are enough.

Recommended screen-level boundaries:

| Screen | Primary Boundary |
| --- | --- |
| Photo Inbox | raw source plus parsed or intermediate result |
| Review Queue | review item |
| Colony Records | canonical structured state |
| Record Detail | canonical structured state plus raw source evidence |
| Mating & Litters | event history plus card snapshot evidence |
| Genotyping | parsed result plus canonical genotype update |
| Export Center | export or view |
| Settings | canonical configuration state |
| Dashboard | view or cache |

## Traceability Requirements In UI

Every high-value field should answer:

- where did this value come from?
- was it raw, normalized, or user-corrected?
- what was the confidence?
- what changed before/after?
- which photo, note item, or Excel row supports it?

Especially important fields:

- mouse ID;
- strain;
- genotype;
- sex;
- DOB;
- death status;
- current card/location;
- mating assignment;
- litter count.

## OCR And External Inference Safety

If external OCR, LLM, or inference services are used, the UI should expose processing safety at least in system status or photo detail:

- local-only;
- external OCR used;
- redacted payload used;
- full source sent with approval;
- processing failed.

When in doubt, keep payloads local-only until the user approves.

## Failure And Recovery UX

The UI should expose failure paths instead of hiding them in logs.

High-risk failure states:

- photo uploaded but parsing failed;
- OCR finished but no card snapshot was created;
- card snapshot created but mouse/event updates failed;
- proposed action created duplicate mouse records;
- review correction changed a value but did not create an action log;
- export generated from stale data;
- Excel import created unmatched rows;
- external OCR or inference failed after partial local processing.

Recommended UI behavior:

- show partial success explicitly;
- keep failed items retryable;
- never delete source photos because parsing failed;
- surface orphan records as review items;
- show stale export warnings;
- block high-risk apply actions when required before/after data is missing;
- provide a visible action log entry for every accepted correction.

Suggested labels:

| State | Meaning |
| --- | --- |
| Parse Failed | Source stored, extraction failed. |
| Partial Draft | Some parsed fields saved, structured update incomplete. |
| Needs Reconcile | Parsed data and canonical records do not fully match. |
| Export Stale | Export is older than the latest accepted correction. |
| Import Unmatched | Excel row could not be linked confidently. |

## Excel Import UX

Excel import should be treated as another source view, not as authoritative replacement data.

Recommended flow:

1. Import workbook.
2. Preserve original file and row references.
3. Parse rows into intermediate import results.
4. Match rows to existing mouse IDs, card snapshots, mating events, or genotype records.
5. Send unmatched, conflicting, or high-risk rows to review.
6. Apply accepted changes with before/after action log entries.

Imported rows should show:

- workbook name;
- sheet name;
- row number;
- raw row values;
- matched canonical record;
- confidence;
- review status.

Do not silently overwrite source-photo-derived values with Excel import values.

## Content And Language Guidelines

Use lab workflow language:

- photos;
- cage cards;
- mouse IDs;
- mating;
- litter;
- genotype;
- review;
- Excel export;
- source evidence;
- parsed note lines.

Avoid implementation language in normal UI:

- internal UUID;
- system cage ID;
- database row;
- hidden record key.

Card ID and cage terminology should stay precise:

- `card_id_raw` is the raw text written in the cage card I.D field;
- `card_snapshot` is the observed state from a photo or imported row;
- `cage_label` is optional if a user or workbook has a human-readable cage label;
- internal record IDs should stay hidden unless needed for debugging.

Do not label the handwritten cage card I.D field as a stable physical cage ID.

Use cautious language for inferred state:

- `Suggested`
- `Likely match`
- `Needs review`
- `Proposed action`
- `Apply reviewed changes`

Do not imply that the system knows more than the source evidence supports.

## Review Interaction Patterns

Review screens should keep the user oriented around evidence and consequence.

Each review item should show:

- issue type;
- severity;
- source photo or Excel row;
- raw extracted value;
- current canonical value;
- suggested value;
- confidence;
- proposed action;
- before/after effect;
- reason the item was sent to review.

For high-risk corrections, require an explicit reviewed apply step. High-risk fields include:

- mouse ID;
- genotype;
- sex;
- DOB;
- death status;
- current active card;
- mating assignment;
- litter count;
- strain mapping.

Review resolution actions should be auditable:

- apply suggested correction;
- edit and apply;
- dismiss with reason;
- split duplicate records;
- merge records;
- create new strain alias;
- escalate for later review.

## Screen Set Recommendation

From the reviewed mockups, the strongest MVP set is:

- Dashboard Revised, with more review/workflow emphasis;
- Photo Inbox Revised;
- Colony Records Revised;
- Record Detail Revised;
- Review Queue Revised;
- Export Center Revised;
- Settings Revised.

The earlier mockups are useful references, but the revised set better matches the PRD because it focuses on source photos, review, traceability, and Excel export.

Additional screens still need dedicated mockups:

- Mating & Litters event view;
- Genotyping sample/result matching view;
- Excel import reconciliation view.

Until those mockups exist, related information should appear through Record Detail, Review Queue, and Export Center without pretending those substitute for the full workflows.

## Known Design Risks

### Hard-coded domain examples

Mockups currently include many strain and genotype examples. These are acceptable as sample data, but final implementation should load them from configurable masters.

Risk mitigation:

- show sample data only in fixtures;
- build UI labels around `Strain Master`, `Matched Strain`, and `Configured Genotype Category`;
- route unknown values to review.

### Inferred actions look too automatic

Some buttons imply immediate execution of biological or colony-state changes.

Risk mitigation:

- show before/after;
- require user confirmation for high-risk changes;
- create action log entries;
- keep source evidence visible during confirmation.

### Dashboard decoration

Broad metrics may distract from the main workflow.

Risk mitigation:

- prioritize review queue, conflict, pending genotype, age warning, and export readiness;
- keep charts secondary.

### Raw and normalized values blur together

If raw values and normalized values share the same visual treatment, users may not know what was actually written.

Risk mitigation:

- preserve raw text;
- label normalized values;
- show confidence and source;
- keep corrections auditable.
- treat ear label prime/circle ambiguity as identity-critical and send low-confidence cases to review.

### Mating and genotyping are under-modeled

If these workflows are represented only as table columns, the app may lose the event history that matters for colony continuity.

Risk mitigation:

- model mating/litter/genotyping as events linked to source evidence;
- show event timelines in record detail;
- avoid treating litter rows as independent animals unless mouse IDs are present.

### Excel import/export appears authoritative

Users may assume a workbook row is the database state.

Risk mitigation:

- label Excel screens as import/export views;
- preserve row references;
- require review before high-risk overwrites;
- show export stale warnings.

## MVP Design Acceptance Checklist

- Source photos are always visible or one click away.
- Raw extracted values are not overwritten by normalized values.
- Low-confidence fields show confidence and review state.
- Ear label raw notation and normalized code are shown separately when used for mouse identity.
- Review items show source evidence, suggested value, and before/after.
- High-risk changes require explicit reviewed application.
- Internal IDs are hidden from normal users.
- Strain, genotype, protocol, and date rules are configurable.
- Excel export is presented as an output/view.
- Excel import is treated as parsed source input, not canonical truth.
- Mating, litter, movement, death, and genotyping changes are represented as events.
- Failed or partial processing states are visible and retryable.
- Duplicate, orphan, and stale records are routed to review.
- Export history and blocked exports are visible.
- Every accepted correction creates traceable history.
