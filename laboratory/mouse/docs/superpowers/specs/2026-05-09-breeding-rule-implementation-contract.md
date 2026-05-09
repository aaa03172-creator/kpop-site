# Breeding Rule Implementation Contract

Layer classification: parsed/intermediate result and review item implementation contract.

Canonical status: non-canonical. This document defines the next implementation surface for parsing, rule application, and review item generation. Accepted state still lives in source-backed canonical tables such as `mating_registry`, `mating_mouse`, `litter_registry`, `mouse_master`, and event/action logs.

## Goal

Convert breeding operation rules into data shapes that code can apply without hard-coding ApoM-specific assumptions, genotype categories, dates, or irreversible colony operations.

The first implementation should generate:

1. configurable rule definitions,
2. parsed breeding evidence,
3. cage/mating/litter/maintenance candidates,
4. review items with conflict metadata,
5. export/readiness suggestions only after the assumptions are visible.

It must not automatically sacrifice, replace, close, delete, or overwrite canonical records.

## Rule Config Shape

A breeding rule set is workflow policy. It can be stored in SQLite later, but the initial fixture/config shape should use the same fields so it can migrate cleanly.

```json
{
  "rule_set_id": "breeding_rule_default_20260509",
  "display_name": "Default breeding operation review rules",
  "policy_scope": {
    "scope_type": "project",
    "strain_text": "",
    "facility": "",
    "effective_from": "2026-05-09",
    "effective_to": ""
  },
  "active": true,
  "signals": [
    {
      "signal_key": "mixed_sex_plus_mating_date",
      "rule_strength": "evidence_candidate",
      "target_candidate_type": "mating_cage",
      "confidence_delta": 25,
      "requires_any": ["mating_date", "parent_style_rows", "active_litter_evidence"],
      "conflict_review_keys": ["possible_holding_cage", "stale_card_text"]
    }
  ],
  "thresholds": {
    "no_birth_review_after_days": 60,
    "parent_replacement_review_after_days": 365,
    "litter_separation_due_after_days": 30,
    "litter_separation_overdue_after_days": 45,
    "litter_separation_high_overdue_after_days": 60,
    "separation_batch_max_dob_span_days": 14
  },
  "strain_specific_assumptions": [
    {
      "assumption_key": "default_genotype_for_pups",
      "strain_text": "ApoM Tg/Tg",
      "value": "Tg",
      "rule_strength": "adopted_policy",
      "review_required_before_global_use": true
    }
  ]
}
```

Required rule strength values:

| Value | Meaning |
| --- | --- |
| `source_structure` | Layout or row pattern used for extraction only. |
| `evidence_candidate` | Suggests a normalized interpretation with confidence. |
| `review_trigger` | Creates or updates a review item. |
| `adopted_policy` | User-approved rule scoped to project, strain, facility, or session. |
| `prohibited_automation` | Must never execute automatically. |

## Parsed Evidence Shape

All parsed breeding facts should be intermediate evidence rows or payloads. They should reference the raw source row/photo and preserve raw values.

```json
{
  "evidence_id": "breed_ev_001",
  "source_kind": "legacy_workbook_row",
  "source_ref": {
    "source_record_id": "src_workbook_001",
    "legacy_import_id": "legacy_import_001",
    "legacy_row_id": "legacy_row_042",
    "sheet_name": "animal sheet",
    "row_number": 42,
    "photo_id": "",
    "note_item_id": ""
  },
  "source_recency": {
    "observed_date": "2026-05-04",
    "imported_at": "2026-05-09T10:00:00Z"
  },
  "raw": {
    "cage_no": "86",
    "strain": "ApoM Tg/Tg",
    "sex": "male",
    "mouse_id": "14",
    "ear_label": "R'",
    "dob": "26.01.21",
    "mating_date": "",
    "pubs": "",
    "status": ""
  },
  "normalized_candidate": {
    "evidence_type": "parent_mouse_row",
    "cage_label": "86",
    "sex": "male",
    "mouse_display_id": "14",
    "dob_start": "2026-01-21",
    "dob_end": "2026-01-21"
  },
  "confidence": 0.82,
  "review_status": "candidate",
  "applied_rule_keys": ["animal_sheet_parent_row"],
  "conflicts": []
}
```

Recommended `evidence_type` values:

| Evidence type | Source examples | Candidate target |
| --- | --- | --- |
| `mating_cage_block` | cage number plus parent rows and mating date | `mating_cage_candidate` |
| `parent_mouse_row` | sex-labeled parent rows in animal sheet | `mating_parent_candidate` |
| `litter_event_row` | `F1`, `F2`, pup count, litter DOB/status | `litter_event_candidate` |
| `current_pups_note` | `Pubs` value such as `26.04.20 9p` | open litter/current pups candidate |
| `maintenance_group_row` | single-sex count/DOB group in separation workbook | maintenance/separated cage candidate |
| `assignment_scope_row` | distribution workbook responsible person and expected counts | assignment comparison only |

## Candidate Output Shapes

### Cage Type Candidate

```json
{
  "candidate_type": "cage_type",
  "candidate_value": "mating",
  "confidence": 0.76,
  "source_evidence_ids": ["breed_ev_001", "breed_ev_002"],
  "supporting_signals": ["mixed_sex_plus_mating_date", "parent_style_rows"],
  "weakening_signals": [],
  "review_required": false,
  "review_reason": ""
}
```

Rules:

- `mating` is a candidate, not a canonical cage type, until accepted or written through the canonical workflow.
- Mixed sex alone should not exceed medium confidence.
- Mixed sex plus mating date plus parent-style rows can become high confidence.
- Stale card text, missing date, or contradictory single-sex workbook rows should lower confidence or create review.

### Mating Candidate

```json
{
  "candidate_type": "mating",
  "mating_label": "cage 86",
  "strain_goal_raw": "ApoM Tg/Tg",
  "start_date_raw": "26.01.21",
  "start_date_candidate": "2026-01-21",
  "parents": [
    {
      "role": "male",
      "mouse_display_id": "14",
      "source_evidence_id": "breed_ev_001"
    },
    {
      "role": "female",
      "mouse_display_id": "15",
      "source_evidence_id": "breed_ev_002"
    }
  ],
  "confidence": 0.78,
  "review_required": false,
  "blockers": []
}
```

Review required when:

- no male parent candidate exists,
- no female parent candidate exists,
- parent mouse ID matches multiple active mice,
- parent appears dead before the mating date,
- mating date is missing and no source structure strongly supports a mating block.

### Litter Event Candidate

```json
{
  "candidate_type": "litter_event",
  "litter_label": "F1",
  "mating_candidate_ref": "cage 86",
  "birth_date_raw": "26.03.24",
  "birth_date_candidate": "2026-03-24",
  "pup_count_raw": "9p",
  "pup_count_candidate": 9,
  "event_status_raw": "separated",
  "event_status_candidate": "separated",
  "source_evidence_ids": ["breed_ev_010"],
  "confidence": 0.8,
  "review_required": false,
  "conflicts": []
}
```

Review required when:

- litter DOB is earlier than mating date,
- first litter is too soon after mating unless the mating date is marked as late-entered/inherited,
- `Pubs` suggests an active litter but a newer separated/dead event exists,
- litter count and later separated mouse count cannot reconcile,
- `F1` or similar tokens appear outside an identified animal-sheet mating block.

### Maintenance Group Candidate

```json
{
  "candidate_type": "maintenance_group",
  "strain_raw": "ApoM Tg/Tg",
  "sex_candidate": "female",
  "count_raw": "8p",
  "count_candidate": 8,
  "dob_raw": "25.12.31 - 26.01.10",
  "dob_start_candidate": "2025-12-31",
  "dob_end_candidate": "2026-01-10",
  "genotype_counts_raw": {
    "Tg": "8"
  },
  "source_evidence_ids": ["breed_ev_020"],
  "confidence": 0.74,
  "review_required": false
}
```

Review required when:

- sex/count total does not reconcile with genotype counts,
- DOB span exceeds adopted grouping threshold,
- genotype labels are not configured for the accepted strain scope,
- source group conflicts with a more recent photo-backed cage card.

## Review Item Contract

Breeding review items should use the existing `review_queue` pattern and include a structured metadata payload.

```json
{
  "issue": "Breeding rule conflict",
  "review_reason": "Mixed-sex cage was inferred as mating, but no mating date or litter evidence was found.",
  "priority": "medium",
  "assigned_role": "Colony Reviewer",
  "source_name": "20260504 ApoM TgTg animal sheet_updated.xlsx",
  "metadata": {
    "rule_set_id": "breeding_rule_default_20260509",
    "rule_key": "mixed_sex_plus_mating_date",
    "rule_strength": "review_trigger",
    "candidate_type": "cage_type",
    "candidate_value": "mating",
    "confidence": 0.52,
    "source_evidence_ids": ["breed_ev_001", "breed_ev_002"],
    "conflicting_fields": [
      {
        "field": "mating_date",
        "raw_value": "",
        "expected_signal": "present"
      }
    ],
    "suggested_actions": ["confirm_mating_cage", "mark_holding_cage", "ignore_candidate"]
  }
}
```

Suggested `issue` values:

| Issue | Priority default | Notes |
| --- | --- | --- |
| `Breeding rule conflict` | medium | Candidate signals disagree. |
| `Biologically unlikely breeding date` | high | DOB/date order is implausible. |
| `Current pups overdue for separation review` | medium | Review only; not automatic cleanup. |
| `No-birth review` | low/medium | Raise only when source recency is adequate. |
| `Parent replacement review` | low/medium | Lower if recent litter evidence exists. |
| `Assignment scope mismatch` | low | Distribution workbook comparison only. |

## Processing Pipeline

1. Preserve workbook/photo as raw source.
2. Parse rows/note lines into breeding evidence payloads.
3. Apply source-structure rules to group rows into blocks.
4. Apply evidence-candidate rules to produce cage, mating, litter, and maintenance candidates.
5. Apply threshold rules only after date normalization confidence is adequate.
6. Generate review items for conflicts, low confidence, or biologically unlikely combinations.
7. Show candidate writes in an apply preview before touching canonical state.
8. Canonical writers create/update `mating_registry`, `mating_mouse`, `litter_registry`, `mouse_master`, and event/action logs only after accepted review or explicit policy.

## First Test Fixtures

Implement tests with compact fixture payloads, not full workbooks:

1. mixed sex with mating date and parent rows becomes high-confidence mating candidate;
2. mixed sex without date/litter evidence becomes reviewable mating candidate;
3. single-sex count/DOB row becomes maintenance candidate;
4. `F1` outside mating block is reviewable, not a litter event;
5. `Pubs` older than separation threshold creates review item only when no newer separated/dead evidence exists;
6. parent older than replacement threshold creates review item but does not close mating;
7. ApoM `all pups Tg` applies only when the strain-scoped assumption is selected;
8. missing litter evidence does not create no-birth review when source recency is unknown.

## Implementation Notes

- Initial implementation can keep rule config in a JSON fixture or Python constant, but table-ready field names should be preserved.
- Do not reuse labeling `crossed_out_handling = dead` for breeding rows. Labeling note lines and litter status rows have separate source contexts.
- Store confidence as `0.0` to `1.0` in new code unless an existing endpoint requires `0` to `100`; convert at API boundaries.
- Keep raw dates and normalized date ranges separate.
- Do not infer genotype categories from workbook columns unless those categories are accepted for the strain scope.
