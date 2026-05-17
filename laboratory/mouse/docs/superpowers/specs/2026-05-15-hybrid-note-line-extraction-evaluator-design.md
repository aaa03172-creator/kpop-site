# Hybrid Note-Line Extraction Evaluator Design

Layer classification: parsed/intermediate workflow policy design.

Canonical: false.

## Objective

Improve real cage-card automatic extraction accuracy for mouse IDs and note-line continuity by combining existing local OCR/AI draft output, ROI crops, note-line parsing, labeling session rules, and review routing. The evaluator should raise the quality of automatic drafts before review, but it must not write canonical mouse, cage, mating, litter, genotype, event, or export state directly.

The first automatic-extraction target metric is `pre_review_exact_rate` for mouse IDs and note-line continuity in the private copied-photo pilot. The evaluator should also report `auto_candidate_usable_without_edit`, `review_correction_rate`, and local-OCR-to-hybrid delta so automatic draft quality is not confused with reviewer-corrected safety.

The first safety target remains mouse ID and note-line exact-or-corrected-before-apply accuracy of at least 95%, with zero unreviewed high-risk mouse ID or source-trace misses.

## Metric Definitions

The private pilot should score note-line extraction at the note-line case level. A scored case is one visible note-line expectation in the private manifest, including mouse ID lines, numeric-only temporary labels, struck note lines, and mating/litter context lines that the evaluator attempts to classify.

- `pre_review_exact_rate`: scored note-line cases where the pre-review hybrid candidate exactly preserves the expected raw note-line continuity anchor and, when applicable, exact mouse ID and ear-label code, divided by all scored note-line cases.
- `auto_candidate_usable_without_edit`: scored note-line cases where the pre-review candidate could be accepted after source-photo check without text correction, divided by all scored note-line cases.
- `review_correction_rate`: scored note-line cases requiring reviewer text or classification correction before apply, divided by all scored note-line cases.
- `local_ocr_to_hybrid_delta`: hybrid `pre_review_exact_rate` minus local-OCR-only `pre_review_exact_rate` on the same scored note-line cases.
- `exact_or_corrected_before_apply`: scored note-line cases that were either pre-review exact or corrected by a reviewer before canonical apply/export use, divided by all scored note-line cases.

Identity continuity errors, missing source refs, and unreviewed high-risk misses are hard-gate failures even when aggregate rates pass.

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
  "source_quality": {
    "source_image_quality": "acceptable",
    "roi_alignment_confidence": 0.86,
    "line_segmentation_confidence": 0.81,
    "quality_flags": []
  },
  "rule_candidate": {
    "labeling_rule_set_id": "label_rule_apom_tgtg_20260506",
    "labeling_rule_display_name": "ApoM Tg/Tg 2026-05-06",
    "labeling_rule_effective_from": "2026-05-06",
    "labeling_rule_hash": "sha256:6b4d2e0f8a1c9d3e",
    "expected_ear_label_code": "R_PRIME",
    "raw_strike_status": "none",
    "default_strike_interpretation": "active",
    "rule_interpretation_candidate": "active",
    "rule_interpretation_boundary": "review hint only"
  },
  "hybrid_candidate": {
    "mouse_display_id": "101",
    "ear_label_code": "R_PRIME",
    "confidence": 0.9,
    "routing": "quick_check"
  },
  "applied_rule_keys": [
    "ocr_ai_exact_note_line_agreement",
    "rule_consistency_expected_ear_label_sequence"
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

## Rule Safety Requirements

Rules improve candidate ranking and review routing, but they are not direct evidence. The evaluator must keep rule assumptions visible and reproducible:

- Store a rule snapshot identifier with each evaluator result: rule set ID, display name, effective date or session date, and a stable hash of the fields used for evaluation.
- Compute the rule hash from a stable JSON object with sorted keys. The first hash input fields are `rule_set_id`, `display_name`, `session_date` or `effective_from`, `crossed_out_handling`, ordered `ear_label_sequence`, `sample_mapping`, and `genotyping_target` when present.
- Preserve `raw_strike_status` separately from any default or rule-specific interpretation.
- Store `default_strike_interpretation` and `rule_interpretation_candidate` separately. A selected rule may propose that a crossed-out mouse line means dead, moved, separated, or needs review, but the evaluator must not overwrite the raw strike mark or silently create a canonical event.
- Treat crossed-out handling as source-context-specific. The labeling-session rule for mouse-number note lines must not be reused for mating/litter rows, workbook cleanup notes, or free-text breeding statuses.
- Treat expected ear-label sequence as a consistency check only. It can explain why a reviewer should inspect a line, but it must not convert weak visual evidence into a high-confidence mouse identity.
- Show rule scope in review surfaces using lab-facing wording, such as `Rule used: ApoM Tg/Tg 2026-05-06, review hint only`.
- Keep strain-specific assumptions as reviewable candidates. A rule such as default genotype for pups should return candidate metadata with `review_required`, not a bare accepted value.
- Move breeding confidence weights, such as mixed-sex plus mating-date deltas, into configurable rule signals before using them to drive automatic routing beyond review suggestions.

## Scoring Rules

The evaluator should score agreement and conflicts conservatively:

- Increase confidence when local OCR and AI agree on raw line, mouse ID, and ear-label code.
- Treat expected labeling rule sequence matches as `rule_consistency` signals, not visual evidence. A sequence match may lower review burden only when OCR/AI/raw visual candidates are independently plausible; it must not raise confidence by itself.
- Increase confidence when line order is consistent with the selected cage/card group.
- Decrease confidence when OCR and AI disagree on mouse ID, ear label, or strike mark.
- Decrease confidence when OCR and AI agree but share weak input quality, such as low ROI alignment confidence, low source image quality, or uncertain line segmentation.
- Decrease confidence when a mouse number jumps without crossed-out/dead evidence.
- Decrease confidence when a parsed ear label conflicts with the expected sequence.
- Decrease confidence when the selected rule set is missing, stale for the batch, outside the photo's scope, or lacks a reproducible snapshot hash.
- Decrease confidence when a line is numeric-only; numeric-only notes stay reviewable and must not become mouse IDs automatically.
- Decrease confidence when a note line maps to a duplicate active mouse candidate.
- Route any impossible ear-label suffix, unclear strike, duplicate active mouse, or missing source reference to `must_review`.

The evaluator can emit `trace_only` only when the note line is not used for canonical candidate apply or export readiness. It can emit `quick_check` when automatic candidates agree, source/ROI quality is acceptable, and no high-risk conflict is present. It must emit `must_review` for any high-risk identity, evidence, or export-safety conflict.

## AI Prompt Context

When external AI extraction is approved, the prompt should include only minimal workflow policy context:

- selected labeling rule-set display name;
- ordered ear-label examples for the first several active mouse lines;
- instruction that crossed-out handling is context-specific and not global;
- instruction that rule context is only a review hint and must never override visible raw transcription;
- reminder that numeric-only note lines are temporary labels or review anchors, not mouse IDs by default;
- assigned strain names/aliases already used for matching scope.

Do not send full colony records, predecessor Excel rows, accepted mouse tables, local database paths, or private manifest expected values.

## Review UI Behavior

Review detail should show the evaluator as an explanation, not as authority:

- raw source photo and note ROI stay visually primary;
- raw line, OCR candidate, AI candidate, rule candidate, and hybrid candidate are distinguishable;
- applied rule keys and conflicts are visible in compact form;
- selected rule set, scope, and `review hint only` status are visible wherever rule-derived candidates are shown;
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
- OCR and AI agreement with weak ROI/source quality still routes to `must_review`;
- AI/OCR mouse ID disagreement routes to `must_review`;
- expected ear-label sequence match records `rule_consistency` without overwriting raw text or raising confidence by itself;
- expected ear-label sequence conflict creates a conflict label and review routing;
- evaluator output stores a rule snapshot hash and rule scope metadata;
- crossed-out note lines preserve raw strike status, default interpretation, and rule-specific candidate interpretation separately;
- strain-specific assumptions return reviewable candidate metadata rather than bare accepted values;
- breeding confidence weights used by routing are read from configurable rule signals before any non-review use;
- AI prompt context includes a guard that rules cannot override visible raw transcription;
- crossed-out mouse line is skipped in active ear-label sequence under the selected rule;
- numeric-only notes remain `unlabeled_numeric_note` and cannot auto-create mouse IDs;
- impossible suffixes such as `RWM` stay reviewable;
- low-confidence OCR plus no AI agreement routes to `must_review`;
- hybrid metadata preserves `photo_id`, `card_snapshot_id`, note item, and ROI refs;
- pilot reports separate `pre_review_exact_rate`, `auto_candidate_usable_without_edit`, and `review_correction_rate`;
- private accuracy reporter can score the note-line field family from sanitized results.

Recommended focused verification:

```powershell
python -m pytest tests/test_labeling_session_rules.py tests/test_review_attention.py tests/test_ai_draft_normalization.py tests/test_ai_payload_minimization.py tests/test_synthetic_draft_extraction.py -q
npm run test:photo-e2e
npm run test:browser-photo-export-e2e
npm run test:python
```

## Implementation Phases

Phase 1: pure note-line evaluator.

1. Add a pure evaluator module that accepts OCR candidates, AI candidates, parsed note rows, source/ROI quality signals, and optional labeling rule context.
2. Add unit tests for scoring and routing before connecting it to API flows.
3. Add a stable rule snapshot helper for labeling rule context used by the evaluator.
4. Attach evaluator metadata additively to existing note-line evidence without changing canonical apply semantics.

Phase 2: rule safety cleanup.

1. Pass selected labeling rule context into approved AI extraction prompts with confirmation-bias guardrails.
2. Surface evaluator explanation and rule scope in review detail.
3. Convert adjacent breeding-rule confidence weights into configurable signals before using them for any routing beyond review suggestions.
4. Change strain-specific assumption helpers to return reviewable candidate metadata before they are reused by evaluator or export flows.

Phase 3: pilot scoring and reporting.

1. Extend private accuracy scoring to report evaluator-specific note-line failures.
2. Report `pre_review_exact_rate`, `auto_candidate_usable_without_edit`, `review_correction_rate`, and local-OCR-to-hybrid delta separately.
3. Include source/ROI quality breakdowns in private aggregate reports without private photo paths or raw text.

## Storage And Pilot Decisions

- First implementation slice should store evaluator output as additive metadata on existing note/evidence rows, such as `card_note_item_log.parsed_metadata_json` and related `photo_evidence_item` references. A separate table can be introduced after the private pilot if reporting or query complexity justifies it.
- First implementation slice should capture source/ROI quality and line ordering signals even if line-level crop files are not yet persisted.
- First implementation slice should include rule snapshot metadata in `parsed_metadata_json`; a future table can normalize it if repeated hashes become useful for reporting.
- Local OCR confidence should be reported by ROI template type when available, but template-specific calibration can follow the first private pilot.
- The first private pilot should compare local OCR only versus hybrid output. AI extraction should be approved per run and used for all pilot photos only if the operator explicitly wants a full AI-assisted baseline; otherwise use it for low-confidence or high-risk note-line cases first.

## Approval Gate

This design is ready for implementation planning when the user confirms that the first implementation slice should focus on the pure evaluator and note-line metadata, without changing canonical apply behavior.
