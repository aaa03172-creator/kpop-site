# Mouse Colony Management System PRD

## Document References

Adopted project documents:

- `AGENTS.md`: project agent guidelines and safety boundaries.
- `design.md`: non-canonical UI and workflow design guidance.
- `mouse_strain_colony_system_design_ko.md`: non-canonical Korean extension design for strain knowledge graph, colony tracking, evidence boundaries, review/correction, and visualization.
- `reference_adoption_notes.md`: non-canonical reference adoption notes for development, design, and external tooling ideas.
- `mouse_open_source_research_adoption_ko.md`: non-canonical adoption note that filters external mouse colony open-source research through the current photo-grounded MVP workflow.
- `open_source_acceleration_candidates_ko.md`: non-canonical technical reference note for open-source libraries that may reduce implementation time or improve local performance.
- `open_source_acceleration_doublecheck_ko.md`: non-canonical double-check note that prioritizes acceleration candidates after license, fit, and MVP-risk review.
- `roi_card_extraction_plan_ko.md`: non-canonical implementation planning note for ROI-based cage-card extraction and reviewable field evidence.
- `wet_lab_operational_review_ko.md`: non-canonical operational review note from a wet-lab workflow perspective.
- `ui_image_usage_improvement_plan_ko.md`: non-canonical UI review note for reducing decorative image noise while preserving evidence-first workflows.
- `review_burden_reduction_plan_ko.md`: non-canonical workflow planning note for separating Focus Review blockers from quick checks and trace-only uncertainty.
- `selective_normalization_controls_plan_ko.md`: non-canonical workflow planning note for keeping raw evidence separate while using bounded selection controls for normalized/reviewed values.
- `mvp_vertical_slice_plan.md`: non-canonical implementation planning note for the first end-to-end workflow.
- `mousedb_cli_first_review_ko.md`: non-canonical review note for a standalone CLI-first MouseDB core that can later be called by PaperPipe, a personal Research Assistant, API, or MCP server.

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
- Prefer bounded selection controls for normalized/reviewed values when the valid range is limited, while keeping the raw OCR/manual value visible and unchanged.
- Ear-label review is a bounded correction flow: reviewers choose a normalized code such as `R_PRIME`, `R_CIRCLE`, `NONE`, or `UNREADABLE`, and the raw note token remains preserved as source evidence.
- If the sex/count evidence indicates both male and female animals in the same cage, the parsed/intermediate card type should default to `Mating`. This is an operational inference for review and export preparation, not permission to overwrite raw sex text or canonical mating records without source-backed review.
- Treat note lines and strike-throughs as structured data.
- Track state changes as events.
- Treat Excel files as outputs/views, not the only source of truth.
- Avoid hard-coded strain, genotype, and protocol logic.

### 3.1 Raw Evidence And Selectable Normalization

When a field has a small or configured set of valid normalized meanings, the UI should let the user select the normalized value instead of typing it repeatedly. This applies especially to card type, sex interpretation, LMO/Y/N style marks, note-line interpretation, genotype status, and assigned strain matching.

Selection controls must not overwrite raw evidence. The system should display and store the original OCR/manual text separately from the selected normalized value or matched candidate. For example, a handwritten sex symbol or unclear OCR text remains `sex_raw`, while the reviewer may select `female`, `male`, `mixed`, `unknown`, or `not_visible` as the normalized interpretation. Assigned strain choices should come from configurable assigned-strain/strain masters, with an explicit unmatched/review path for new or unexpected strains.

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

This workbook is not part of the daily update loop and is not an animal state export. It is an occasional assignment reference that helps the user update their own assigned strain scope.

The normal day-to-day product loop remains:

1. upload cage card photos,
2. OCR/parse and review uncertain fields,
3. update accepted structured records,
4. preview/export `animal sheet` and `분리 현황표` workbooks.

When a new distribution workbook arrives, the user should use it only to update `My Assigned Strains`. The system should then classify uploaded cage cards primarily within that assigned strain scope. If a photo parses to something outside that scope, it should become a review item instead of being silently accepted.

Observed structure from the current example:

- one `Mating` sheet;
- repeated column blocks for institution/group sections such as `수의대` and `의대`;
- each block contains responsible person, `mating 종류`, `Cage 갯수`, and `mating cage 개수`;
- merged person cells indicate that multiple mating types belong to one responsible person or group;
- total or subtotal values may appear in the `mating cage 개수` column.

The system should treat this file as raw source evidence first. Rows from this workbook may suggest updates to:

- `My Assigned Strains`,
- optional raw aliases for those assigned strains,
- expected cage counts,
- review items when the user chooses to import and inspect the workbook.

In the current prototype, the workbook can be converted to parsed/intermediate JSON with `scripts/parse_distribution_workbook.py` and then loaded through `Import Distribution JSON`. This is a helper path, not the primary workflow. The converted rows retain workbook filename, sheet name, source row number, and source cell coordinates. The user should still decide which rows become active assigned strains.

The distribution workbook must not silently overwrite photo-backed colony state, current cage/card state, or confirmed strain master values.

## 6. Note And Strike-Through Rules

The `Note` section is not plain free text. It is structured evidence and must be parsed line by line.

### 6.1 Separated / Stock Cage Note

For separated or stock cage cards, each note line often represents one mouse.

Example:

| Raw note line | Meaning |
| --- | --- |
| `319 L'` | mouse 319, raw ear label `L'`, normalized code `L_PRIME` |
| `320 R'L'` | mouse 320, raw ear label `R'L'`, normalized code `R_PRIME_L_PRIME` |
| `318 R'` with one strike-through | mouse 318 moved/separated out |
| mouse line with two strike-throughs | mouse is dead |

Status interpretation:

| Strike status | Interpreted status |
| --- | --- |
| none | active in this cage/card record |
| single | moved/separated out |
| double | dead |
| unclear | needs review |

### 6.2 Ear Label Notation

Ear labels are structured mouse identity data, not decorative text. The system must preserve both the exact raw notation from the card and a normalized internal code used for matching, validation, and duplicate checks.

Canonical examples:

| Raw card value | Normalized code |
| --- | --- |
| `R'` | `R_PRIME` |
| `L'` | `L_PRIME` |
| `R°` | `R_CIRCLE` |
| `L°` | `L_CIRCLE` |
| `R'L'` | `R_PRIME_L_PRIME` |
| `R°L°` | `R_CIRCLE_L_CIRCLE` |
| `R'L°` | `R_PRIME_L_CIRCLE` |
| `R°L'` | `R_CIRCLE_L_PRIME` |
| `N` | `NONE`, only when the note-line context supports no ear mark |

The lab's intended circle notation is the degree sign form, such as `R°` and `L°`. OCR aliases or accidental input variants such as masculine ordinal `º`, ring-above `˚`, zero, `Ro`, or spaced forms like `R o` should be handled through configurable alias/fuzzy matching, but they are not the preferred canonical raw examples. Unicode prime marks, curly apostrophes, backtick-like marks, and dot suffixes should likewise be handled as aliases for prime candidates when confidence supports it. However, prime and circle are different identity signals. Ambiguity between `R_PRIME` and `R_CIRCLE`, or between `L_PRIME` and `L_CIRCLE`, must not be silently merged. If confidence is not high enough, the parsed value should be marked `check` or routed to the Review Queue according to severity.

### 6.3 Mating Cage Note

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

### 6.4 Preserve Struck Lines

Struck-through lines must not be deleted. They are historical evidence of completed or dead/missing mice/litters. They should generate or update event records.

## 7. Strain And Genotype Configuration

### 7.1 No Hard-Coding

Strain names, genotype categories, PCR protocols, and management rules must not be hard-coded. The user receives new strain assignment lists over time. These should be registered before use.

### 7.2 My Assigned Strains And Pre-Registration

The user should maintain a simple active list called `My Assigned Strains`. This list is the default matching scope for cage card OCR.

In normal use, the user will likely upload photos only for their own assigned strains. Therefore:

- high-confidence OCR matches inside `My Assigned Strains` can be auto-filled according to policy;
- OCR values outside `My Assigned Strains` should go to review;
- the system should suggest close aliases within `My Assigned Strains` before suggesting unrelated global strains;
- adding or removing assigned strains should be deliberate and logged.

When the user receives a new assigned strain list or distribution workbook, they can manually enter/update `My Assigned Strains`, or use the distribution import helper to find candidate entries. Distribution rows can suggest assigned strains or aliases, but confirmation should remain reviewable.

Benefits:

- reduces strain OCR errors,
- improves fuzzy matching,
- prevents unknown strings from being incorrectly accepted,
- allows export categories to be configured in advance.

If a parsed strain is not in `My Assigned Strains` or `Strain_Master`, the system should not silently create a final confirmed strain. It should:

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

### 8.3 `my_assigned_strain`

Purpose: active user scope for OCR matching, review routing, and export grouping.

Fields:

- `assigned_strain_id`
- `strain_id`
- `display_name`
- `active`
- `source_type`: manual / distribution_workbook / imported_list
- `source_reference`
- `assigned_at`
- `removed_at`
- `notes`

Rows in this table should be explicit user scope, not inferred current cage/card state.

### 8.4 `ear_label_master`

Purpose: allowed normalized ear label codes and lab-friendly display text.

Boundary: canonical configuration.

Fields:

- `ear_label_code`: primary key, e.g. `R_PRIME`, `R_CIRCLE`, `NONE`
- `display_text`: lab-facing notation, e.g. `R'`, `R°`, `R'L°`
- `meaning`
- `active`
- `created_at`

Seed examples:

| `ear_label_code` | `display_text` | Meaning |
| --- | --- | --- |
| `R_PRIME` | `R'` | right ear prime mark |
| `L_PRIME` | `L'` | left ear prime mark |
| `R_CIRCLE` | `R°` | right ear circle mark |
| `L_CIRCLE` | `L°` | left ear circle mark |
| `R_PRIME_L_PRIME` | `R'L'` | right prime + left prime |
| `R_CIRCLE_L_CIRCLE` | `R°L°` | right circle + left circle |
| `R_PRIME_L_CIRCLE` | `R'L°` | right prime + left circle |
| `R_CIRCLE_L_PRIME` | `R°L'` | right circle + left prime |
| `NONE` | `N` | no ear label / no mark |

The degree sign form, such as `R°` and `L°`, is the lab's intended circle notation. Similar glyphs such as `º` and `˚` may appear as OCR/input aliases but should not be the preferred display text.

### 8.5 `ear_label_alias`

Purpose: maps OCR/raw ear label variants to allowed ear label codes.

Boundary: parsed/intermediate configuration until confirmed; confirmed aliases become configuration.

Fields:

- `alias_id`
- `raw_text`
- `ear_label_code`
- `confidence`
- `confirmed`
- `hit_count`
- `created_at`

Seed examples:

| `raw_text` | `ear_label_code` | Confirmed |
| --- | --- | --- |
| `R'`, `R′`, `R’` | `R_PRIME` | yes |
| `L'`, `L′`, `L’` | `L_PRIME` | yes |
| `R°`, `Rº`, `R˚` | `R_CIRCLE` | yes |
| `L°`, `Lº`, `L˚` | `L_CIRCLE` | yes |
| `N` | `NONE` | yes |
| `R0`, `Ro`, `L0`, `Lo` | circle candidates | no, review/check unless visual confidence is high |

Ambiguous aliases must not silently become confirmed just because they occur often. Confirmation should preserve the raw alias, normalized code, confidence, and source evidence for the decision.

### 8.6 `genotype_category_master`

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

### 8.6.1 `strain_target_genotype`

Purpose: strain-level target genotype settings used to suggest maintenance, mating, experimental, backup, or cleanup decisions after genotyping.

Boundary: canonical configuration.

Fields:

- `target_id`
- `strain_id`
- `target_genotype`
- `purpose`: strain_maintenance / mating_candidate / experimental_cross / backup / unknown
- `active`
- `created_at`

Examples are configuration examples only and must not be hard-coded. The same normalized genotype result may imply a different next action depending on strain, target purpose, colony plan, and user review.

### 8.7 `management_rule_master`

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

### 8.8 `photo_log`

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

### 8.9 `parse_result`

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

### 8.10 `card_snapshot`

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

### 8.11 `mouse_master`

Purpose: individual mouse-level state.

Rationale: `mouse_master` is required because colony continuity is mouse-centered, not cage-centered. Cage cards may not have a stable cage ID, and the same mouse can appear in separated, moved, mating, genotyping, or historical note contexts over time. Ear label, tail sample ID, genotype result, target genotype match, and current status must remain connected to the same individual mouse without ambiguity.

Boundary: canonical structured state. It stores the latest accepted state for fast lookup. Historical changes should be represented as events in `action_log`, source note rows, genotyping records, or other event tables rather than accumulating all history directly in `mouse_master`.

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
- `ear_label_code`: normalized internal code; replaces the older planning name `ear_label_normalized`
- `ear_label_confidence`
- `ear_label_review_status`: auto_filled / check / needs_review / verified / user_corrected
- `sample_id`
- `sample_date`
- `genotyping_status`: not_sampled / sampled / submitted / pending / resulted / failed / not_required / unknown
- `genotype_result`
- `genotype_result_date`
- `target_match_status`: matches_target / does_not_match_target / partially_matches / unknown / not_applicable
- `use_category`: maintenance_candidate / mating_candidate / experimental_candidate / cleanup_candidate / backup / unknown
- `next_action`: sample_needed / awaiting_result / review_result / keep_for_maintenance / consider_for_mating / available_for_experiment / cleanup_or_confirm / review_needed
- `source_note_item_id`
- `current_card_snapshot_id`
- `status`: active / moved / mating / dead / used / unknown
- `source_photo_id`
- `created_at`
- `updated_at`

Implementation notes:

- `display_id` must not be globally unique by itself. Matching should use candidates such as display ID, strain or raw strain, DOB range, ear label, source history, and review status.
- `raw_strain_text` must remain available because a strain may not be matched when the mouse candidate is first created.
- In the current local SQLite implementation, unresolved future references such as `strain_id` and `current_card_snapshot_id` may be stored as nullable text values until those tables are implemented. Safe existing references such as `source_photo_id` and `ear_label_code` can use foreign keys.

### 8.12 `card_note_item_log`

Purpose: stores each note line as structured evidence.

Rationale: the cage card `Note` area is not plain free text. In separated/stock cards, note lines often represent individual mice with mouse IDs, ear labels, and strike-through status. In mating cards, note lines often represent litter events. Storing the note area only as a blob would lose line number, strike status, parsed mouse/litter meaning, confidence, and reviewability.

Boundary: parsed/intermediate evidence. Rows should preserve what was read from the photo and how it was interpreted at parse time. They should not be silently overwritten when OCR or parsing is corrected; use review/action history or a later parse version to preserve traceability.

Fields:

- `note_item_id`
- `photo_id`
- `parse_id`
- `card_snapshot_id`
- `card_type`
- `line_number`
- `raw_line_text`
- `strike_status`: none / single / double / unclear
- `parsed_type`: mouse_item / litter_event / unknown
- `interpreted_status`
- `parsed_mouse_display_id`
- `parsed_ear_label_raw`
- `parsed_ear_label_code`: normalized internal code; replaces the older planning name `parsed_ear_label_normalized`
- `parsed_ear_label_confidence`
- `parsed_ear_label_review_status`: auto_filled / check / needs_review / verified / user_corrected
- `parsed_event_date`
- `parsed_count`
- `confidence`
- `needs_review`
- `created_at`

Implementation notes:

- `raw_line_text` must preserve the original parsed line.
- `strike_status` and `interpreted_status` are separate because a single strike can mean moved/separated for mouse lines and separated for litter lines.
- `parsed_ear_label_raw` and `parsed_ear_label_code` must stay separate.
- `parse_id` should be kept when available so repeated parsing of the same photo can be audited.
- In the current local SQLite implementation, `photo_id`, `parse_id`, and `parsed_ear_label_code` can use existing foreign keys; `card_snapshot_id` can remain nullable text until the card snapshot table exists.

### 8.13 `mating_event_log`

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

### 8.14 `genotyping_record`

Purpose: sample collection, submission, and genotype result records linked to mice.

Boundary: event/history record. The latest accepted genotype state may be summarized in `mouse_master`, but source result history belongs here.

Fields:

- `genotyping_id`
- `mouse_id`
- `sample_id`
- `sample_date`
- `submitted_date`
- `result_date`
- `strain_id`
- `target_name`
- `mouse_display_id`
- `raw_result`
- `normalized_result`
- `result_status`: pending / resulted / failed / ambiguous / needs_review
- `source_photo_id`
- `confidence`
- `notes`
- `created_at`
- `updated_at`

### 8.15 `action_log`

Purpose: audit trail for all automatic and manual state changes.

Fields:

- `action_id`
- `action_type`: created / moved / separated / dead / born / assigned_to_mating / genotyped / sample_collected / genotyping_submitted / genotyping_resulted / genotyping_failed / genotype_updated / use_category_suggested / updated / closed
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

### 8.16 `review_queue`

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

### 8.17 `export_log`

Purpose: records Excel export history.

Fields:

- `export_id`
- `export_type`: separation_xlsx / animalsheet / dashboard / handoff
- `file_path`
- `exported_at`
- `notes`

### 8.18 `distribution_import`

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

### 8.19 `distribution_assignment_row`

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

Distribution workbook upload is a separate, occasional raw-source intake path from cage-card photo upload. It can help update `My Assigned Strains`, but it does not update current cage/card state.

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
5. parsed into raw mouse ID and raw ear label candidates when present,
6. normalized into mouse ID and ear label codes with confidence,
7. stored with confidence.

For ear labels, raw text and normalized code must stay separate. A clear `R'` can normalize to `R_PRIME`, while uncertain variants such as `R`, `R.`, `Ro`, or `R0` should remain reviewable unless the alias match and visual context are strong enough.

Example separated/stock note parsing:

| Raw note line | Mouse display ID | Ear label raw | Ear label code |
| --- | --- | --- | --- |
| `319 L'` | `319` | `L'` | `L_PRIME` |
| `320 R'L'` | `320` | `R'L'` | `R_PRIME_L_PRIME` |
| `321 R°` | `321` | `R°` | `R_CIRCLE` |
| `322 R°L'` | `322` | `R°L'` | `R_CIRCLE_L_PRIME` |
| `323 N` | `323` | `N` | `NONE` |

The original line must still be preserved in `card_note_item_log.raw_line_text`, even when the parsed mouse ID and ear label are clear.

### 9.7 Ear Label Normalization Logic

The parser should expose ear label normalization as a deterministic function backed by `ear_label_master` and `ear_label_alias`.

Conceptual return shape:

```ts
normalizeEarLabel(raw: string): {
  code: string | null;
  confidence: number;
  status: "auto_filled" | "check" | "needs_review";
  candidates?: Array<{ code: string; confidence: number }>;
}
```

Expected behavior:

| Raw value | Result |
| --- | --- |
| `R'`, `R′`, `R’` | `R_PRIME`, high confidence |
| `L'`, `L′`, `L’` | `L_PRIME`, high confidence |
| `R°` | `R_CIRCLE`, high confidence |
| `L°` | `L_CIRCLE`, high confidence |
| `Rº`, `R˚` | `R_CIRCLE`, alias match |
| `Lº`, `L˚` | `L_CIRCLE`, alias match |
| `N` | `NONE`, when note-line context supports no ear mark |
| `R0`, `Ro`, `L0`, `Lo` | circle candidate with `check` unless visual confidence is very high |
| `R`, `L` | ambiguous, `needs_review` |

Combination parsing must support multiple marks in one label, including `R'L'`, `R°L°`, `R'L°`, and `R°L'`. If one component is uncertain, such as `R0L'`, the parser may suggest `R_CIRCLE_L_PRIME` with `check`. If both components are uncertain, such as `RoLo`, it should produce candidates and choose `check` or `needs_review` based on confidence.

### 9.8 Fuzzy Matching

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
- Unicode prime or curly apostrophe variants may map to `R_PRIME`.
- The intended lab notation `R°` maps to `R_CIRCLE`; visually similar OCR/input variants may be suggested as aliases only when confidence supports it.

The system should suggest likely matches rather than silently overwriting when confidence is not high. Ear label prime/circle ambiguity is identity-critical and should be sent to `check` or review instead of being collapsed into one code.

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

If raw strain is not in `My Assigned Strains`:

- auto-fill raw text,
- suggest closest aliases inside the assigned scope first,
- mark as review if not confident.

If the raw strain appears to be a real strain but outside the assigned scope, the system should ask the user to confirm whether it belongs to them before accepting it.

### 11.6 Genotype Logic

If genotype is not in the strain's configured genotype categories:

- mark as review,
- allow user to add a new genotype category if legitimate.

If a genotype result can be parsed but does not match any configured `genotype_category_master` row for the strain, do not silently create a new category. Keep the raw result, suggest the closest configured category when possible, and send the item to review.

### 11.7 Ear Label Logic

Ear labels must participate in validation because they are part of mouse identity.

Duplicate label warning:

- If two active mice in the same cage/card snapshot have the same `ear_label_code`, same strain, and same compatible DOB group, create a Review Queue item.
- This should be a warning/review item, not an automatic overwrite, because same-label collisions may represent OCR error, a missing label, or a real cage-card issue.

Mouse identity matching:

- If the same mouse display ID appears again and strain, DOB, and ear label are compatible, treat it as the same mouse candidate.
- If display ID matches but ear label differs, create a Review Queue item.
- Do not silently overwrite the previous ear label. Store the new raw value, normalized candidate, source photo, and note line.

Strike-through handling:

- If a struck-through note line contains an ear label, still parse and store the ear label.
- The strike-through affects interpreted status or event creation; it does not erase identity evidence.
- For example, `318 R'` with a single strike should preserve `R_PRIME`, interpret the line as moved/separated, and create an action log event when accepted.

Review Queue items should be created when:

- an ear label cannot be parsed;
- prime/circle distinction is ambiguous;
- the same active cage has duplicate ear label codes for otherwise similar mice;
- an existing mouse ID has a conflicting ear label;
- OCR output is likely ambiguous, such as `R0`, `Ro`, `L0`, `Lo`, `R`, or `L`;
- a combination label is partially ambiguous.

Ear label review items should include the original photo, cropped ROI when available, raw note line, parsed mouse ID, suggested candidates, confidence score, and any existing matched mouse record.

### 11.8 Genotyping Workflow Logic

After pups are separated and individual mouse records are created, the system should treat genotyping as a structured workflow:

`Separated cage created -> Mouse IDs created -> Ear labels assigned -> Tail sample collected -> Genotyping submitted or pending -> Genotype result entered -> Target genotype matched -> Next action suggested`

Newly separated mice should default to:

- `genotyping_status`: not_sampled
- `genotype_result`: unknown
- `target_match_status`: unknown
- `use_category`: unknown
- `next_action`: sample_needed

When a tail sample is collected from a sample sheet, cage card note, or manual entry:

- update `sample_id`;
- update `sample_date`;
- set `genotyping_status` to sampled;
- set `next_action` to awaiting_result;
- create a `sample_collected` action log entry.

If sample ID equals mouse display ID by lab convention, the system may suggest an automatic mapping, but ambiguous matches still go to review.

When genotyping is submitted or pending:

- set `genotyping_status` to submitted or pending;
- set `next_action` to awaiting_result;
- create a `genotyping_submitted` action log entry when the state change is accepted.

When a result is uploaded or manually entered:

- create a `genotyping_record`;
- update the latest genotype fields in `mouse_master`;
- compare the normalized result with active `strain_target_genotype` settings;
- suggest `target_match_status`, `use_category`, and `next_action`;
- create `genotyping_resulted`, `genotype_updated`, and when applicable `use_category_suggested` action log entries.

The system should suggest, not force, final use category. A non-target result may still be useful for a control, experiment, backup, or colony decision.

### 11.9 Sample ID Matching Logic

Sample ID matching priority:

1. exact mouse display ID match;
2. mouse ID without prefix match;
3. same strain, compatible DOB group, and same ear label;
4. fuzzy match candidate;
5. Review Queue.

If one sample ID maps to multiple possible mice, or if no mouse can be matched, create a Review Queue item. The review item should show sample ID, raw result, candidate mice, strain, DOB, ear label, source photo or sheet, and confidence.

### 11.10 Genotyping Validation Rules

Create warnings or Review Queue items when:

- genotype result exists but the mouse was never marked sampled;
- sample ID cannot be matched to any mouse;
- one sample ID matches multiple mice;
- result conflicts with an existing genotype;
- genotype does not match any configured category for that strain;
- result contradicts an active target genotype setting;
- mouse is marked dead before sample or result date;
- mouse is already used or moved but a new result is uploaded;
- sample date is before DOB;
- result date is before sample date.

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
5. Ear labels are parsed and linked as identity evidence.
6. New separated mice default to `genotyping_status = not_sampled` and `next_action = sample_needed` unless the strain does not require genotyping.
7. Existing mouse IDs are linked or moved.
8. Struck mouse lines generate moved/dead actions.
9. Count mismatch is flagged.
10. Export view updates separated workbook format.

### 13.3 Mating Cage Workflow

1. Photo is classified as mating cage.
2. System extracts parents, parent DOB, mating date, strain/cross.
3. System parses note lines as litter events.
4. Litter lines generate mating event entries.
5. Struck litter lines update event status to separated or dead.
6. Linked separated cage records are associated where possible.
7. Export view updates animalsheet format.

### 13.4 Genotyping Workflow

1. Newly separated mice appear in the genotyping worklist as not sampled.
2. User uploads a sample sheet/photo, enters tail sample collection manually, or records sample IDs from cage card notes.
3. System links sample IDs to mouse IDs when possible.
4. Sampled mice move to awaiting result.
5. User uploads a genotyping result photo/sheet or enters results manually.
6. System creates `genotyping_record` rows and updates latest genotype state in `mouse_master`.
7. System compares results with configured genotype categories and active strain target genotypes.
8. System suggests target match status, use category, and next action.
9. Genotype count summaries update output sheets.
10. Unmatched, conflicting, or ambiguous sample/result rows go to review.

For MVP, manual or semi-structured result entry is sufficient before real OCR. Supported input shapes may include sample/result rows such as `Sample 319: Tg/Tg`, `Sample MT320: Cre+`, or `Sample 21: fl/fl`.

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

Genotyping dashboard cards should include:

| Card | Meaning |
| --- | --- |
| Not sampled | separated mice that still need tail sampling |
| Awaiting result | sampled/submitted mice without an accepted result |
| Failed or ambiguous | failed, ambiguous, or review-needed results |
| Target genotype confirmed | mice whose result matches an active target genotype setting |
| Non-target genotype | mice needing cleanup, experiment, backup, or review decision |
| Review needed | sample/result matching conflicts or invalid genotype states |

The dashboard should help the user know what to do next without remembering which mice need sampling, which samples are awaiting results, or which mice are possible maintenance/mating/experiment candidates.

### 14.1 Ear Label Review UI

For ear label review, the UI should show:

- original photo;
- highlighted note line;
- cropped ear label ROI when available;
- AI/OCR raw reading;
- suggested normalized code;
- candidate options from `ear_label_master`, including combinations and `NONE`;
- manual correction input;
- confidence and review status.

Example review message:

`Ear label uncertain: raw value "R0" may indicate "R°" (R_CIRCLE). Please confirm.`

### 14.2 Mouse Detail Ear Label Display

Mouse detail should show both lab notation and internal code:

- Ear label: `R'`
- Internal code: `R_PRIME`
- Source: source photo and note line
- Status: `auto_filled`, `check`, `needs_review`, `verified`, or `user_corrected`

Do not show only the normalized code to the user. The lab is accustomed to raw notation, so raw/display notation should be prominent and the internal code should remain secondary.

### 14.3 Mouse Detail Genotyping Display

Mouse detail should show:

- Mouse ID;
- strain;
- sex;
- DOB;
- ear label;
- current cage/card snapshot;
- genotyping status;
- sample ID;
- sample date;
- genotype result;
- target match status;
- suggested use category;
- next action;
- source photos or result sheets;
- action timeline.

### 14.4 Genotyping Worklist And Result Entry UI

The Genotyping screen should include a worklist with:

| Mouse ID | Ear label | Strain | DOB | Sample status | Result | Next action |
| --- | --- | --- | --- | --- | --- | --- |

Filters should include:

- not sampled;
- awaiting result;
- failed;
- target genotype confirmed;
- non-target genotype;
- needs review.

Result entry should support:

- upload result sheet photo;
- upload Excel/CSV later if needed;
- manual entry table for MVP.

Manual entry columns:

- Sample ID;
- Result;
- Target;
- Notes.

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

Ear labels in exports should use lab-friendly display notation from `ear_label_master.display_text`, not internal codes. For example, export `R'`, `L'`, `R°`, `L°`, and `R'L°` rather than `R_PRIME` or `R_PRIME_L_CIRCLE`.

If an ear label is uncertain, the export preview should mark it clearly without disrupting the familiar workbook shape. Acceptable representations include:

- inline marker: `320 R°?`
- compact status marker: `320 R° (check)`
- separate notes/status column when the template allows it

The app should propose the least disruptive representation for the selected export template and block final export only when unresolved review items make the row unsafe.

Where appropriate, separated-cage exports should include or support mouse ID, ear label, sample ID, genotyping status, genotype result, and use category/notes. If the existing lab workbook format does not have a safe place for these values, keep the original format unchanged and add a separate export sheet such as `Genotyping_Worklist` or `Mouse_Master`.

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

- CLI-first MouseDB core with a thin web app/PWA layer when needed,
- mobile-friendly upload flow,
- desktop dashboard for review and export,
- database-backed source of truth,
- Excel import/export support.

MouseDB should remain an independent tool, not a PaperPipe submodule. PaperPipe should manage papers, literature, and methods. MouseDB should manage strain, colony, mouse, cage, mating, litter, genotype, and event records. A future personal Research Assistant may call both tools as a control layer.

The first durable implementation should keep business logic in services that can be called by CLI, web UI, API, or MCP wrappers:

```text
CLI or UI -> schemas/input validation -> services -> repositories -> models/db
```

The CLI is a public integration surface. Major commands should support stable `--json` output so later automation can call MouseDB without scraping human-readable tables.

### 18.2 Storage

The system must store:

- original photos,
- parsed raw text,
- normalized values,
- confidence,
- validation issues,
- action logs,
- export history.

For CLI-first MouseDB tables and commands, source/evidence traceability should be included from the beginning where feasible. Important canonical records and events should be able to reference a source photo, note item, imported Excel row, manual entry, or CLI action.

Minimum traceability fields to consider on imported, parsed, canonical, or event records:

- `source_type`,
- `source_id`,
- `confidence`,
- `reviewed_status`,
- `raw_value` where applicable,
- `normalized_value` where applicable.

### 18.3 Safety

Every auto-filled value should be traceable to:

- source photo,
- parse result,
- note line if applicable,
- action log entry.

State-changing operations that update current structured state and create history must be transactional. For example, cage movement should update the mouse's current cage and create a movement event in the same transaction. Genotype recording should create the genotype result and the related mouse event together. Partial writes are not acceptable for mouse-relevant state changes.

MouseEvent or action log entries should be append-only by default. Corrections and inferred state changes should preserve previous and new values instead of silently rewriting history.

`Mouse.current_genotype_summary` should be treated as a display/cache field. Authoritative genotype calls should live in structured `GenotypeResult` records.

Controlled vocabularies such as status values, genotype categories, protocol names, date rules, and event types should be centralized and replaceable. They may start as seed/config values in MVP, but they should not be scattered as hard-coded domain logic.

### 18.4 Labeling Session Rules

Labeling session rule sets are configurable parsed/intermediate workflow policy, not canonical mouse state. A rule set may describe the session date, compatible strain text, mouse numbering order, ear-label sequence, crossed-out note handling, sample-to-mouse mapping, and default genotyping target.

Rule application must preserve raw note text, raw ear-label tokens, raw sample IDs, and source photo links. Expected ear-label codes, inferred dead candidates, and genotyping target defaults should remain traceable processing assumptions until existing review/canonical writer paths accept them with before/after evidence.

## 19. Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| handwriting OCR errors | ROI parsing, confidence scores, review queue |
| strain name variations | pre-registration and alias mapping |
| ear label prime/circle ambiguity | preserve raw notation, normalize to explicit codes, route low-confidence identity marks to check/review |
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
