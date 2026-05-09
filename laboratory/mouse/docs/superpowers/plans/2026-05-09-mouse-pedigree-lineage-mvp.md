# Mouse Pedigree / Lineage MVP Plan

> **For agentic workers:** This plan is a non-canonical implementation guide. It describes a small read-only UI slice and does not define database truth, final export schemas, or lab workflow policy.

## Goal

Add a compact Mouse Detail pedigree / lineage panel that helps a lab user answer, "Where did this mouse come from?" without inferring uncertain relationships or mutating colony state.

The first slice should show only the selected mouse path: accepted parent IDs, source litter, source mating, same-litter siblings, field-level evidence, and review attention links.

## Data Boundary

- API response: export or view
- `mouse_master`: canonical structured state
- `mating_registry`: canonical structured state
- `litter_registry`: canonical structured state
- `source_record`: raw/source reference metadata
- Missing or conflicting relationships: review item
- Rendered layout: view/cache, never canonical

If a relationship is not already accepted in canonical state, it must appear as pending review rather than confirmed.

## API Contract

Candidate endpoint:

```text
GET /api/ui/mouse-pedigree?mouse_id=MT401
```

Top-level response fields:

- `source_layer`
- `page_question`
- `mode`
- `mouse`
- `relationship_summary`
- `nodes`
- `evidence_rows`
- `attention_links`
- `empty_state`

The first payload must not expose raw review item details. It should link unresolved relationships to Focus Review.

## Workflow Rules

- Start from the selected mouse.
- Read accepted parent, litter, and mating values from canonical tables.
- Attach source evidence per field where available.
- Show unresolved parent relationships as pending.
- Route open review attention to Focus Review.
- Do not create events, infer parents, or mutate colony state from this endpoint.

## UI Rules

- Use a light, low-fatigue layout.
- Render the selected path by default rather than a full graph.
- Show confirmed relationships and pending relationships distinctly.
- Put pending evidence and review needs near the top.
- Use mouse IDs as primary labels.
- Keep strain, status, sex, and genotype as secondary metadata.
- Show same-litter siblings as a compact grouped row.
- Keep field evidence visible and source-backed.

## Implementation Tasks

- [x] Add contract tests for `/api/ui/mouse-pedigree`.
- [x] Implement the read-only API from accepted canonical tables.
- [x] Verify empty state does not fabricate relationships.
- [x] Add a static Mouse Detail panel against the API contract.
- [x] Add MVP verification coverage for pending relationships, siblings, and Focus Review links.

## Deferred

- Full multi-generation interactive tree
- Zoom or minimap controls
- Export or print pedigree view
- Barcode or QR workflows
- Calendar or external writeback
