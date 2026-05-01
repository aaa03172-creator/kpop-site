# Mouse Colony Management System PRD

## Document References

Adopted project documents:

- `AGENTS.md`: project agent guidelines and safety boundaries.
- `design.md`: non-canonical UI and workflow design guidance.
- `reference_adoption_notes.md`: non-canonical reference adoption notes for development, design, and external tooling ideas.
- `mvp_vertical_slice_plan.md`: non-canonical implementation planning note for the first end-to-end workflow.

## 1. Product Summary

This product is a personal mouse colony management system for a researcher who must manage assigned mouse strains using the lab's existing handwritten cage cards and Excel-based records.

The system does not replace the lab workflow. Researchers will continue writing cage cards by hand in the animal facility and maintaining the lab's familiar Excel formats. The product adds a structured layer on top:

1. Upload photos of handwritten cage cards and related paper records.
2. Automatically parse the card contents.
3. Auto-fill mouse, cage/card, mating, litter, genotype, and event records.
4. Run validation checks to catch likely errors.
5. Send only uncertain or conflicting items to a review queue.
6. Export/update records in the existing lab Excel formats.

The intended first version is for the user's own assigned strains, but the design must not hard-code strain names, genotype categories, protocols, or date rules.

## 2. Background And Current Workflow

The lab currently manages mouse colony data through a combination of:

- Handwritten cage cards attached to separated cages and mating cages.
- A separation workbook, currently represented by the lab's `분리.xlsx` style file, for separated/stock cage summaries.
- An `animalsheet` style workbook for mating cage and breeding history.
- Separate handwritten or printed genotyping sheets.
- Informal notes, strike-through marks, and manually updated cage cards.

The user is newly assigned to manage mouse strains and wants a practical system that reduces errors in:

- dates,
- mouse counts,
- strain/genotype tracking,
- mating and separation timing,
- mouse movement history,
- Excel transcription.

The animal facility workflow is constrained:

- Direct app use inside the animal room may be difficult.
- QR code or barcode adoption is not realistic initially.
- Handwritten cage cards will continue to be the primary source.
- The user can take photos after writing cards and upload them later.
- Existing Excel formats should remain usable for lab sharing.

## 3. Core Product Philosophy

The system is not primarily a "cage inventory table." It is a photo-grounded colony state-change tracking system.

Core principles:

- Preserve the handwritten source record.
- Auto-fill by default.
- Review only low-confidence or logically conflicting items.
- Keep raw values and normalized values separate.
- Treat note lines and strike-throughs as structured data.
- Track state changes as events.
- Treat Excel files as outputs/views, not the only source of truth.
- Avoid hard-coded strain, genotype, and protocol logic.

## 4. Important Domain Clarifications

### 4.1 Cage Card I.D Is Not A Stable Cage ID

The handwritten cage card has only one `I.D` field. In actual use, this field may contain:

- an ID prefix such as `MT`,
- parent mouse IDs,
- individual mouse IDs,
- a loose group identifier,
- or may be empty while the note section contains the real mouse IDs.

Therefore, the system must not treat the card's `I.D` field as a stable physical Cage ID.

### 4.2 Do We Need A `system_cage_id`?

The user-facing product does not need to expose a separate `system_cage_id`.

However, the underlying database or workbook implementation will still need a stable internal key for a card snapshot. This can be a generic row identifier such as `record_id`, `card_snapshot_id`, or a hidden database UUID. It should not become a visible operational concept that the user has to manage.

Recommended terminology:

- `card_id_raw`: the raw text from the cage card `I.D` field.
- `mouse_display_id`: the mouse ID as written by the researcher, for example `318`, `MT318`, `GH70`.
- `card_snapshot`: a system record representing one observed cage card state at a point in time.
- `cage_label`: optional human-readable label if the user or Excel sheet has a cage number.
- `record_id`: internal implementation key only.

The system should identify and connect cage/card states using:

- source photo,
- strain,
- DOB,
- sex/count,
- active mouse list,
- mating date if present,
- note lines,
- and previous history.

### 4.3 Mouse ID Is More Important Than Cage ID

Mouse IDs and note-line IDs are the strongest continuity anchors. Cage/card records can change whenever mice are separated, moved, or assigned to mating. A mouse can appear in multiple cage/card records over time.

### 4.4 Cage/Card Records Are Snapshots

A cage/card record represents a state observed from a photo or an Excel row. It is useful for current status and export, but the durable history comes from events:

- created,
- born,
- separated,
- moved,
- assigned_to_mating,
- litter_recorded,
- genotyped,
- dead,
- used,
- closed,
- updated.

## 5. Current Lab Data Sources

### 5.1 Separation Workbook

The `분리.xlsx` style workbook is a cage summary format. It typically records separated or stock cages by researcher/sheet.

Common structure:

- cage number or row grouping,
- strain,
- genotype,
- sex/count,
- DOB,
- genotype count columns,
- usage/status/note columns.

This workbook is not ideal as the primary database because it is a summary view. It should be generated or updated from structured records where possible.

### 5.2 Animalsheet Workbook

The `animalsheet` style workbook is closer to a mating/breeding history log.

Common structure:

- cage or strain block,
- sex,
- ID,
- genotype/status,
- DOB,
- mating date,
- pup/litter records,
- place.

Rows such as `F1`, `F2`, `separated`, and pup counts represent litter/separation batches from a mating cage. These should be treated as breeding events rather than individual mouse rows.

### 5.3 Cage Card Photos

Blue cage cards contain fields such as:

- `Strain`,
- `Sex`,
- `D.O.B`,
- `I.D`,
- `Mating date`,
- `LMO` / `O/N` or similar lab-specific checkbox,
- `Note`.

The card type must be inferred from the fields:

- A mating card usually has a mating date and parent IDs.
- A separated/stock card usually has note lines listing mouse IDs and ear labels.

### 5.4 Genotyping Sheets

Genotyping sheets may include:

- sample numbers,
- PCR target,
- primer/mix conditions,
- band sizes,
- final genotype/result.

These records should link to mouse IDs where possible and update genotype status.

### 5.5 Distribution / Assignment Workbook

The user may periodically receive a distribution workbook such as `20260407 의대 수의대 분배현황표.xlsx`.

This workbook is not an animal state export. It is an assignment and planning source that says who is responsible for which mating types and how many cages are assigned or expected.

Observed structure from the current example:

- one `Mating` sheet;
- repeated column blocks for institution/group sections such as `수의대` and `의대`;
- each block contains responsible person, `mating 종류`, `Cage 갯수`, and `mating cage 개수`;
- merged person cells indicate that multiple mating types belong to one responsible person or group;
- total or subtotal values may appear in the `mating cage 개수` column.

The system should treat this file as raw source evidence first. Rows from this workbook may create or update:

- assigned-person scope,
- candidate strain or mating type names,
- expected cage counts,
- optional strain-master suggestions,
- review items when a distribution row conflicts with existing configured strains or active records.

In the current prototype, the workbook is converted to parsed/intermediate JSON with `scripts/parse_distribution_workbook.py` and then loaded through `Import Distribution JSON`. The converted rows retain workbook filename, sheet name, source row number, and source cell coordinates. The Settings view groups `mating 종류` values into reviewable candidate strain suggestions; these suggestions must not become confirmed strain-master values without explicit review.

The distribution workbook must not silently overwrite photo-backed colony state. It should help the user know what they are responsible for and which strain names should be pre-registered before processing photos.

## 6. Note And Strike-Through Rules

The `Note` section is not plain free text. It is structured evidence and must be parsed line by line.

### 6.1 Separated / Stock Cage Note

For separated or stock cage cards, each note line often represents one mouse.

Example:

| Raw note line | Meaning |
| --- | --- |
| `319 L'` | mouse 319, left ear mark |
| `320 R'L'` | mouse 320, right and left ear marks |
| `318 R'` with one strike-through | mouse 318 moved/separated out |
| mouse line with two strike-throughs | mouse is dead |

Status interpretation:

| Strike status | Interpreted status |
| --- | --- |
| none | active in this cage/card record |
| single | moved/separated out |
| double | dead |
| unclear | needs review |

### 6.2 Mating Cage Note

For mating cage cards, each note line often represents a litter or breeding event.

Example:

| Raw note line | Meaning |
| --- | --- |
| `26.4.13 - 10p` | litter/event on 2026-04-13, 10 pups |
| one strike-through | litter separated |
| two strike-throughs | litter dead/lost |

Status interpretation:

| Strike status | Interpreted event status |
| --- | --- |
| none | open / not yet processed |
| single | separated |
| double | dead |
| unclear | needs review |

### 6.3 Preserve Struck Lines

Struck-through lines must not be deleted. They are historical evidence of completed or dead/missing mice/litters. They should generate or update event records.

## 7. Strain And Genotype Configuration

### 7.1 No Hard-Coding

Strain names, genotype categories, PCR protocols, and management rules must not be hard-coded. The user receives new strain assignment lists over time. These should be registered before use.

### 7.2 Strain Pre-Registration

When the user receives an assigned strain list or distribution workbook, they should import or enter it before processing photos. Distribution rows can suggest new `Strain_Master` entries, but confirmation should remain reviewable.

Benefits:

- reduces strain OCR errors,
- improves fuzzy matching,
- prevents unknown strings from being incorrectly accepted,
- allows export categories to be configured in advance.

If a parsed strain is not in `Strain_Master`, the system should not silently create a final confirmed strain. It should:

1. auto-fill the raw strain text,
2. suggest similar known strains,
3. create a review item if confidence is low or no match exists.

### 7.3 Strain Alias Learning

Different handwritten forms may refer to the same strain.

Examples:

- `ApoM Tg/Tg`,
- `ApoM Tg/tg`,
- `ApoM-tg`,
- `all Tg`,
- `Sgpl1 fl/fl`,
- `SGPL1 fl/fl`.

The system should store:

- raw strain text,
- mapped standard strain,
- confidence,
- confirmed status,
- hit count.

Confirmed aliases should improve future matching.

## 8. Data Model

The following model is a product-level schema. Exact implementation may use a database, local JSON, or workbook tables.

### 8.1 `strain_master`

Purpose: registered strain/cross definitions.

Fields:

- `strain_id`
- `standard_name`
- `display_name`
- `strain_type`
- `target_genotype`
- `active`
- `requires_genotyping`
- `notes`
- `created_at`
- `updated_at`

### 8.2 `strain_alias_master`

Purpose: maps handwritten/raw strain text to registered strains.

Fields:

- `alias_id`
- `raw_text`
- `strain_id`
- `confidence`
- `confirmed`
- `hit_count`
- `created_at`

### 8.3 `genotype_category_master`

Purpose: strain-specific genotype output categories.

Fields:

- `category_id`
- `strain_id`
- `category_name`
- `display_order`
- `is_target`
- `is_unknown_category`
- `active`

Examples:

- `Tg/Tg`, `Tg/+`, `WT`, `result unknown`
- `fl/fl`, `fl/+`, `WT`, `result unknown`
- `Cre; fl/fl`, `WT; fl/fl`, `result unknown`

### 8.4 `management_rule_master`

Purpose: global or strain-specific timing rules.

Fields:

- `rule_id`
- `scope`: global / strain / cage_type
- `strain_id`
- `cage_type`
- `min_age_days`
- `max_age_days`
- `warning_before_days`
- `active`
- `notes`

Default example:

- min age: 30 days,
- max age: 90 days.

### 8.5 `photo_log`

Purpose: stores uploaded photo evidence.

Fields:

- `photo_id`
- `file_path`
- `original_filename`
- `uploaded_at`
- `captured_at`
- `raw_ocr_text`
- `image_quality_status`
- `blur_score`
- `deskew_applied`
- `status`
- `notes`

### 8.6 `parse_result`

Purpose: stores ROI-level extraction results.

Fields:

- `parse_id`
- `photo_id`
- `roi_name`
- `field_name`
- `raw_value`
- `normalized_value`
- `confidence`
- `status`
- `needs_review`
- `created_at`

ROI examples:

- strain area,
- sex area,
- DOB area,
- ID area,
- mating date area,
- note area,
- LMO/O/N area.

### 8.7 `card_snapshot`

Purpose: represents one parsed cage card snapshot. This replaces exposing a user-facing `system_cage_id` or user-managed cage identifier.

Fields:

- `card_snapshot_id` or hidden internal `record_id`
- `latest_photo_id`
- `card_type`: mating / separated / stock / genotyping / unknown
- `card_id_raw`
- `cage_label`: optional value from an Excel row or user-provided label
- `strain_id`
- `raw_strain_text`
- `sex_count_raw`
- `sex`
- `count`
- `dob_raw`
- `dob_start`
- `dob_end`
- `mating_date`
- `lmo_raw`
- `active`
- `status`
- `notes`
- `created_at`
- `updated_at`

Important:

- `card_snapshot_id` is an implementation detail.
- The user should work with photo, strain, DOB, mouse IDs, and Excel row outputs rather than internal IDs.

### 8.8 `mouse_master`

Purpose: individual mouse-level state.

Fields:

- `mouse_id`: internal ID
- `display_id`: handwritten mouse ID, e.g. `318`, `MT318`
- `id_prefix`
- `strain_id`
- `raw_strain_text`
- `sex`
- `genotype`
- `genotype_status`: unknown / pending / confirmed
- `dob_raw`
- `dob_start`
- `dob_end`
- `ear_label_raw`
- `ear_label_normalized`
- `current_card_snapshot_id`
- `status`: active / moved / mating / dead / used / unknown
- `source_photo_id`
- `created_at`
- `updated_at`

### 8.9 `card_note_item_log`

Purpose: stores each note line as structured evidence.

Fields:

- `note_item_id`
- `photo_id`
- `card_snapshot_id`
- `card_type`
- `line_number`
- `raw_line_text`
- `strike_status`: none / single / double / unclear
- `parsed_type`: mouse_item / litter_event / unknown
- `interpreted_status`
- `parsed_mouse_display_id`
- `parsed_ear_label_raw`
- `parsed_ear_label_normalized`
- `parsed_event_date`
- `parsed_count`
- `confidence`
- `needs_review`
- `created_at`

### 8.10 `mating_event_log`

Purpose: mating cage and litter/breeding event history.

Fields:

- `mating_id`
- `card_snapshot_id`
- `strain_id`
- `raw_strain_text`
- `sire_display_id`
- `dam_display_ids`
- `sire_mouse_id`
- `dam_mouse_ids`
- `mating_date`
- `parent_dob_raw`
- `litter_date`
- `pup_count`
- `separated_count`
- `event_status`: open / separated / dead / unknown
- `source_photo_id`
- `notes`
- `created_at`
- `updated_at`

Pedigree note:

- Full `sire_id` / `dam_id` pedigree fields can be added later.
- MVP should capture parent IDs in mating events without requiring complete pedigree resolution.

### 8.11 `genotyping_record`

Purpose: genotype result records linked to mice.

Fields:

- `genotyping_id`
- `date`
- `strain_id`
- `target_name`
- `sample_no`
- `mouse_id`
- `mouse_display_id`
- `band_pattern`
- `wild_band_bp`
- `target_band_bp`
- `result`
- `result_status`
- `source_photo_id`
- `notes`

### 8.12 `action_log`

Purpose: audit trail for all automatic and manual state changes.

Fields:

- `action_id`
- `action_type`: created / moved / separated / dead / born / assigned_to_mating / genotyped / updated / closed
- `target_type`: mouse / card_snapshot / mating / genotype / strain
- `target_id`
- `mouse_id`
- `from_card_snapshot_id`
- `to_card_snapshot_id`
- `source_photo_id`
- `source_note_item_id`
- `previous_value`
- `new_value`
- `confidence`
- `auto_generated`
- `created_by`
- `created_at`
- `description`

All automatic updates must create an `action_log` entry.

### 8.13 `review_queue`

Purpose: queue for uncertain, conflicting, or high-risk items.

Fields:

- `review_id`
- `photo_id`
- `parse_id`
- `note_item_id`
- `issue_type`
- `severity`
- `target_type`
- `target_id`
- `field_name`
- `current_value`
- `suggested_value`
- `message`
- `status`: pending / resolved / ignored
- `resolved_value`
- `resolved_at`
- `created_at`

### 8.14 `export_log`

Purpose: records Excel export history.

Fields:

- `export_id`
- `export_type`: separation_xlsx / animalsheet / dashboard / handoff
- `file_path`
- `exported_at`
- `notes`

### 8.15 `distribution_import`

Purpose: records periodic assignment workbook imports.

Boundary: raw source plus parsed/intermediate rows until reviewed.

Fields:

- `distribution_import_id`
- `source_file_name`
- `source_file_path`
- `received_date`
- `sheet_name`
- `imported_at`
- `status`: imported / parsed / reviewed / superseded
- `notes`

### 8.16 `distribution_assignment_row`

Purpose: row-level assignment extracted from a distribution workbook.

Boundary: parsed/intermediate result unless reviewed into configuration.

Fields:

- `assignment_row_id`
- `distribution_import_id`
- `source_sheet`
- `source_row_number`
- `institution_or_group`
- `responsible_person_raw`
- `mating_type_raw`
- `matched_strain_id`
- `cage_count_raw`
- `mating_cage_count_raw`
- `confidence`
- `review_status`
- `traceability`

## 9. Parsing Pipeline

### 9.1 Upload

The user uploads photos from phone or PC. Direct in-animal-room app use is not required for MVP.

Batch upload should be a first-class path because the user will often upload many cage card/name tag photos at once after animal-room work. Each upload batch should have a `batch_id`, preserve per-photo source evidence, and show per-batch progress across processing, review, accepted, and blocked states. A failed or low-confidence photo in a batch must not prevent the rest of the batch from being stored, parsed, reviewed, or exported when ready.

Distribution workbook upload is a separate raw-source intake path from cage-card photo upload. It updates assignment scope and strain-master suggestions, not current cage/card state.

### 9.2 Image Quality Check

The system should check:

- blur,
- glare,
- cropped card,
- rotated/skewed image,
- missing note area,
- low resolution.

Poor images should still be stored, but low-quality fields should receive lower confidence and may go to review.

### 9.3 ROI-Based Extraction

Because cage cards have a consistent layout, parsing should use regions of interest:

- Strain field,
- Sex field,
- DOB field,
- ID field,
- Mating date field,
- LMO/O/N field,
- Note field.

This should be more accurate than treating the whole card as one OCR block.

### 9.4 LLM-Optional Parse Assist

The core parsing pipeline should not require an LLM. MVP should work with local/manual inputs, OCR or fixture text, configurable masters, deterministic parsing, validation, review, and export previews.

An LLM may be added later as an approval-gated Parse Assist for ambiguous note lines, card-type suggestions, or review explanations. LLM output remains parsed/intermediate data and must not silently create canonical records, new strains, genotype categories, or biological state changes. External LLM use must minimize payloads and avoid sending unnecessary full colony records.

### 9.5 Card Type Classification

The system classifies the card:

- mating,
- separated,
- stock,
- genotyping,
- unknown.

Signals:

- mating date present,
- parent IDs in ID field,
- note lines look like dates/pup counts,
- note lines look like mouse IDs/ear labels.

### 9.6 Note Line Parsing

Each note line should be:

1. extracted,
2. assigned a line number,
3. checked for strike-through count,
4. classified as mouse item / litter event / unknown,
5. normalized,
6. stored with confidence.

### 9.6 Fuzzy Matching

The system should compare parsed values against existing records.

Targets:

- strain names,
- mouse IDs,
- card ID raw values,
- ear labels,
- DOB/date strings.

Examples:

- `MT3I8` may be `MT318`.
- `ApoM Tg/tg` may map to `ApoM Tg/Tg`.
- `25.01.30` may be `26.01.30` if DOB is late 2025 and the card is a mating card.

The system should suggest likely matches rather than silently overwriting when confidence is not high.

## 10. Auto-Fill Policy

The default UX should be:

1. parse photo,
2. auto-fill structured data,
3. run validation checks,
4. flag only uncertain or conflicting items.

The user should not need to approve every normal item.

### 10.1 Auto-Fill States

| State | Meaning |
| --- | --- |
| Auto-filled | parsed and inserted with no major issue |
| Check | inserted, but user should glance later |
| Needs Review | low confidence or conflict; user action needed |
| User Corrected | user edited the auto-filled value |
| Verified | user confirmed |

### 10.2 No Silent Destructive Overwrites

Automatic updates must not silently overwrite high-value existing data.

If updating:

- mouse ID,
- genotype,
- sex,
- DOB,
- death status,
- current active location,

the system must record before/after values in `action_log`. High-risk conflicts should go to `review_queue`.

## 11. Validation Rules

### 11.1 Required Field Checks

Fields that should normally exist:

- strain,
- card type,
- DOB,
- sex/count,
- mouse ID or note items,
- mating date for mating cards,
- source photo.

Missing fields may be allowed but should affect confidence.

### 11.2 Count Consistency

For separated/stock cards:

- parsed sex/count should match the number of active, unstruck mouse note items.

If not, create a warning.

### 11.3 Mouse Active Conflict

If the same mouse appears active in multiple current card records:

- create high-severity review item,
- suggest moved event if previous card line was single-struck,
- require a dedicated movement resolution with evidence before accepting the duplicate-active source,
- preserve the previous active state and reviewed after state in the action log,
- block or flag dead-to-active contradictions.

### 11.4 Date Logic

Examples:

- DOB cannot be in the future unless intentionally entered.
- Separation/movement cannot logically precede DOB.
- Mating date should not precede parent DOB.
- If a date is implausible, suggest likely year correction but do not silently confirm.

### 11.5 Strain Logic

If raw strain is not pre-registered:

- auto-fill raw text,
- suggest closest strain aliases,
- mark as review if not confident.

### 11.6 Genotype Logic

If genotype is not in the strain's configured genotype categories:

- mark as review,
- allow user to add a new genotype category if legitimate.

## 12. Data Stitching Rules

Because there is no QR/barcode, continuity must be inferred.

### 12.1 Mouse Matching

Strongest matching signals:

- mouse display ID,
- ID prefix,
- strain,
- DOB range,
- ear label,
- source/history.

### 12.2 Cage/Card Matching

Do not rely on card `I.D` as cage ID.

Use:

- strain,
- DOB range,
- sex/count,
- active mouse list,
- mating date,
- parent IDs,
- latest photo,
- previous known state.

### 12.3 Movement Inference

If a mouse appears in a new card record and was previously active elsewhere:

- if previous note line was single-struck, infer moved/separated with medium-high confidence,
- if no previous strike evidence, auto-fill current record but flag possible movement,
- if previous status was dead, high-severity review.

### 12.4 Mating Assignment Inference

If a mouse that was previously in a separated cage appears as a parent in a mating card:

- create `assigned_to_mating` action,
- update mouse status to mating,
- link source photo and note item.

## 13. User Workflows

### 13.1 Photo Upload Workflow

1. User writes cage card by hand as usual.
2. User takes photos.
3. User uploads one or many photos later from phone or PC.
4. System stores photo and performs quality checks.
5. System parses ROI fields and note lines.
6. System auto-fills records.
7. System creates warnings/review items only where needed.
8. User reviews exceptions on PC.
9. Export previews and export readiness update after each accepted upload/review action.

The workflow should be upload-driven, not calendar-driven. Any lab handoff should happen from the current accepted state when the user needs it, while the product keeps records continuously current as photos are uploaded.

### 13.2 Separated Cage Workflow

1. Photo is classified as separated/stock cage.
2. System extracts strain, DOB, sex/count, ID field, note lines.
3. System creates/updates card record.
4. New mouse IDs are added to `mouse_master`.
5. Existing mouse IDs are linked or moved.
6. Struck mouse lines generate moved/dead actions.
7. Count mismatch is flagged.
8. Export view updates separated workbook format.

### 13.3 Mating Cage Workflow

1. Photo is classified as mating cage.
2. System extracts parents, parent DOB, mating date, strain/cross.
3. System parses note lines as litter events.
4. Litter lines generate mating event entries.
5. Struck litter lines update event status to separated or dead.
6. Linked separated cage records are associated where possible.
7. Export view updates animalsheet format.

### 13.4 Genotyping Workflow

1. User uploads genotyping sheet/result photo or enters results.
2. System links sample numbers to mouse IDs when possible.
3. Genotype records update `mouse_master`.
4. Genotype count summaries update output sheets.
5. Unmatched sample IDs go to review.

## 14. Dashboard Requirements

Dashboard should show:

- photos uploaded today/recently,
- auto-filled records,
- review queue count,
- high severity conflicts,
- 3-month or configured max-age warnings,
- genotype unknown/pending counts,
- active mice by strain,
- active card snapshots by strain,
- open mating/litter events,
- export status.

## 15. Excel Output Requirements

### 15.1 Existing Format Preservation

The lab's existing formats should be preserved as much as possible:

- `분리.xlsx` style output,
- `animalsheet` style output.

These outputs should be generated from structured records. They should not be the only source of truth.

Current lab examples use `animal sheet.xlsx` for mating cage status and `분리 현황표.xlsx` for separated cage status. Existing lab workbooks can be imported as previous snapshots or template references. They should be reconciled against photo-backed records and must not silently overwrite newer accepted source-photo-derived state.

Before generating a file, the web app should show workbook-like previews for both output types so the user can inspect the current accepted rows, blocked review items, and traceability without opening Excel.

The user may manage multiple assigned strains at the same time. Export previews and downloads should therefore be grouped or filtered by selected strain, and the selected strain must be visible before download because it is part of the required filename.

### 15.1.1 Template Mapping From Current Lab Examples

The current ApoM TgTg examples map to the following output shapes:

| Output | Template columns | Source records |
| --- | --- | --- |
| `animal sheet.xlsx` | `Cage No.`, `Strain`, `Sex`, `I.D`, `genotype`, `DOB`, `Mating date`, `Pubs` plus optional right-side template notes | Accepted mating card snapshots, parent mouse IDs, mating date, and litter note events |
| `분리 현황표.xlsx` | `Strain`, `Genotype`, `total`, `DOB`, `Genotype` split into `WT` / `Tg`, optional blank spacer, `Sampling point` | Accepted separated/stock card snapshots, sex/count, DOB, configured genotype counts, and sampling or age-rule notes |

For `animal sheet.xlsx`, a mating cage should render as a block:

- parent rows for sire/dam IDs;
- litter rows such as `F1`, `F2`, with pup count/status in `I.D` or `genotype` and litter DOB in `DOB`;
- `Pubs` values for open litter notes where applicable.

For `분리 현황표.xlsx`, separated cages should render one summary row per accepted separated/stock card snapshot, with sex/count in `total` and genotype count columns derived from accepted genotype state or left blank/pending when not yet reviewed.

### 15.1.2 Multi-Strain Senior Workbook Findings

The senior-provided examples show that the system must support more than one template layout and more than one strain per operational file:

- `(수의대) animalsheet 김상보 24.10.31.xlsx` has strain-like sheet tabs such as `GFAP Cre; S1PR1 flox`, `GFAP Cre; S1PR1 flox; td tomato`, and `ptgs2 S565A flox`.
- `분리.xlsx` has researcher/person tabs, with multiple strain blocks inside many tabs.
- Header naming varies across sheets (`SEX`, `Sex`, `Total`, `성별 및 총 마리수`, `genotyping 결과`, `비고`, `place`, usage/status columns).
- Some sheets use merged cells to mark strain blocks; others repeat or leave strain blank until the next block.

Implementation consequence: imported Excel rows should be preserved as raw source rows first, then mapped through configurable export templates and strain aliases. The app must not assume one global ApoM-style output, one sheet per workbook, or a single genotype split such as `WT`/`Tg` for every strain.

For MVP exports, it is acceptable to generate one selected-strain workbook at a time using the current selected preview. Later versions may support batch download of one file per strain.

### 15.2 Separation Output

Should summarize by card snapshot:

- cage number/label if available,
- strain,
- genotype,
- sex/count,
- DOB,
- genotype category counts,
- usage/status,
- notes with mouse IDs and ear labels.

### 15.3 Animalsheet Output

Should summarize:

- mating cage/card block,
- parent sex,
- parent IDs,
- parent genotypes,
- parent DOB,
- mating date,
- litter events,
- separated/dead status,
- place if available.

### 15.4 Export Log

Every export should be logged with date, type, and file path.

Exports are generated on demand by the user, not automatically on a monthly schedule. The web app should support direct `.xlsx` downloads for both current workbook previews and show the expected filenames before the user downloads. The expected filename pattern is:

- `{update_date} {strain} animal sheet.xlsx`
- `{update_date} {strain} 분리 현황표.xlsx`

The system may show a manual handoff checklist, but MVP should not automate email sending.

## 16. MVP Scope

### 16.1 MVP 1: Personal Usable System

Must include:

- photo upload,
- photo log,
- auto-filled parse draft with editable fields,
- strain pre-registration,
- strain alias matching,
- mouse master,
- card snapshots,
- note item log,
- action log,
- review queue,
- dashboard,
- separation export,
- animalsheet export.

### 16.2 MVP 1 Parsing Expectations

Parsing can be semi-automated at first:

- local/manual input, fixture text, or OCR suggests parsed fields,
- auto-fill normal values,
- review only uncertain/conflicting cases.

Perfect OCR is not required for MVP, and an LLM is not required for MVP. Source photo and confidence must always be preserved.

### 16.3 Out Of Scope For MVP

Not required initially:

- QR/barcode,
- direct animal-room app workflow,
- full pedigree tree,
- treatment/drug log,
- behavior experiment tracking,
- multi-lab permission system,
- automated email sending,
- native iOS/Android apps.

## 17. Future Extensions

Possible later additions:

- PWA mobile capture interface,
- better image pre-processing,
- model-specific ROI templates,
- gel image parsing,
- treatment/observation log,
- full pedigree tracking,
- reminder notifications,
- Google Sheets or Notion sync,
- multi-user audit permissions.

## 18. Technical Recommendations

### 18.1 App Form

Recommended implementation:

- Web app/PWA,
- mobile-friendly upload flow,
- desktop dashboard for review and export,
- database-backed source of truth,
- Excel import/export support.

### 18.2 Storage

The system must store:

- original photos,
- parsed raw text,
- normalized values,
- confidence,
- validation issues,
- action logs,
- export history.

### 18.3 Safety

Every auto-filled value should be traceable to:

- source photo,
- parse result,
- note line if applicable,
- action log entry.

## 19. Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| handwriting OCR errors | ROI parsing, confidence scores, review queue |
| strain name variations | pre-registration and alias mapping |
| card ID misunderstood as cage ID | separate raw ID from mouse ID and card record |
| count mismatch | active note item count validation |
| mouse appears in two places | high-severity active conflict check |
| dead mouse reappears | high-severity review |
| existing Excel formats change | keep exports configurable and template-based |
| photos are blurry | image quality checks and confidence downgrade |
| over-engineering | keep MVP personal and workflow-driven |

## 20. Success Criteria

The system is successful if:

- the user can upload cage card photos and get useful auto-filled records,
- new mice are added automatically when clear,
- moved/separated/dead events are inferred from note lines and strike-throughs,
- only uncertain or conflicting records require manual review,
- existing lab Excel outputs can be generated,
- the user can see when mating/separation/genotyping actions are due,
- every important record can be traced back to a source photo.

## 21. Final Definition

This product is a personal, photo-grounded mouse colony state tracking system that respects the lab's handwritten workflow and existing Excel formats.

It should not force QR codes, barcode labels, or animal-room app usage.

It should not expose unnecessary internal cage IDs as user-facing workflow.

It should treat cage cards as source evidence, note lines as structured records, mouse IDs as the main continuity anchor, and actions/events as the durable history.
