# MouseDB open-design Artifact Workflow Review

Layer classification: implementation planning / non-canonical project note.

Canonical: false. This document does not introduce an open-design runtime dependency, change database schema, redefine MouseDB as a design generator, or authorize AI/parser output to write canonical mouse state directly.

## Executive Summary

Decision: **do not adopt open-design as a product dependency**.

Recommended adoption is **structure-only**:

- keep MouseDB local-first and SQLite/service-layer centered;
- use existing `canonical_candidate` apply-preview as the canonical preview-before-commit path;
- document file-backed artifacts for proposed changesets, validation reports, export manifests, and review batches;
- strengthen traceability between export logs, validation reports, and the canonical state that produced each export;
- do not add open-design daemon, skill marketplace, design-system registry, or design-generation scope to MouseDB v1.

This is a partial conceptual adoption, not a package or runtime adoption.

## Why Not Install open-design

open-design is optimized for design artifact generation: local daemon, agent adapters, `SKILL.md` registry, design systems, sandboxed preview, and web/deck/image/video exports.

MouseDB is a local-first colony evidence system. Its risk surface is different:

- handwritten cage-card photos are raw evidence;
- OCR/AI output is a parsed draft;
- review and correction are required before high-risk writes;
- canonical mouse/cage/genotype/event state must be traceable;
- Excel files are derived views;
- lab data must not be sent to external tools unless explicitly approved.

Installing open-design would add runtime complexity and conceptual pressure toward design-generation workflows that are outside MouseDB core v1.

## What To Borrow

Borrow these patterns only:

1. **Artifact folder discipline**
   Store durable, reviewable generated artifacts as plain files with metadata.

2. **Preview before commit**
   Show proposed state changes before canonical writes. MouseDB already has this through `/api/canonical-candidates/{candidate_id}/apply-preview`.

3. **Self-check gate**
   Generate a validation report before canonical apply or final export.

4. **Append-only history mindset**
   Keep `action_log`, `mouse_event`, `correction_log`, and export manifests linked instead of silently rewriting high-risk state.

5. **Runtime/source separation**
   Keep transient caches separate from reviewable artifacts and canonical state.

## What Not To Borrow

Do not borrow:

- open-design as a product dependency;
- local design daemon;
- design skill registry as-is;
- design-system `DESIGN.md` registry;
- agent-driven direct file/database mutation;
- cloud/BYOK design generation path for lab records;
- sandboxed iframe as a core data-correctness mechanism;
- UI/design generation as MouseDB v1 scope.

## Current MouseDB Fit

MouseDB already has the most important pieces:

- `photo_log`: raw source photo records;
- `parse_result`: parsed/intermediate drafts;
- `card_snapshot`: source-backed observed card state;
- `card_note_item_log`: note-line evidence;
- `review_queue`: user review boundary;
- `canonical_candidate`: draft canonical update proposal;
- `/api/canonical-candidates/{candidate_id}/apply-preview`: preview-before-commit;
- `/api/canonical-candidates/{candidate_id}/apply`: guarded canonical apply;
- `/api/canonical-candidates/{candidate_id}/audit` and `/void`: audit and non-destructive reversal path;
- `mouse_master`, `mouse_event`, `genotyping_record`, cage/mating/litter tables: canonical structured state;
- `export_log`: generated/blocked export record;
- `evals/cage_card_skill_gym/`: non-canonical safety probes.

The missing layer is not another runtime. The missing layer is a clearer artifact contract around changesets, validation reports, and export provenance.

## Recommended Artifact Root

Use a project-local folder only when an artifact needs file-level review, export, or attachment. Do not duplicate every database row into files.

```text
mousedb_artifacts/
  proposed_changesets/
  validation_reports/
  review_batches/
  export_manifests/
  exports/
    separation_xlsx/
    animalsheet_xlsx/
  action_history/
```

Recommended `.gitignore` stance:

- commit schemas, docs, and synthetic fixtures;
- do not commit real lab photos, real workbook exports, or generated reports from real data by default;
- allow synthetic validation reports under fixtures only when explicitly adopted for tests.

## Proposed MouseDB Artifact Lifecycle

```text
raw cage card photo
-> photo_log
-> parse_result
-> card_snapshot
-> card_note_item_log
-> review_queue
-> canonical_candidate
-> apply-preview / proposed changeset artifact
-> validation report
-> approved canonical mouse/cage/genotype/event update
-> export preview
-> export validation report
-> export artifact
-> export_log + export manifest
```

Boundary rules:

- raw source photo stays raw source;
- parsed result remains draft/intermediate;
- review queue is the human decision boundary;
- `canonical_candidate` is still not canonical until applied;
- apply preview and validation report are export/view artifacts;
- only approved apply writes canonical structured state;
- Excel exports remain derived artifacts.

## Preview-Before-Commit Standard

MouseDB should standardize the existing canonical candidate flow as the only safe apply path:

1. Create or resolve review item.
2. Create `canonical_candidate` draft.
3. Run apply preview.
4. Generate proposed changeset artifact when a durable review record is needed.
5. Run self-check gate.
6. If blockers exist, keep candidate draft/reviewable.
7. If user approves and checks pass, apply in one transaction.
8. Write `mouse_event` and `action_log`.
9. Make audit/void available.

AI parsing, workbook import, or inferred movement must not bypass this path.

## Self-Check Gate

Before canonical apply or final export, validation should produce a report with these checks at minimum:

| Check | Apply behavior |
| --- | --- |
| duplicate active mouse ID | block canonical apply |
| impossible date | block normalized date write; preserve raw date |
| genotype conflict | block experiment release; may block export depending status |
| cage mismatch | route to review unless supported by movement evidence |
| ambiguous ear label | block identity-sensitive canonical apply |
| uncertain strike status | block moved/dead event apply |
| count mismatch | route separated-card summary to review |
| missing source trace | block canonical apply and final export |
| open Focus Review blocker | block final export |

The report should be deterministic. An LLM may explain a report only after the deterministic gate has produced findings.

## Export Provenance

Current `export_log` records type, filename, query, row count, blockers, status, and source layer. The next safe improvement is to link each generated export to:

- validation report id/path;
- canonical state watermark or source max timestamp;
- source note item ids and photo ids included in the export;
- export preview query/filter;
- generated file path or artifact path if saved locally.

This makes it clear which accepted state produced a given `분리.xlsx` or `animalsheet`.

## Artifact Preview For Page Design

The page can use open-design's layout idea without adopting its runtime:

- left: photo/review queue/evidence;
- center: proposed changeset or workbook preview;
- right: validation report, blockers, and action log;
- primary action: `Preview apply`, then `Apply accepted changes`, then `Export`.

The page should not become a design-generation surface. It should be an evidence and state-change review surface.

## Concrete PR Recommendation

Safe PR scope:

1. Add this review document.
2. Add JSON schemas for proposed changeset and validation report artifacts.
3. Later, optionally add an export manifest schema.
4. Do not change runtime behavior in this PR.
5. Do not add open-design dependency.

Follow-up implementation PRs can then:

- persist proposed changeset artifacts from existing apply-preview output;
- persist validation report artifacts for apply/export gates;
- add `validation_report_ref` and `state_watermark` to export logging if adopted.

## Final Recommendation

Do **not** install open-design.

Adopt the artifact workflow pattern only where it directly improves MouseDB correctness:

- proposed changeset before canonical apply;
- deterministic validation report;
- export manifest/provenance;
- local artifact folder for reviewable generated outputs;
- no new product runtime dependency.
