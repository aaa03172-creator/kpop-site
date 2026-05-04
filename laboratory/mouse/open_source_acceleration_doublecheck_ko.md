# Open Source Acceleration Double-Check Note

## Document Status

Layer classification: design guidance / non-canonical technical reference note.

This is the double-checked version of `open_source_acceleration_candidates_ko.md`. It summarizes which open-source tools are most likely to reduce development time or improve local performance for this project, after re-checking official documentation and licensing signals on 2026-05-04.

This document does not change canonical product scope. The MVP remains:

```text
source photo / workbook evidence -> parsed result -> review -> accepted event/state -> Excel export/view
```

## Double-Check Criteria

Each candidate was checked against five questions:

1. Does it directly help our photo-grounded review/export loop?
2. Is the license low-risk for a local Python/FastAPI tool?
3. Can it be added without replacing the existing architecture?
4. Does it preserve raw evidence and review boundaries?
5. Is it useful before QR, pedigree visualization, or ResearchGraph integration?

## Final Shortlist

| Priority | Candidate | Decision | Why |
| --- | --- | --- | --- |
| P0 | RapidFuzz | adopt first | Small dependency, MIT, directly improves strain/genotype/sample matching. |
| P0 | SQLite FTS5 | adopt first | Uses existing SQLite direction; improves evidence/review search without new service. |
| P1 | OpenCV Python | experiment next | Best practical tool for card crop, deskew, threshold, ROI extraction. |
| P1 | openpyxl optimized modes | adopt in-place | Already installed; read-only/write-only modes can reduce memory/time. |
| P1 | PaddleOCR | evaluate, optional | Strong multilingual OCR including Korean; heavier dependency, must be proven on our photos. |
| P2 | DuckDB | defer | Good for local analytics/export analysis, but not needed for canonical OLTP state. |
| P2 | Pydantic schemas | adopt gradually | Useful for parse/review/API contracts, but not a performance lever by itself. |
| P2 | Segno/qrcode | defer | QR generation is post-MVP. |
| P2 | zxing-cpp | defer | QR/barcode decoding is post-MVP. |
| Avoid now | Surya OCR | avoid for product core | Strong OCR/layout project, but GPL code plus custom model license is too much friction. |

## P0: Adopt First

### RapidFuzz

Use it for:

- matching raw OCR strain text to `My Assigned Strains`;
- suggesting genotype category matches;
- linking genotype sample IDs to mouse IDs when exact matching is not enough;
- typo-tolerant review/search helpers.

Why it should come first:

- It is small and focused.
- It is MIT licensed.
- It avoids `fuzzywuzzy`/GPL concerns.
- It improves review speed without pretending OCR is clean.

Implementation guardrails:

- Fuzzy match output is a suggestion, not canonical truth.
- Store score, matched candidate, raw value, and chosen threshold.
- Unknown values create review items; they do not create strain/genotype masters automatically.

Official sources:

- https://github.com/rapidfuzz/RapidFuzz
- https://rapidfuzz.github.io/RapidFuzz/

### SQLite FTS5

Use it for:

- global search across mouse display IDs, note lines, review issue text, raw genotype text, source filenames, Excel row evidence, and action/correction logs.

Why it should come first:

- It fits our current SQLite local-first architecture.
- It avoids adding a search server.
- It replaces broad `LIKE '%query%'` scans as evidence grows.

Implementation guardrails:

- FTS tables are derived indexes/cache.
- Canonical state remains in normal tables.
- FTS updates should happen transactionally with accepted writes or be rebuilt safely.

Official source:

- https://www.sqlite.org/fts5.html

## P1: Experiment Next

### OpenCV Python

Use it for:

- detecting the cage card area inside a photo;
- cropping fixed ROI regions;
- deskew/perspective correction;
- contrast, threshold, denoise preprocessing;
- image quality score before OCR.

Why it is useful:

- It directly supports the biggest practical blocker: messy handwritten card photos.
- OpenCV 4.5+ is Apache-2.0.

Implementation guardrails:

- Never modify or replace the raw photo.
- Store crops and preprocessing outputs as cache or parsed/intermediate artifacts.
- Keep coordinates, source photo ID, and confidence on extraction evidence.

Official sources:

- https://opencv.org/license/
- https://github.com/opencv/opencv-python

### openpyxl Optimized Modes

Use it for:

- faster predecessor workbook parsing;
- lower memory `.xlsx` import;
- safer generated workbook writing.

Why it is useful:

- `openpyxl` is already in `requirements.txt`.
- Read-only and write-only modes can improve memory/time without adding a new library.

Implementation guardrails:

- Existing Excel files are raw source or export/view, never canonical DB.
- Parsed workbook rows remain review candidates.
- Preserve filename, sheet name, cell/row references.

Official source:

- https://openpyxl.readthedocs.io/en/stable/optimized.html

### PaddleOCR

Use it for:

- optional local OCR evaluation;
- Korean/English mixed card text;
- genotype/result sheet OCR;
- possible layout/table extraction via PP-StructureV3.

Why it is promising:

- PaddleOCR is Apache-2.0.
- PP-OCRv5 supports 106 languages including Korean.
- PP-StructureV3 is aimed at document/layout/table parsing.

Risks:

- Heavy dependency.
- Real handwritten cage-card accuracy is unknown.
- It may be slower or harder to install than the rest of the stack.

Implementation guardrails:

- Add as optional extra or isolated script first.
- Benchmark against actual cage-card photos.
- Save OCR text/confidence/ROI source region as parsed evidence only.
- Do not make OCR required for MVP.

Official sources:

- https://github.com/PaddlePaddle/PaddleOCR
- https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md
- https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-StructureV3/PP-StructureV3.html

## P2: Defer Until There Is Pressure

### DuckDB

Use later for:

- larger export analytics;
- ad hoc summaries over CSV/JSONL/Parquet snapshots;
- fast read-heavy reporting.

Why defer:

- Our canonical state is transactional and SQLite-shaped.
- DuckDB is excellent for embedded analytics, but not a replacement for the current OLTP database.

Official sources:

- https://duckdb.org/why_duckdb
- https://duckdb.org/faq

### Pydantic

Use gradually for:

- parse result schemas;
- review action payloads;
- API request/response models;
- stable CLI JSON contracts.

Why defer as a separate project:

- Useful for correctness and maintainability.
- Not the main performance bottleneck.
- Best introduced when touching API/service boundaries anyway.

Official source:

- https://docs.pydantic.dev/

### Segno Or qrcode

Use later for:

- QR generation for read-only card/cage views.

Why defer:

- PRD explicitly keeps QR/barcode out of MVP.
- If added later, QR should contain a hidden token/deep link, not the cage card `I.D` field.

Official sources:

- https://segno.readthedocs.io/en/stable/
- https://pypi.org/project/qrcode/

### zxing-cpp

Use later for:

- decoding QR/barcodes from uploaded photos if the lab adopts labels.

Why defer:

- QR/barcode is not part of the current workflow.
- The PyPI package is production/stable and recently released, but no need to add it now.

Official source:

- https://pypi.org/project/zxing-cpp/

## Avoid For Now

### Surya OCR

Why avoid now:

- It has strong OCR/layout/table capabilities.
- However, its code is GPL and model weights use a modified AI Pubs Open Rail-M license with usage conditions.
- That is too much licensing friction for our core product path.

Official source:

- https://github.com/datalab-to/surya

### Large Mouse Colony Backend Forks

Avoid direct backend reuse from:

- JCMS;
- MausDB;
- RodentSQL;
- MyVivarium;
- TopoDB;
- Glams.

Why:

- They are useful as workflow references.
- They do not directly solve our current photo-review-Excel loop.
- Several have legacy stacks or GPL/LGPL constraints.

## Recommended Implementation Order

### Step 1: RapidFuzz Matching Service

Add:

```text
matching.py
- match_assigned_strain(raw_text, assigned_strains)
- match_genotype_category(raw_text, allowed_categories)
- match_mouse_or_sample_id(raw_text, candidate_ids)
```

Outputs should include:

```text
raw_value
candidate_value
score
decision: auto_filled / check / needs_review
reason
```

Acceptance checks:

- Unknown strain does not create a new strain.
- Ambiguous top scores go to review.
- Matched value keeps source evidence and raw text.

### Step 2: SQLite FTS5 Evidence Search

Add derived search indexes for:

- `photo_log.original_filename`;
- `card_note_item_log.raw_line_text`;
- `review_queue.issue`, `current_value`, `suggested_value`, `review_reason`;
- accepted mouse summary fields;
- genotyping raw/normalized result fields.

Acceptance checks:

- FTS index is rebuildable.
- Search result shows boundary/source layer.
- Search failure does not block canonical writes.

### Step 3: OpenCV ROI Preprocessing Spike

Add a small script first:

```text
scripts/extract_card_roi.py
```

Inputs:

- source photo path;
- ROI preset from `config/roi_presets.json`.

Outputs:

- card crop;
- field crops;
- image quality metrics;
- JSON metadata with normalized coordinates.

Acceptance checks:

- raw photo stays unchanged.
- crop metadata is linked to photo ID.
- poor photos still create reviewable evidence.

### Step 4: openpyxl Import/Export Tuning

Review existing workbook parsers/exporters and apply:

- read-only mode for imports;
- write-only mode for large generated exports where practical;
- explicit cell coordinate preservation for parsed source rows.

Acceptance checks:

- parsed Excel rows remain non-canonical.
- export output shape remains familiar.
- blocked reviews still block final export when required.

### Step 5: PaddleOCR Evaluation Only

Add only after Step 3:

```text
scripts/evaluate_ocr_candidates.py
```

Compare:

- manual transcription fixture;
- PaddleOCR output;
- Tesseract output if installed;
- optional OpenAI Parse Assist output where user-approved.

Acceptance checks:

- field-level accuracy is measured.
- OCR outputs are saved as parsed/intermediate evidence.
- no OCR path writes canonical mouse state.

## Final Recommendation

For the next development cycle, do not add a broad stack. Add:

```text
RapidFuzz + SQLite FTS5 + OpenCV ROI spike + openpyxl optimized modes
```

Then evaluate PaddleOCR on real photos. This gives the best chance of reducing manual review time while preserving the core product promise:

```text
raw evidence stays preserved, uncertainty stays reviewable, accepted state stays traceable.
```
