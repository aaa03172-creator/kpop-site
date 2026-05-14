# UI/UX Revision Plan - 2026-05-13

Layer classification: implementation planning / non-canonical UI plan.

Canonical: false.

This plan turns `docs/ui_ux_review_2026-05-13_ko.md` into scoped implementation
slices. It does not change product policy, schema, API contracts, or lab workflow
rules by itself.

## Success Criteria

The UI revision is successful when:

1. Primary navigation and topbar counts represent operator workload, not hidden
   diagnostic/sample rows.
2. Review Queue answers `What needs my decision today?` in the first viewport.
3. Operations Home hides raw internal IDs from normal operator copy.
4. Export Center clearly separates preview/worklist downloads from final lab files.
5. Missing source photos render as explicit evidence states, not broken image UI.
6. External AI readiness copy always mentions approval when approval is required.
7. Pilot-critical mobile views remain readable without forcing horizontal scrolling
   for the main decision path.

## Slice 1 - Review Workload Counter Contract

Boundary classification:

- API/read model: export or view.
- Review items: review item.
- No canonical structured state changes.

Problem:

Global UI counts currently include hidden-default fixture/sample rows. This makes
the app show open review pressure while default Focus Review is intentionally empty.

Plan:

1. Add or derive a count model with:
   - `operator_workload_count`
   - `must_review_count`
   - `quick_check_count`
   - `open_review_total`
   - `hidden_diagnostic_count`
   - `trace_only_count`
2. Use `operator_workload_count` in topbar and primary nav.
3. Show hidden/diagnostic counts only in secondary chips or Settings diagnostics.
4. Keep `/api/export-preview` able to report total open reviews for audit, but do
   not make hidden-default rows look like daily work.

Likely files:

- `app/main.py`
- `static/index.html`
- `tests/test_review_attention.py`
- `tests/test_low_fatigue_ui_contracts.py`
- `tests/test_operations_home.py`

Verification:

- Seed hidden-default fixture reviews and assert topbar/nav primary count is `0`.
- Seed one must-review and one quick-check item and assert primary count is `2`.
- Assert hidden count remains visible only as diagnostics.

## Slice 2 - Review Queue First-Viewport Reorder

Boundary classification:

- UI only: export or view surface.
- No data writes.

Problem:

Review Queue shows role and priority master tables before active decision work.

Plan:

1. Reorder Review Queue so the first viewport shows:
   - filters,
   - workload summary,
   - Focus Review card list,
   - selected review/evidence detail.
2. Move review persona, priority, and vocabulary masters to Settings or a collapsed
   `Review configuration` section below active work.
3. Keep the existing master data available for debugging and audit, but secondary.

Likely files:

- `static/index.html`
- `tests/test_low_fatigue_ui_contracts.py`

Verification:

- Browser DOM/screenshot check that a seeded Focus Review card appears above role
  and priority master tables.
- Check empty state still says no Focus Review items without fabricating records.

## Slice 3 - Operator Copy Without Raw Internal IDs

Boundary classification:

- UI/read-model presentation: export or view.
- Raw IDs remain stored internally; no canonical data changes.

Problem:

Operations Home displays `review_id`, `parse_id`, and `source_photo_id` as primary
task copy.

Plan:

1. Replace raw ID lines with user-facing evidence summaries:
   - source photo filename,
   - review issue,
   - source note text,
   - mouse IDs or evidence preview,
   - assigned role/persona.
2. Add a collapsed `Debug details` disclosure for internal IDs when useful.
3. Avoid exposing internal IDs in normal card titles, subtitles, and task bodies.

Likely files:

- `static/index.html`
- `tests/test_operations_home.py`

Verification:

- Seed an Operations Home task and assert visible text does not contain
  `review_id:`, `parse_id:`, or `source_photo_id:`.
- Assert debug disclosure, if present, can still reveal IDs for troubleshooting.

## Slice 4 - Export Center Download Hierarchy

Boundary classification:

- Export preview and generated files: export or view.
- No canonical state writes from download controls.

Problem:

Search/CSV/worklist downloads appear before the final export gate, which can make
blocked final export state feel less authoritative.

Plan:

1. Place a compact gate banner near the top of Export Center.
2. Group actions into:
   - `Preview / search`
   - `Worklists`
   - `Final lab files`
3. Add labels or helper text stating whether each action is preview-only, worklist,
   or final.
4. Keep final lab files disabled until blockers are clear and accepted
   source-backed rows exist.

Likely files:

- `static/index.html`
- `app/main.py` only if read-model labels need support.
- `tests/test_artifact_workflow.py`
- `tests/test_browser_photo_export_e2e.py`

Verification:

- Browser check with one Focus Review blocker: final lab file buttons disabled and
  preview/worklist actions labeled as non-final or separately gated.
- Browser check with zero blockers and accepted rows: final buttons enabled with
  source-backed row count.

## Slice 5 - Source Photo Missing-State UI

Boundary classification:

- Source photo: raw source.
- Missing preview state: review item / export or view UI state.

Problem:

When source image loading fails, the current detail area can look like a broken
image rather than a named evidence state.

Plan:

1. Add `onerror` handling or render-time checks for source image preview.
2. Show an explicit state:
   - `Source photo unavailable`
   - filename/path if safe,
   - whether review can continue,
   - whether acceptance/export must be blocked.
3. Disable or relabel `Open source photo` when there is no usable image URL.

Likely files:

- `static/index.html`
- `tests/test_low_fatigue_ui_contracts.py`

Verification:

- Seed a review with source photo metadata but missing file and assert no broken
  image UI appears.
- Assert required-evidence reviews remain blocked or clearly marked.

## Slice 6 - External AI Readiness Copy

Boundary classification:

- Health/status copy: export or view.
- External inference payload: parsed or intermediate result only after approval.

Problem:

`local + AI draft ready` can overstate safety because approval is still required.

Plan:

1. Change topbar status to `AI draft: approval required` when `/api/health` reports
   `approval_required: true`.
2. Keep payload-minimization detail close to the extraction action.
3. Preserve local-only wording when no key/provider is available.

Likely files:

- `static/index.html`
- `tests/test_ai_payload_minimization.py`
- `tests/test_browser_photo_export_e2e.py`

Verification:

- Health state with API key: topbar says approval required.
- Health state without API key: topbar says local-only or AI unavailable.
- Browser E2E still confirms explicit approval before external inference.

## Slice 7 - Pilot Mobile Ergonomics

Boundary classification:

- UI layout only: export or view.
- No canonical data changes.

Problem:

Mobile viewport is usable, but pilot-critical dense tables still require horizontal
scrolling.

Plan:

1. Convert high-traffic mobile tables to stacked rows:
   - upload batches,
   - Focus Review cards,
   - final export blockers.
2. Keep horizontal scroll for low-priority audit/config tables.
3. Re-test `390 x 844` and desktop default viewport.

Likely files:

- `static/index.html`

Verification:

- Browser screenshots at desktop default and `390 x 844`.
- DOM check that pilot-critical rows remain readable without clipping primary labels.

## Recommended Order

1. Slice 1: Review Workload Counter Contract.
2. Slice 2: Review Queue First-Viewport Reorder.
3. Slice 3: Operator Copy Without Raw Internal IDs.
4. Slice 4: Export Center Download Hierarchy.
5. Slice 5: Source Photo Missing-State UI.
6. Slice 6: External AI Readiness Copy.
7. Slice 7: Pilot Mobile Ergonomics.

Reasoning:

The first three slices remove the largest day-to-day operator confusion. Export
hierarchy comes next because it protects final lab handoff. Missing source-photo
and AI copy are safety polish, and mobile ergonomics can follow once the decision
hierarchy is stable.

## Review Checklist Before Implementation

- Confirm whether fixture/sample hidden-default records should appear anywhere in
  normal operator chrome.
- Confirm whether CSV and genotyping worklist downloads are final exports,
  preview exports, or separately gated worklists.
- Confirm whether raw IDs should be visible only in debug disclosures or also in
  copied audit text.
- Confirm mobile support target for the first pilot: desktop-first only, tablet,
  or phone-compatible review.
