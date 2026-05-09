# Labeling Rule UI Design

Layer classification: implementation planning / non-canonical project note.

## Goal

Expose the active labeling session rule in the local Genotyping Worklist so rule-based sample matching is visible and applied when requesting genotyping.

## Scope

- Add a read-only API for configured labeling rule sets.
- Show a rule selector in the Genotyping Worklist request form.
- Display the selected rule's sample mapping, default target, and crossed-out handling as processing assumptions.
- Submit `labeling_rule_set_id` with genotyping requests.
- Surface API conflicts, including sample ID mismatch, without creating partial genotyping state.

## Data Boundaries

| Artifact | Boundary | Notes |
| --- | --- | --- |
| `labeling_rule_set` rows | parsed/intermediate workflow policy | Configures parsing and matching assumptions; not canonical mouse state. |
| selected rule in UI | reviewable processing assumption | User-visible choice for one request, not a mouse record by itself. |
| submitted `labeling_rule_set_id` | parsed/intermediate evidence on generated records | Preserved in event details when a request is accepted. |
| mismatch error | review item candidate / blocking feedback | Prevents silent sample-to-mouse attachment. |

## Recommended Approach

Use the existing single-page app and FastAPI patterns. Add `GET /api/labeling-rule-sets`, fetch it during `refresh()`, render a compact selector in the Genotyping request form, and include the selected ID in `/api/genotyping/request`.

This keeps the implementation small and avoids introducing a full rule management screen before the lab workflow needs editing controls.

## Acceptance Checks

- The active ApoM Tg/Tg rule appears in the Genotyping Worklist.
- The UI shows `sample_id_equals_mouse_display_id` and default target `ApoM-tg` for that rule.
- Request Genotyping sends `labeling_rule_set_id`.
- API mismatch errors are shown to the user rather than failing silently.
- Raw sample IDs and existing mouse records remain unchanged when the API rejects a mismatch.
