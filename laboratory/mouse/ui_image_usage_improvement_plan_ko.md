# UI Image Usage Improvement Plan

## Layer Classification

- Artifact type: review item / implementation plan
- Canonical status: non-canonical
- Purpose: generated illustration assets are currently overused in the UI. This document defines what to keep, remove, simplify, and verify without changing source evidence, parsed records, or canonical mouse state.

## Decision Standard

The UI should support the MVP workflow first:

- preserve raw cage-card photos as evidence
- review uncertain OCR and imported workbook values
- correct records with traceability
- inspect source-backed mouse, cage, mating, litter, genotype, note, and export views
- avoid visual noise that slows scanning or pressures users to accept inferred data

Images should be used only when they improve orientation or reduce cognitive load. Repeated operational tables should prioritize text, chips, confidence, source references, and review actions.

## Current Findings

### What Works

- Photo Review hero has a useful visual overview of photo evidence, review, and export flow.
- Evidence Comparison visual board helps explain the photo-to-review-to-workbook relationship.
- Export Readiness visual board can help explain why final exports are gated.
- Mouse Detail can reasonably use one representative mouse or cage illustration because it is a focused detail page.
- Empty or placeholder states can use illustrations if they do not compete with source evidence.

### What Is Too Much

- Review Queue uses a generated image on every review card. This makes the list feel decorative and slows issue scanning.
- Records view uses generated images heavily inside rows. A browser check previously counted about 310 visible generated images in that view.
- Cage, breeding, genotyping, and note rows use large PNG illustrations at tiny sizes. This does not improve comprehension enough to justify the weight or visual noise.
- Current PNG files are about 1 MB each and 1254px square. Many are displayed at 28px to 58px, which is inefficient.
- SVG and PNG variants both remain in `static/assets/`; this is acceptable temporarily but should be cleaned once the final direction is chosen.

## Keep, Reduce, Remove

### Keep

Keep generated PNG illustrations in these high-level orientation areas:

- Photo Review hero
- Evidence Comparison visual board
- Export Readiness visual board, but smaller and less dominant
- Mouse Detail top profile or empty state
- Optional empty states for missing mouse/cage/event data

### Reduce

Reduce illustration use in these areas:

- Mouse Detail pedigree: use small labels or simple line icons rather than repeating the same mouse illustration for father, mother, and subject.
- Cage and breeding overview cards: keep one representative visual per section, not one per row.
- Genotyping overview: keep one overview flow if it helps, but row-level generated images should be removed.
- Note Evidence overview: keep one source evidence visual, remove per-row images.

### Remove

Remove generated PNGs from repeated scanning surfaces:

- Review Queue card leading image
- Cage table rows
- Mating table rows
- Litter table rows
- Genotyping table rows
- Note Evidence table rows
- Genotyping metric cards if they are repeated counts rather than workflow steps

Use status chips, compact labels, severity color, and short text instead.

## Proposed UI Rules

1. Use generated illustrations only in orientation, summary, detail, and empty-state surfaces.
2. Do not use generated illustrations inside dense tables or long repeated lists.
3. Review Queue cards should lead with issue, severity, assigned role, source, confidence, and action, not decoration.
4. Repeated table rows should use plain text, chips, small CSS status dots, or existing lightweight SVG icons.
5. Raw photo evidence must remain visually primary in Photo Review. Decorative illustrations must never compete with the actual uploaded cage-card photo.
6. Asset size should match usage:
   - representative illustration: max 512px source dimension
   - small icon: prefer SVG or max 128px transparent PNG
   - target file size: under 250 KB for representative PNGs where practical

## Implementation Plan

### Phase 1: Remove Row-Level Noise

Goal: improve scanning without changing workflows or APIs.

- Replace Review Queue `review-card-visual` image block with a compact text badge.
- Remove generated image tags from `cage-cell`, `breeding-cell`, `genotyping-row-cell`, `note-source-cell`, and `note-review-cell`.
- Keep the existing labels and status chips so no information is lost.
- Remove or simplify CSS rules that only support row-level image cells.

Expected result:

- Review Queue becomes faster to scan.
- Records view generated image count drops sharply.
- MVP workflows remain unchanged.

### Phase 2: Keep Only Section-Level Illustrations

Goal: retain helpful orientation without decorative repetition.

- Keep Photo Review hero visual, but check image scale and spacing.
- Keep Evidence Comparison and Export Readiness boards, but reduce their visual weight if they dominate the page.
- Keep Mouse Detail profile image and one cage or timeline image only.
- Convert pedigree repeated mouse images into simple text nodes or compact relationship chips.

Expected result:

- The UI still has visual breathing room.
- Dense operational data stays readable.

### Phase 3: Asset Optimization

Goal: reduce file weight and align style.

- Resize kept PNG assets to 512px or smaller.
- Compress PNGs or convert to WebP if the app accepts it.
- Remove unused SVG or PNG variants after final references are confirmed.
- If regenerating assets, use a flatter UI style:
  - clean vector UI illustration
  - transparent background
  - minimal lab icon
  - no text, no watermark, no logo

Expected result:

- Faster load.
- More coherent product tone.
- Less stock-render feeling.

### Phase 4: Verification

Run:

- `npm test`
- `npm run test:local`

Browser checks:

- Photo Review desktop and mobile
- Review Queue desktop
- Records desktop and mobile
- Mouse Detail desktop

Acceptance checks:

- no broken generated image references
- no horizontal overflow
- raw cage-card photo remains visually primary in Photo Review
- Review Queue issue text and action buttons remain immediately visible
- Records tables can be scanned without repeated decorative images
- generated image count in Records view is no longer excessive

## Current Code Touchpoints To Review

These are the main areas identified in `static/index.html`:

- `hero-illustration`: keep, but tune scale if needed
- `visual-board`: keep for high-level flows
- `review-card-visual`: remove or replace with badge
- `mini-visual-card`: keep only for detail or empty states
- `cage-cell`: remove row image
- `breeding-cell`: remove row image
- `genotyping-row-cell`: remove row image
- `note-source-cell`: remove row image
- `note-review-cell`: remove row image
- `reviewVisual(item)`: keep classification logic, return badge text/tone instead of image asset
- `genotypingIcon(value)`: remove if no longer used outside section-level flow

## Recommended First Patch

The first implementation patch should be intentionally small:

1. Remove generated images from Review Queue cards.
2. Remove generated images from repeated Records rows.
3. Leave hero, visual boards, and detail summary illustrations untouched.
4. Re-run automated and browser checks.

This gives the largest readability improvement while minimizing risk to the MVP workflow.

## Implementation Status

- Phase 1 row-level image cleanup: implemented.
- Review Queue card illustrations were replaced by compact classification badges.
- Repeated cage, breeding, genotyping, and note-evidence row illustrations were removed.
- Section-level and detail-level illustrations remain in place.
- Browser check after the patch showed Review Queue generated images reduced to 0 and Records generated images reduced to 10 visible section/detail images.
- Phase 2 detail cleanup: implemented for Mouse Detail pedigree; repeated mouse illustrations were replaced with text relationship nodes.
- Export Readiness visual board was reduced in height and image scale so it reads as supporting context rather than a dominant panel.
- Phase 3 asset optimization: implemented for current PNG assets; kept generated PNGs are resized/compressed and each representative PNG is now under 250 KB.
- Unused SVG backup assets were removed after confirming the UI no longer references them.
