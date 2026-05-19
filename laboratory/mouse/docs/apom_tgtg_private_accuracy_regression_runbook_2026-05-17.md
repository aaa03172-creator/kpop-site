# ApoM tgtg Private Accuracy Regression Runbook

Layer classification: review item / local operations runbook. Canonical: false.

This runbook describes how to rerun the private ApoM tgtg field-level accuracy regression from review resolution audit metadata. It is an operator procedure and audit aid, not canonical colony state.

## Data Boundary

Keep all raw photos, private paths, local SQLite files, generated scoring input, and generated Markdown reports under `data/` ignored private run folders. Do not commit private run outputs unless a separate review confirms they contain only sanitized aggregate metrics.

Classify the artifacts as:

| Artifact | Boundary | Commit policy |
| --- | --- | --- |
| Source cage-card photos | raw source | Local-only under `data/` ignored folders. |
| `real-photo-hybrid-manifest.json` | review item / test fixture | Private local fixture; may include private source references. |
| `review-scoring-audit-with-field-outcomes.sqlite` | review item / local audit database | Local-only. |
| `review-scoring-audit-export-input-with-field-outcomes.json` | review item / private accuracy scoring input | Baseline sanitized input for regression comparison; keep in private run folder. |
| Generated `review-scoring-audit-export-input-*.json` | review item / private accuracy scoring input | Generated local-only output. |
| Generated `sanitized-private-accuracy-*.md` | review item / sanitized private accuracy report | Publish only after leak checks and explicit review. |
| Generated `field-outcomes-regression-comparison-*.json` | review item / private accuracy regression comparison | Generated local-only output. |
| `private-accuracy-regression-history.json` | review item / private accuracy regression history | Local-only sanitized run index; keep under ignored `data/`. |

## Command

Run from the `laboratory/mouse` project directory:

```powershell
Set-Location "<repo root>/laboratory/mouse"
$base = "<private run dir>"
npm run pilot:private-accuracy-regression -- `
  --db-path "$base/review-scoring-audit-with-field-outcomes.sqlite" `
  --manifest "$base/real-photo-hybrid-manifest.json" `
  --run-dir "$base" `
  --run-label "apom-tgtg-17-field-outcome-regression-YYYYMMDD" `
  --suffix "field-outcomes-gated-regression-YYYYMMDD" `
  --baseline-results "$base/review-scoring-audit-export-input-with-field-outcomes.json" `
  --history-index "$base/private-accuracy-regression-history.json" `
  --json
```

The command writes:

- `review-scoring-audit-export-input-<suffix>.json`
- `sanitized-private-accuracy-<suffix>.md`
- `field-outcomes-regression-comparison-<suffix>.json`
- `private-accuracy-regression-history.json`

The CLI summary intentionally reports private output locations as `private output path omitted`.

## Pass Criteria

Treat the run as passing only when all of these are true:

| Check | Expected |
| --- | --- |
| `status` | `passed` |
| `decision` | `go` |
| `matched_case_count` | `17` for the current ApoM tgtg run |
| `unmatched_audit_count` | `0` |
| `missing_result_case_count` | `0` |
| `extra_result_case_count` | `0` |
| `result_validation_failures` | `0` |
| `regression_gate.status` | `passed` |
| `regression_gate.field_outcome_integrity_status` | `passed` |
| `regression_gate.comparison_all_key_metrics_match` | `true` |
| Sanitized payload validation | No blocked private keys, path markers, raw OCR markers, or secret markers |
| `baseline_promotion.status` | `ready_for_operator_promotion` before any baseline file is changed |

Latest checked ApoM tgtg result on 2026-05-17:

- Decision: `go`
- Matched cases: `17/17`
- Field outcome integrity: no scope missing, no empty scoped payload, no invalid scoring status, no scored scope missing scored cases
- Baseline comparison: all key metrics matched
- Hard gates included private data containment, traceability, review blocking, silent_overwrite prevention, accuracy thresholds, and hybrid evaluator input validation

## Failure Handling

If `field_outcome_integrity.missing_scope` is non-empty, a review resolution produced field-level scoring data without a note-line scoring scope. Reopen the corresponding review audit trail and correct the review resolution metadata before using the report.

If `field_outcome_integrity.empty_scoped` is non-empty, a review resolution selected a scoring scope but did not record any field score or failure label. Treat the case as incomplete review scoring.

If `field_outcome_integrity.scored_scope_missing_scored_cases` is non-empty, a review resolution marked a note line as scored without preserving the scoring taxonomy needed for hybrid evaluator metrics. Correct the review scoring audit metadata before using the report.

If `comparison.all_key_metrics_match` is false, inspect the comparison JSON. A metric mismatch can be legitimate only when the baseline intentionally changed. Otherwise, treat it as a regression and investigate the exporter, reporter, or audit DB before publishing results.

If `decision` is not `go`, do not treat the run as ready. Check failed hard gates first, especially traceability, review blocking, silent_overwrite prevention, and accuracy thresholds.

If the exporter reports `sanitized payload validation failed`, treat the generated scoring input as unsafe to share. Fix the exporter or review audit mapping before rerunning; the error intentionally names only violation categories, not private values.

## Run History And Baseline Promotion

The history index is local-only and non-canonical. It stores sanitized run summaries, artifact filenames, comparison status, field outcome integrity, and baseline promotion eligibility. It must not contain absolute paths, raw photo references, raw OCR/AI text, or reviewer free text.

Treat `baseline_promotion.recommended_action` as an instruction for the operator, not an automatic file mutation. Only promote a generated results file to the baseline after all of these are true:

- `baseline_promotion.eligible` is `true`.
- `baseline_promotion.recommended_action` is `operator_may_promote_current_results_to_baseline_after_review`.
- The operator has inspected the generated report and leak check output.
- The candidate filename in `baseline_promotion.candidate_results_filename` is the intended baseline source.

If `baseline_promotion.status` is `blocked`, do not update the baseline. Use `baseline_promotion.blocked_reasons` to decide whether the issue is a regression gate failure, a baseline comparison mismatch, incomplete field outcome integrity, or a missing baseline input.

If `report_hard_gate_failures` includes `manifest_validation`, first confirm the private manifest points to existing local source photos. Do not promote a baseline from a run whose source photo evidence cannot be verified.

## Leak Check

Before sharing any generated report, search the new output files for private markers:

```powershell
Select-String -Path "$base/review-scoring-audit-export-input-<suffix>.json",`
  "$base/sanitized-private-accuracy-<suffix>.md",`
  "$base/field-outcomes-regression-comparison-<suffix>.json" `
  -Pattern '<private-marker-pattern-list>'
```

Expected result: no matches. Private source paths, raw OCR text, raw AI text, and raw cage-card photo references must not appear in sanitized regression outputs.

## Git Hygiene

After running the regression, check:

```powershell
git status --short --ignored
```

Expected tracked state: no changes unless you intentionally edited source, tests, or documentation. Generated private outputs should remain ignored under `data/`.
