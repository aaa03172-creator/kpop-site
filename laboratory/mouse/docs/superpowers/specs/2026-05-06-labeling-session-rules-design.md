# Labeling Session Rules Design

Layer classification: parsed or intermediate result / workflow policy design.

Canonical status: non-canonical design spec. Canonical product behavior remains governed by `final_mouse_colony_prd.md`, `AGENTS.md`, and adopted project documents.

## Goal

Use day-specific lab labeling rules to improve note-line parsing, mouse identity continuity, death handling, and genotyping sample matching without replacing handwritten cage cards or treating OCR as clean canonical data.

## Context

The lab writes mouse IDs and ear labels by hand on cage cards, note paper, and genotyping sheets. For the 2026-05-06 ApoM Tg/Tg workflow, the user described these operational rules:

- Mouse numbering starts with males.
- Mouse numbers continue within the same ID lineage even when cages change.
- Ear-label sequence starts from the first label again whenever the cage changes.
- Crossed-out mistake lines are treated as dead mice.
- Genotyping sample numbers correspond to mouse numbers.
- Genotyping target is ApoM-tg for the current workflow.

These rules should be configurable session rules, not strain-specific hard-coded logic.

## Data Boundaries

| Artifact | Boundary | Notes |
| --- | --- | --- |
| Cage card photo | raw source | Preserve even when image quality is poor. |
| Handwritten note sheet photo | raw source | Preserve line evidence and strike-through marks. |
| Genotyping sheet photo | raw source | Preserve sample/result source evidence. |
| OCR or manual transcription text | parsed or intermediate result | Never overwrite raw source text. |
| Labeling session rule set | parsed/intermediate workflow policy | Guides parsing and validation for a batch/session. |
| Parsed note item | parsed or intermediate result | Stores raw line, mouse candidate, ear-label candidate, confidence, strike status. |
| Dead status inferred from crossed-out line | canonical event candidate | Can become canonical only through policy-approved write with evidence. |
| Genotyping sample record | parsed/intermediate until result accepted | Links sample ID to mouse candidate with evidence. |
| Confirmed genotype result | canonical structured state plus event | Requires accepted or policy-approved result. |
| Excel export/genotyping result form | export or view | Generated from structured records and review state. |

## Rule Set Model

A labeling rule set describes how to interpret one labeling session or batch.

Recommended fields:

- `rule_set_id`
- `display_name`
- `applies_to_strain_text`
- `session_date`
- `numbering_order`: for this workflow, `male_first`
- `mouse_number_scope`: for this workflow, `continues_across_cages_within_same_id`
- `ear_sequence_scope`: for this workflow, `resets_per_cage`
- `crossed_out_handling`: for this workflow, `dead`
- `sample_mapping`: for this workflow, `sample_id_equals_mouse_display_id`
- `genotyping_target`: for this workflow, `ApoM-tg`
- `active`
- `created_at`
- `updated_at`

This table is a workflow policy/config layer. It should not by itself create canonical mice, deaths, or genotype results.

## Ear Label Sequence

Ear labels should remain normalized codes with display text separate from raw OCR/manual tokens.

Recommended sequence for this workflow:

| Sequence | Code | Display |
| ---: | --- | --- |
| 1 | `R_PRIME` | `R'` |
| 2 | `L_PRIME` | `L'` |
| 3 | `R_PRIME_L_PRIME` | `R'L'` |
| 4 | `R_CIRCLE` | right circle/punch |
| 5 | `L_CIRCLE` | left circle/punch |
| 6 | `R_CIRCLE_L_CIRCLE` | right circle + left circle |
| 7 | `R_PRIME_L_CIRCLE` | `R'` + left circle |
| 8 | `R_CIRCLE_L_PRIME` | right circle + `L'` |
| 9 | `R_DOUBLE_CIRCLE` | right double circle |
| 10 | `L_DOUBLE_CIRCLE` | left double circle |
| 11 | `R_DOUBLE_CIRCLE_L_DOUBLE_CIRCLE` | right double circle + left double circle |
| 12 | `R_PRIME_L_DOUBLE_CIRCLE` | `R'` + left double circle |
| 13 | `R_DOUBLE_CIRCLE_L_PRIME` | right double circle + `L'` |

The user's spoken placeholder "ppong" is only a conversational shorthand for the circle/punch mark. The app should store stable codes and show either a symbol, image, or clear label.

## Processing Flow

1. Store photos and note sheets as raw source records.
2. Parse visible note lines into `card_note_item_log` with raw text, line number, strike status, mouse candidate, ear-label raw token, normalized ear-label candidate, confidence, and review status.
3. Select or infer a labeling rule set for the batch.
4. Group note items by card snapshot or cage/card observation.
5. Apply the ear-label sequence from the start of each cage group.
6. Validate mouse number continuity across cage groups within the same ID lineage.
7. Treat crossed-out mouse lines as dead candidates when the rule set says `crossed_out_handling = dead`.
8. Create review items only for conflicts that the rules cannot resolve safely.
9. Create or update canonical mouse state only through the existing canonical writer path with source evidence and action/event logging.
10. Create genotyping records by matching sample IDs to mouse display IDs under the rule set.

## Validation Behavior

Auto-fill or policy-approved:

- Ear-label token matches expected sequence for the current cage group.
- Missing label can be inferred from an otherwise consistent sequence, while raw value remains blank or unreadable.
- Crossed-out mouse line becomes a dead candidate with source note evidence.
- Genotyping sample ID exactly matches mouse display ID.

Review required:

- Same active mouse number appears in two incompatible cage groups.
- Parsed ear-label token conflicts with the expected sequence.
- Mouse number jumps without a crossed-out or dead line explaining the gap.
- Sample ID has no matching mouse candidate.
- One sample ID matches multiple mice.
- Genotype result conflicts with an existing confirmed genotype result.
- Genotype result is outside configured result categories.

## UI Behavior

The user should be able to choose a labeling rule set for a photo batch or genotyping batch. The UI should default to the most recent compatible rule set but keep it visible as a reviewable processing assumption.

For each parsed note line, the UI should show:

- raw note text,
- parsed mouse number,
- raw ear-label token,
- normalized ear-label code/display,
- expected label from the selected sequence,
- strike/dead interpretation,
- source photo link.

For genotyping, the UI should show:

- sample number,
- matched mouse number,
- ear label,
- cage/card source,
- target,
- raw result,
- normalized result,
- result status.

## Testing Strategy

Tests should cover the workflow using small fixtures rather than the full photo set:

- Ear-label sequence resets per cage.
- Mouse numbers continue across cages.
- Crossed-out note lines become dead candidates.
- Unexpected ear-label tokens remain reviewable.
- Sample IDs match mouse display IDs.
- Unmatched or duplicate sample IDs produce review items.
- Genotype result acceptance records both structured result and event/action trace.

## Out Of Scope

- Replacing handwritten cage cards.
- Inferring strain-specific biological rules from ApoM Tg/Tg.
- Automatically interpreting every possible ear-marking system.
- Sending full records to external OCR/LLM services.
- Creating a final Excel export redesign.
