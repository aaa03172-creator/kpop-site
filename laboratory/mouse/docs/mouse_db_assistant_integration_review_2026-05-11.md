# MouseDB Assistant Integration Review

Layer classification: review item / non-canonical project documentation.
Canonical status: non-canonical. This document adapts external assistant-integration proposals to the current MouseDB repository. If this document conflicts with `AGENTS.md`, `final_mouse_colony_prd.md`, committed tests, or runtime behavior, call out the mismatch before implementation.

Date: 2026-05-11

Reviewed external inputs from the user's KakaoTalk received-files folder:

- `mouse_db_assistant_integration_seam_2026-05-10.md`
- `mouse_db_cli_first_mcp_ready_architecture_2026-05-10.md`
- `mouse_db_integration_review_packet_2026-05-10.md`

## Review Outcome

Disposition: accept with MouseDB-specific boundary changes.

The external proposal is directionally compatible with this repository. MouseDB should remain the canonical domain system for mouse colony records, while future assistant, API, or MCP surfaces should be thin orchestration layers over MouseDB-owned state and service logic.

The proposal should not be copied in as-is because it refers to second-brain parent documents that are not present in this workspace. In this repository, the adopted anchors are:

1. `AGENTS.md`
2. `final_mouse_colony_prd.md`
3. committed implementation and tests
4. `README.md`
5. non-canonical support documents listed in `docs/DOCUMENTATION_MAP.md`

## What Fits Current MouseDB

The following points are already aligned with the current project direction.

### MouseDB Owns Colony Truth

MouseDB should remain the truth owner for:

- source photos and cage-card records
- mouse identity
- cage and card snapshots
- accepted mouse state
- mating, litter, lineage, and parentage state
- genotype evidence and genotype results
- observations, corrections, review decisions, exports, and event history

Future assistants may summarize or route work, but they must not become a parallel source of truth for colony state.

### CLI-First Is Still Correct

The current `README.md` and `final_mouse_colony_prd.md` already describe MouseDB as CLI-first and service-layer based. This should remain the default posture:

```text
CLI or UI -> schemas/input validation -> services -> repositories -> models/db
```

Future API or MCP wrappers should reuse this boundary instead of reimplementing domain behavior.

### JSON Output Is A Public Integration Contract

Important CLI commands should keep stable `--json` output where practical. Later automation should consume JSON output or service/API read models, not scrape human-readable tables.

### Assistant Summaries Are Views

Assistant-facing summaries should be classified as `export or view`, `cache`, or another explicitly non-canonical layer unless a future adopted PRD section says otherwise.

They may include:

- `id`
- `uri`
- `family`
- `title`
- `status`
- `summary`
- `warnings`
- `updated_at`
- `related_refs`
- `next_operator_action`
- source or evidence references

They must not hide unresolved review items, low-confidence OCR, conflicting evidence, or missing lineage.

## Required MouseDB-Specific Changes To The Proposal

### 1. Add Photo And Review Objects To The Assistant Boundary

The external proposal focuses on `mouse`, `cohort`, `lineage`, `protocol`, `event`, and `attachment`.

For this repository, the first assistant-safe object families should include the photo-grounded workflow:

- `source_photo`
- `cage_card_snapshot`
- `review_item`
- `mouse`
- `cage`
- `mating`
- `litter`
- `genotype_result`
- `mouse_event`
- `export_manifest`

This reflects the current product rule: handwritten cage-card photos and related source records are raw evidence, and review/correction workflows protect canonical writes.

### 2. Use Current Lab Terms Before Generic Cohort Language

The proposal's `cohort` language is useful later, but the current product vocabulary is more specific:

- photos
- cage cards
- mouse IDs
- mating
- litter
- genotype
- review
- Excel export

If `cohort` is introduced, it should be defined as a configured or derived grouping, not silently treated as a primary canonical object.

### 3. Make Safety Classes Match Existing Review Gates

The proposal's mutation classes are good, but MouseDB should map them to current workflow gates.

| Safety class | MouseDB interpretation |
| --- | --- |
| `read_only` | Inspect accepted state, source evidence, review queue, export readiness, and recent events. |
| `additive_safe` | Add source evidence, create a review item, attach a note/file reference, or generate a non-canonical preview/export artifact. |
| `operator_confirmed` | Apply reviewed canonical candidates, correct parentage, change accepted genotype state, reassign cage/mating/litter state, archive records, or resolve conflicts. |

Even additive operations must preserve source references and avoid duplicate or orphan records.

### 4. URI Planning Should Include Evidence And Review

The suggested `mousedb://` URI family should be expanded before any assistant adapter becomes implementation-ready:

```text
mousedb://source-photo/{source_photo_id}
mousedb://cage-card/{card_snapshot_id}
mousedb://review-item/{review_item_id}
mousedb://mouse/{mouse_id}
mousedb://cage/{cage_id}
mousedb://mating/{mating_id}
mousedb://litter/{litter_id}
mousedb://genotype-result/{genotype_result_id}
mousedb://event/{event_id}
mousedb://export/{export_manifest_id}
```

These URIs are a planning direction, not a current runtime contract.

### 5. Assistant Read Models Need Evidence Warnings

MouseDB assistant summaries should include evidence and readiness signals beyond generic status text:

- source evidence count or representative source refs
- unresolved review blocker count
- low-confidence or conflicting parsed fields
- export readiness blockers
- whether values are raw, normalized, accepted, inferred, or cached
- next operator action in lab workflow language

This keeps uncertain cage-card and OCR-derived state visible instead of polished away.

## Deferred Or Rejected Parts

### Defer MCP Implementation

MCP should remain a later compatibility target. It is not a current implementation priority until the following are stable enough:

1. object identity and URI direction
2. service-layer read/write contracts
3. CLI JSON output for key commands
4. review and canonical-apply gates
5. evidence-backed summaries

### Defer Generic Protocol/Cohort Expansion

Protocol and cohort summaries may be useful later, but the current MVP priority is source photo -> review -> accepted state -> Excel export. Generic protocol or cohort abstractions should not pull effort away from that flow.

### Reject Assistant-Owned Colony Memory

Do not copy canonical MouseDB truth into a personal assistant memory layer as durable colony state. Assistants may store references, task queues, and bounded summaries that point back to MouseDB-owned records.

## Recommended MouseDB-Adapted Handoff Set

If these external notes are kept in this repository, prefer this adapted structure:

1. This review document as the local MouseDB-specific decision note.
2. The original external files preserved outside the repo or copied later under `docs/archive/` only if traceability is needed.
3. `docs/DOCUMENTATION_MAP.md` as the navigation and boundary source for future maintainers.

Do not mark the external proposal documents as canonical parents unless the missing second-brain documents are intentionally imported and adopted by the MouseDB project.

## Practical Next Steps

Use assistant-readiness as a standing design habit during ordinary MouseDB work. When touching IDs, CLI JSON output, service methods, read models, review workflows, export manifests, or generated artifacts, ask:

1. Does this preserve MouseDB as the owner of colony truth?
2. Can a future assistant point back to a source photo, note item, review item, accepted record, event, or export manifest?
3. Is the output machine-readable without forcing automation to scrape human-readable text?
4. Are uncertain OCR values, unresolved review blockers, and export blockers visible rather than summarized away?
5. Is any new automation-facing operation clearly read-only, additive/review-producing, or operator-confirmed?
6. Does this avoid starting an MCP/API adapter before the underlying service and review gates are stable?

Use this order if assistant-readiness later becomes active implementation work:

1. Inventory current public IDs and decide which object families need durable user-facing IDs.
2. Define draft `mousedb://` URI formats for source photos, review items, accepted records, events, and exports.
3. Audit key CLI commands for stable `--json` output and source/evidence references.
4. Define one or two non-canonical assistant read models, starting with `MouseReviewSummary` and `ExportReadinessSummary`.
5. Add tests proving summaries do not become canonical writes and do not hide unresolved review blockers.
6. Reconsider API or MCP only after those contracts are stable.

## Current Repository Fit

Current status after review:

- The proposal is compatible with the existing CLI-first and service-layer direction.
- The proposal should be adapted to emphasize photo evidence, review items, canonical apply gates, and Excel export readiness.
- The proposal should remain non-canonical until an adopted PRD update explicitly promotes any part of it.
- No implementation should begin solely from these external notes without checking `final_mouse_colony_prd.md`, tests, and current runtime behavior.
