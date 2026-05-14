# UI/UX Review - 2026-05-13

Layer classification: review item / non-canonical UI review documentation.

Canonical: false.

This review evaluates the current local MouseDB browser UI against `AGENTS.md`,
`final_mouse_colony_prd.md`, `docs/ui_interaction_visual_feedback_direction_2026-05-11_ko.md`,
and the executable UI surface. It does not define database schema, API response
shape, lab policy, or final product behavior.

## Review Scope

Reviewed flow:

1. Empty local app load.
2. Fixture parse import through `/api/fixtures/import-sample`.
3. Review Queue default and all-review states.
4. Seeded Focus Review state with one must-review blocker and one quick-check item.
5. Operations Home task summary.
6. Export Center blocked final export state.
7. Mobile viewport smoke check at `390 x 844`.

Runtime evidence:

- Local URL: `http://127.0.0.1:8765`.
- Browser title: `Mouse Colony LIMS - Photo Review Workbench`.
- Console check: no relevant browser `error` or `warn` logs observed in the inspected states.
- API checks used: `/api/health`, `/api/ui/focus-review`, `/api/review-items`, `/api/export-preview`.
- Disposable data only: sample fixture records plus a seeded synthetic focus-review card in a temp data directory.

## Perspective Summary

| Perspective | What works | Main UX risk |
| --- | --- | --- |
| Product/data boundary | The UI consistently names photos, review, accepted state, and Excel export as separate workflow concepts. | Global review counts mix operator work and hidden diagnostic/sample records. |
| Wet-lab operator flow | The first screen starts with photo upload and review before canonical change, matching the handwritten cage-card workflow. | Review Queue initially spends too much first-viewport space on role/priority master tables before the actual decision work. |
| Evidence traceability | Focus Review and Export Center expose source evidence, note evidence, and blocker links. | Broken or missing source photos can appear as a dark/broken preview rather than a clear evidence-unavailable state. |
| Review fatigue | Must Review / Quick Check / Trace / Hidden categories exist and are meaningful. | Hidden-default records still inflate topbar and nav counts, making the user feel there is work even when default Focus Review is empty. |
| Export safety | Final export buttons are visibly disabled when Focus Review blockers exist or no accepted rows exist. | Search/CSV download actions appear above the final export gate, so the page needs clearer separation between exploratory downloads and final lab files. |
| Accessibility and responsive layout | Mobile layout is usable; buttons and chips remain readable; no color-only status was obvious in inspected states. | Dense tables still fall back to horizontal scrolling on mobile; acceptable for now, but tiring during pilot review. |
| Privacy/external AI | Health and UI copy show local storage and external inference approval requirements. | "local + AI draft ready" in the topbar can sound operationally safe even before the user has approved an external inference action. |
| Implementation alignment | Current tests and read models already encode low-fatigue review levels and export gating. | Normal Operations Home displays internal IDs directly, conflicting with `AGENTS.md` guidance to hide internal IDs unless debugging. |

## Findings

### P1 - Global Review Counts Include Hidden Diagnostic Work

Evidence:

- After fixture import, the topbar and nav showed `8 open reviews`.
- `/api/ui/focus-review` returned `workload_summary: { must_review: 0, quick_check: 0 }` and no cards.
- `/api/export-preview` returned `open_review_items: 8` and `open_review_attention_counts.hidden_default: 8`.
- The Review Queue default filter showed `No Focus Review items are currently open` plus `Hidden 8`.

Why it matters:

The default user question is "What needs my decision today?" Showing `8 open reviews`
in global chrome while the default review queue is intentionally empty creates false
workload pressure. It also blurs the distinction between operator review items and
fixture/sample diagnostics.

Likely source areas:

- `static/index.html:4325`
- `static/index.html:4445`
- `static/index.html:7692`
- `app/main.py:12211`

Recommendation:

Separate counters into:

- `operator workload`: must-review + quick-check records that should be acted on.
- `open review total`: all open review rows.
- `diagnostic hidden`: hidden-default / fixture / trace diagnostics.

Use the operator workload count in the topbar and primary nav. Keep hidden-default
counts in a secondary diagnostics chip or Settings view.

### P1 - Operations Home Exposes Internal IDs As Primary Copy

Evidence:

Operations Home displayed strings such as:

- `review_id: review_ui_duplicate_mt319`
- `parse_id: parse_ui_review_focus`
- `source_photo_id: photo_ui_review_focus`

Why it matters:

`AGENTS.md` says to keep internal IDs hidden unless needed for debugging. The
Operations Home is a normal operator surface, not a debug inspector. Showing raw
IDs adds cognitive load and makes the product feel less like a lab workflow tool.

Likely source area:

- `static/index.html:4726`

Recommendation:

Show user-facing evidence labels first, for example:

- `Source photo: ui-review-focus-card.jpg`
- `Review type: Duplicate active mouse`
- `Evidence: MT318 R' / MT319 L' / MT320`

Move raw IDs into a collapsed `Debug details` disclosure, available only when useful
for troubleshooting.

### P1 - Review Queue Information Hierarchy Delays The Decision Work

Evidence:

With a seeded must-review blocker, the first visible Review Queue screen showed:

- filter controls,
- Review persona master table,
- Review priority master table,
- then Focus Review cards below the fold.

Why it matters:

The Focus Review page is supposed to answer `What needs my decision today?`.
Configuration masters are useful, but they should not outrank live review work.

Likely source areas:

- `static/index.html:3314`
- `static/index.html:5395`

Recommendation:

Move role/priority/vocabulary masters to Settings or collapse them below the active
review list. The first viewport should show workload summary, active Focus Review
cards, and the selected evidence detail.

### P2 - Export Center Needs Stronger Separation Between Preview Downloads And Final Lab Files

Evidence:

The Export Center first viewport contains `Search & CSV Export` with enabled-looking
`Download Mouse CSV` and `Download Genotyping Worklist` actions before the final
export gate. Lower on the page, final export buttons are correctly disabled with
`Final downloads disabled`.

Why it matters:

The product principle is that Excel files are export/views and final exports must
come after review. If exploratory or worklist downloads remain available, the UI
needs to state whether they are safe preview artifacts, blocked by the same gate,
or separate non-final views.

Likely source area:

- `static/index.html:7245`

Recommendation:

Put a compact export gate summary above all download controls. Label each action as
one of:

- `Preview / non-final`
- `Worklist`
- `Final lab file`

Final lab files should stay disabled until blockers are clear and accepted
source-backed rows exist.

### P2 - Missing Source Photo Preview Needs A Clear Failure State

Evidence:

The seeded Focus Review card used a synthetic photo row without a real stored image.
The detail panel showed a broken/dark source-photo preview area while still offering
`Open source photo`.

Why it matters:

Source photos are raw evidence. A missing image is a review blocker or at least a
clear evidence availability warning, not a cosmetic image failure.

Likely source areas:

- `static/index.html:5988`
- `static/index.html:6283`

Recommendation:

When the source image cannot load, show an explicit state:

- `Source photo unavailable in this local run`
- stored filename/path if safe,
- disable or relabel `Open source photo`,
- keep review blocked from acceptance if the evidence is required.

### P2 - Topbar AI Readiness Copy Can Overstate External Inference Safety

Evidence:

The topbar showed `local + AI draft ready`. `/api/health` also correctly reported
`approval_required: true` and payload-minimization copy.

Why it matters:

The short topbar chip is easy to read as "AI can be used safely now." The actual
rule is narrower: external inference requires explicit approval and minimized
payloads.

Recommendation:

Change the chip to wording such as `AI draft: approval required` or `AI available,
approval required`, and keep the fuller payload-minimization explanation in the
action area.

### P3 - Mobile Layout Is Usable But Table-Heavy Areas Still Require Horizontal Scrolling

Evidence:

At `390 x 844`, the main photo review flow remained readable. The upload batch
table and similar dense tables showed horizontal scrolling.

Why it matters:

This is acceptable for a local desktop-first pilot, but repeated cage-card review
on a small screen will be tiring.

Recommendation:

For pilot-critical tables, use card/stacked rows on small screens. Keep horizontal
scroll for lower-priority audit tables.

### P3 - Hero Illustration Is Pleasant But Should Stay Secondary To Real Evidence

Evidence:

The first screen includes a stylized mouse illustration beside the workflow
explanation. It does not break the flow, but the design guidance says real source
photos should outrank illustrations.

Recommendation:

Keep the illustration small or replace the hero panel with an empty/source-photo
evidence placeholder once real photos exist. Avoid making decorative imagery more
prominent than source-photo evidence.

## Positive Observations

- The main workflow starts with raw cage-card photo upload rather than a dashboard
  or canonical data grid.
- Final export gating is visible and correctly disables final workbook actions
  in the observed blocked states.
- Must Review, Quick Check, Trace, and Hidden classifications exist in both API
  and UI concepts.
- Review detail and Export Center preserve source/evidence language rather than
  presenting OCR or Excel rows as canonical truth.
- Mobile navigation and primary buttons remain readable in the checked viewport.
- No relevant console errors or warning overlays appeared during the browser review.

## Documentation And Implementation Mismatches

| Area | Documentation expectation | Observed implementation |
| --- | --- | --- |
| Internal IDs | Hide internal IDs unless needed for debugging. | Operations Home shows raw `review_id`, `parse_id`, and `source_photo_id` in normal task copy. |
| Review workload | Default UI should emphasize Must Review and Quick Check. | Global counts include hidden-default fixture records, creating apparent workload. |
| Focus Review priority | Decision work should be visible first. | Role and priority master tables appear before active card-level review work. |
| Source photo as evidence | Missing source evidence should be explicit and reviewable. | Broken/missing image can appear as a visual failure rather than a named evidence state. |

## Suggested Verification For Fixes

- `npm test`
- `npm run test:local`
- `python -m pytest tests/test_low_fatigue_ui_contracts.py tests/test_operations_home.py tests/test_review_attention.py -q`
- Browser check: app load, Review Queue default, Review Queue all/filter states, Operations Home, Export Center blocked and ready states, mobile viewport.
