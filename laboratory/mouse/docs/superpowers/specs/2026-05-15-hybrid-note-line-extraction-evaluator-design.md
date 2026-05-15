# Hybrid Note-Line Extraction Evaluator Design

Layer classification: parsed/intermediate workflow policy design.

Canonical: false.

## Objective

Improve real cage-card automatic extraction accuracy for mouse IDs and note-line continuity by combining existing local OCR/AI draft output, ROI crops, note-line parsing, labeling session rules, and review routing. The evaluator should raise the quality of automatic drafts before review, but it must not write canonical mouse, cage, mating, litter, genotype, event, or export state directly.

The first target metric is mouse ID and note-line exact-or-corrected-before-apply accuracy of at least 95% in the private copied-photo pilot, with zero unreviewed high-risk mouse ID or source-trace misses.

## Existing Assets To Reuse

The design builds on work already present in this repository:

- `app.main.parse_note_line` keeps numeric-only notes reviewable and separates raw note lines from parsed mouse IDs and ear-label candidates.
- `app.main.normalize_ear_label` handles prime/circle/zero ambiguity and impossible ear-label suffixes.
- `app.labeling_rules` applies ordered ear-label sequences, crossed-out handling, and sample-to-mouse matching as workflow policy.
- `labeling_rule_set` and `labeling_rule_ear_sequence` tables seed the ApoM Tg/Tg 2026-05-06 rule set.
- `config/roi_presets.json` defines card-level and note-area ROI crops for blue structured and yellow note-dense cage cards.
- `request_ai_transcription_draft` already requests exact raw visible text, symbol confusions, numeric-only note handling, ROI cross-checking, and conservative date normalization.
- `review_attention_level`, `review_check_targets`, and export blocker counts already route low-confidence or risky parsed evidence into `must_review` or `quick_check`.
- `scripts/report-private-accuracy.py` provides the local-only aggregate scoring surface for the private copied-photo pilot.

## Data Boundaries

| Artifact | Boundary | Rule |
| --- | --- | --- |
| Source cage-card photo | raw source | Preserve unchanged even when extraction fails. |
| ROI crop or line crop | cache | Derived from a raw photo; may be regenerated. |
| Local OCR candidate | parsed or intermediate result | Review aid only; never canonical by itself. |
| AI ROI candidate | parsed or intermediate result | Requires explicit per-run approval and payload minimization. |
| Rule-applied candidate | parsed/intermediate workflow policy result | Stores assumptions, conflicts, and confidence; not canonical. |
| Hybrid evaluator decision | review item routing signal | Chooses `trace_only`, `quick_check`, or `must_review`. |
| Reviewer correction | review item / correction history | Preserve before/after, source refs, and rule context. |
| Accepted mouse/event/export state | canonical structured state / export or view | Only after existing reviewed apply/export gates. |

## Scope

In scope:

- mouse ID candidate extraction from visible note lines;
- raw note-line preservation and line ordering;
- ear-label candidate normalization and ambiguity detection;
- selected labeling rule-set context for expected ear-label sequence;
- local OCR versus AI draft agreement scoring;
- conflict labels and applied rule keys on note-line evidence;
- review routing improvements for `quick_check` and `must_review`;
- private pilot scoring for note-line accuracy and reviewer workload.

Out of scope for the first slice:

- automatic canonical writes from OCR, AI, or evaluator output;
- broad OCR provider replacement;
- full card-layout detection beyond existing ROI presets;
- strain/genotype biological inference;
- automatic interpretation of all possible ear-marking systems;
- sending full colony records or predecessor Excel rows to external services.

## Evaluator Flow

1. A source photo is uploaded and preserved as raw source.
2. Existing ROI logic creates a normalized card crop and note-area ROI crop as cache.
3. Local OCR produces a note-line candidate set when available.
4. If the user approves external inference for the run, AI extraction produces a second note-line candidate set from the minimal card/ROI payload and assigned strain scope.
5. Each raw candidate line is passed through the existing `parse_note_line` and `normalize_ear_label` logic.
6. If a `labelingRuleSetId` is selected, the evaluator adds expected ear-label sequence context and crossed-out handling.
7. The evaluator compares local OCR, AI, parser, and rule context to produce a hybrid candidate with confidence, applied rules, conflicts, and routing.
8. The result is stored as parsed/intermediate evidence and attached to the existing review item or note item.
9. Existing canonical candidate apply and export gates decide whether reviewed state can move forward.

## Candidate Shape

The evaluator should use an additive structure so existing readers keep working:

```json
{
  "source_note_item_id": "note_parse_001_1",
  "line_number": 1,
  "raw_line_text": "101 R'",
  "candidate_kind": "hybrid_note_line",
  "ocr_candidate": {
    "raw": "101 R'",
    "mouse_display_id": "101",
    "ear_label_raw": "R'",
    "ear_label_code": "R_PRIME",
    "confidence": 0.72
  },
  "ai_candidate": {
    "raw": "101 R'",
    "mouse_display_id": "101",
    "ear_label_raw": "R'",
    "ear_label_code": "R_PRIME",
    "confidence": 0.88
  },
  "rule_candidate": {
    "labeling_rule_set_id": "label_rule_apom_tgtg_20260506",
    "expected_ear_label_code": "R_PRIME",
    "crossed_out_interpretation": "active"
  },
  "hybrid_candidate": {
    "mouse_display_id": "101",
    "ear_label_code": "R_PRIME",
    "confidence": 0.9,
    "routing": "quick_check"
  },
  "applied_rule_keys": [
    "ocr_ai_exact_note_line_agreement",
    "expected_ear_label_sequence_match"
  ],
  "conflicts": [],
  "source_refs": {
    "photo_id": "photo_001",
    "card_snapshot_id": "snapshot_001",
    "roi_label": "notes"
  }
}
```

This payload is parsed/intermediate evidence. It may be stored in a new helper table later or embedded as additive metadata on `card_note_item_log` / `photo_evidence_item`, but raw note-line text must remain unchanged.

## Scoring Rules

The evaluator should score agreement and conflicts conservatively:

- Increase confidence when local OCR and AI agree on raw line, mouse ID, and ear-label code.
- Increase confidence when the parsed ear label matches the expected labeling rule sequence.
- Increase confidence when line order is consistent with the selected cage/card group.
- Decrease confidence when OCR and AI disagree on mouse ID, ear label, or strike mark.
- Decrease confidence when a mouse number jumps without crossed-out/dead evidence.
- Decrease confidence when a parsed ear label conflicts with the expected sequence.
- Decrease confidence when a line is numeric-only; numeric-only notes stay reviewable and must not become mouse IDs automatically.
- Decrease confidence when a note line maps to a duplicate active mouse candidate.
- Route any impossible ear-label suffix, unclear strike, duplicate active mouse, or missing source reference to `must_review`.

The evaluator can emit `trace_only` only when the note line is not used for canonical candidate apply or export readiness. It can emit `quick_check` when automatic candidates agree and no high-risk conflict is present. It must emit `must_review` for any high-risk identity, evidence, or export-safety conflict.

## AI Prompt Context

When external AI extraction is approved, the prompt should include only minimal workflow policy context:

- selected labeling rule-set display name;
- ordered ear-label examples for the first several active mouse lines;
- instruction that crossed-out handling is context-specific and not global;
- reminder that numeric-only note lines are temporary labels or review anchors, not mouse IDs by default;
- assigned strain names/aliases already used for matching scope.

Do not send full colony records, predecessor Excel rows, accepted mouse tables, local database paths, or private manifest expected values.

## Review UI Behavior

Review detail should show the evaluator as an explanation, not as authority:

- raw source photo and note ROI stay visually primary;
- raw line, OCR candidate, AI candidate, rule candidate, and hybrid candidate are distinguishable;
- applied rule keys and conflicts are visible in compact form;
- reviewer can accept, correct, mark as numeric/count note, ignore, or send to manual transcription;
- corrections preserve before/after values and source evidence refs.

## Failure Taxonomy

The private accuracy report should use existing labels where possible:

- `mouse_id_or_note_line_error`
- `low_confidence_unreviewed`
- `raw_normalized_mixed`
- `source_trace_missing`
- `export_safety_error`
- `operator_workload_excessive`

Add evaluator-specific internal labels only when needed:

- `ocr_ai_note_line_disagreement`
- `expected_ear_sequence_conflict`
- `numeric_note_auto_id_blocked`
- `ambiguous_ear_suffix_reviewed`

Public reports should aggregate these labels without raw text or private paths.

## Testing Strategy

Focused tests should cover:

- OCR and AI exact agreement routes a note-line candidate to `quick_check`;
- AI/OCR mouse ID disagreement routes to `must_review`;
- expected ear-label sequence match raises confidence without overwriting raw text;
- expected ear-label sequence conflict creates a conflict label and review routing;
- crossed-out mouse line is skipped in active ear-label sequence under the selected rule;
- numeric-only notes remain `unlabeled_numeric_note` and cannot auto-create mouse IDs;
- impossible suffixes such as `RWM` stay reviewable;
- low-confidence OCR plus no AI agreement routes to `must_review`;
- hybrid metadata preserves `photo_id`, `card_snapshot_id`, note item, and ROI refs;
- private accuracy reporter can score the note-line field family from sanitized results.

Recommended focused verification:

```powershell
python -m pytest tests/test_labeling_session_rules.py tests/test_review_attention.py tests/test_ai_draft_normalization.py tests/test_ai_payload_minimization.py tests/test_synthetic_draft_extraction.py -q
npm run test:photo-e2e
npm run test:browser-photo-export-e2e
npm run test:python
```

## Implementation Order

1. Add a pure evaluator module that accepts OCR candidates, AI candidates, parsed note rows, and optional labeling rule context.
2. Add unit tests for scoring and routing before connecting it to API flows.
3. Attach evaluator metadata additively to note-line evidence without changing canonical apply semantics.
4. Pass selected labeling rule context into approved AI extraction prompts.
5. Surface evaluator explanation in review detail.
6. Extend private accuracy scoring to report evaluator-specific note-line failures.

## Open Questions

- Whether to store evaluator output in a new table or as metadata on existing note/evidence rows.
- Whether line-level ROI crops are needed before or after the first 20-30 copied-photo pilot.
- Whether local OCR confidence should be calibrated per ROI template type.
- Whether the first pilot should require AI extraction for all photos or only for low-confidence local OCR notes.

## Approval Gate

This design is ready for implementation planning when the user confirms that the first implementation slice should focus on the pure evaluator and note-line metadata, without changing canonical apply behavior.
