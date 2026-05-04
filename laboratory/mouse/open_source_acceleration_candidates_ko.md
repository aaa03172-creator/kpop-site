# Open Source Acceleration Candidates For Mouse Colony System

## Document Status

Layer classification: design guidance / non-canonical technical reference note.

This note lists open-source libraries and projects that may shorten development time or improve performance for the current mouse colony system. It does not change the PRD, schema, or MVP scope. Canonical behavior still follows `final_mouse_colony_prd.md`, `AGENTS.md`, and adopted project documents.

Research date: 2026-05-04.

## Current Stack Fit

The current project already uses:

- Python/FastAPI for local API workflows.
- SQLite for local state.
- `openpyxl` for `.xlsx` import/export.
- `Pillow` for image handling.
- Static HTML/JS for the local UI.
- Playwright for smoke verification.

The best acceleration strategy is not a large framework replacement. It is to add small, well-scoped tools around the main bottlenecks:

1. photo preprocessing and OCR;
2. strain/genotype/date fuzzy matching;
3. Excel import/export performance;
4. local search and analytics;
5. PDF/QR output for later cage-card views;
6. external reference ingestion.

## Recommended Now

### 1. RapidFuzz

Use for:

- strain alias matching;
- genotype category matching;
- mouse ID or sample ID reconciliation;
- typo-tolerant search in Review Queue.

Why it helps:

- Fast C++ backed fuzzy matching with Python API.
- MIT license.
- Avoids `fuzzywuzzy`/GPL licensing headaches.

Adoption shape:

- Add a `matching.py` service that returns top candidates plus score and explanation.
- Never auto-create canonical strain/genotype categories from fuzzy matches.
- Use thresholds only to route `auto_filled`, `check`, or `needs_review`.

Sources:

- https://github.com/rapidfuzz/RapidFuzz
- https://rapidfuzz.github.io/RapidFuzz/

### 2. SQLite FTS5

Use for:

- fast local search across mouse IDs, raw note lines, source filenames, review issues, raw genotype text, and Excel row evidence.

Why it helps:

- Already inside SQLite in many Python builds.
- Keeps the local-first architecture simple.
- Better than repeated `LIKE '%query%'` scans once source evidence grows.

Adoption shape:

- Add FTS virtual tables for source text, note lines, review items, and accepted mouse summaries.
- Keep FTS as a derived index/cache, not canonical state.
- Rebuild or update the index transactionally after accepted writes.

Source:

- https://www.sqlite.org/fts5.html

### 3. OpenCV Python

Use for:

- card boundary detection;
- perspective correction;
- contrast/threshold cleanup;
- ROI crop generation before OCR;
- image quality scoring.

Why it helps:

- Strongly maintained computer vision toolkit.
- OpenCV 4.5+ is Apache-2.0.
- More practical than writing custom image geometry and preprocessing.

Adoption shape:

- Keep raw photos unchanged.
- Store derived crops as cache or parsed/intermediate artifacts.
- Put crop coordinates and image quality scores on parsed evidence, not canonical state.

Sources:

- https://opencv.org/license/
- https://github.com/opencv/opencv-python

### 4. PaddleOCR

Use for:

- local OCR evaluation, especially Korean/English mixed cards;
- table/layout extraction experiments;
- optional offline OCR path before external LLM parsing.

Why it helps:

- PP-OCRv5 covers 106 languages including Korean.
- PaddleOCR is Apache-2.0.
- PP-StructureV3 adds document/layout/table parsing, which may help genotype sheets or workbook-like images.

Risks:

- Heavier dependency than Tesseract.
- Must be evaluated on actual cage-card photos before adoption.
- OCR output remains parsed/intermediate and reviewable.

Adoption shape:

- Add as an optional extra or separate worker script, not a required core dependency.
- Save OCR output, confidence, and crop/source region.
- Compare against manual transcription fixtures before enabling by default.

Sources:

- https://github.com/PaddlePaddle/PaddleOCR
- https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md
- https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-StructureV3/PP-StructureV3.html

### 5. Tesseract OCR

Use for:

- lightweight offline OCR baseline;
- fast printed text extraction from clearer cards or labels;
- local privacy-preserving fallback.

Why it helps:

- Apache-2.0.
- Mature, offline, and easy to compare against PaddleOCR.

Risks:

- Handwritten cage cards may be weak.
- Windows install/runtime setup can be annoying.

Adoption shape:

- Keep as baseline evaluator, not primary final parser.
- Use per-ROI OCR with tuned page segmentation modes.
- Route all uncertain output to review.

Sources:

- https://github.com/tesseract-ocr/tesseract
- https://github.com/tesseract-ocr/tessdoc

## Recommended Soon

### 6. DuckDB

Use for:

- fast analytics over exports, parsed rows, audit logs, and large CSV/JSONL snapshots;
- ad hoc reporting without changing SQLite canonical state.

Why it helps:

- Embedded, no server.
- MIT license.
- Designed for analytical workloads and high-speed data transfer in-process.

Adoption shape:

- Keep SQLite as canonical transactional DB.
- Use DuckDB as an export/report/query accelerator over CSV/Parquet/JSONL or SQLite snapshots.
- Do not use DuckDB for many-writer canonical OLTP state.

Sources:

- https://duckdb.org/why_duckdb
- https://duckdb.org/faq

### 7. Polars

Use for:

- faster workbook-derived row normalization after conversion to CSV/JSON;
- distribution workbook parsing and multi-sheet reconciliation;
- export preview transformations if row volume grows.

Why it helps:

- Rust-backed DataFrame library.
- Good fit for batch transformations.

Risks:

- Direct Excel support depends on external engines.
- For current small workbooks, `openpyxl` may be enough.

Adoption shape:

- Use only after `openpyxl` parsing becomes slow or messy.
- Treat Polars outputs as parsed/intermediate rows.

Sources:

- https://pola.rs/
- https://docs.pola.rs/

### 8. Pydantic

Use for:

- typed parse result contracts;
- review item payload schemas;
- API request/response validation;
- future CLI JSON contract stability.

Why it helps:

- FastAPI already works naturally with Pydantic.
- Keeps parsed/intermediate vs canonical payloads explicit.

Adoption shape:

- Add schema models around parse results, review actions, correction actions, and export previews.
- Do not move domain writes into Pydantic models; keep service layer responsible.

Sources:

- https://docs.pydantic.dev/
- https://pydantic.dev/docs/validation/latest/concepts/validators/

### 9. `openpyxl` Read-Only / Write-Only Patterns And Possible `xlsxwriter`

Use for:

- improving current `.xlsx` import/export without changing stack.

Why it helps:

- `openpyxl` is already installed.
- Official docs recommend read-only mode for faster low-memory workbook access.
- `xlsxwriter` can be considered if export generation becomes style-heavy and write-only.

Adoption shape:

- First optimize existing `openpyxl` use with read-only mode for imports and write-only mode for generated exports.
- Only add `xlsxwriter` if export formatting becomes a bottleneck.

Source:

- https://openpyxl.pages.heptapod.net/openpyxl/performance.html

## Later / Conditional

### 10. Segno Or `qrcode`

Use for:

- post-MVP QR card/view generation.

Recommendation:

- Prefer `segno` if we need pure-Python QR generation with no dependencies.
- `qrcode` is also stable and familiar, but QR is not MVP-critical.

Adoption shape:

- QR contains only a hidden card/cage-view token or URL.
- QR never makes card `I.D` a stable cage ID.

Sources:

- https://segno.readthedocs.io/en/stable/
- https://pypi.org/project/qrcode/

### 11. zxing-cpp

Use for:

- post-MVP QR/barcode decoding from uploaded photos if the lab ever adopts printed labels.

Why it helps:

- Production/stable Python bindings.
- Apache-2.0 metadata on PyPI.
- Can read/write QR and barcode formats.

Adoption shape:

- Optional post-MVP decoder only.
- Do not make barcode scan required for current workflow.

Source:

- https://pypi.org/project/zxing-cpp/

### 12. WeasyPrint Or Browser-Based PDF Rendering

Use for:

- post-MVP printable cage cards or PDF review packets.

Recommendation:

- WeasyPrint is attractive for HTML/CSS to PDF, but Windows/native dependencies should be tested before committing.
- Because this project already uses Playwright, browser PDF/screenshot rendering may be simpler for local cards if Chromium is available.

Sources:

- https://weasyprint.org/
- https://playwright.dev/python/docs/screenshots

### 13. MouseMine / InterMine Python Client

Use for:

- future MGI gene/allele/strain lookup;
- resolving official symbols and IDs.

Why it helps:

- MouseMine is an InterMine data warehouse for mouse genomic data.
- InterMine exposes scriptable web service APIs and Python clients.

Risks:

- External dependency and network variability.
- Not necessary for the first photo-review-export vertical slice.

Adoption shape:

- Start with manual external IDs and curated strain master.
- Later add a `catalog sync/lookup` command that writes parsed/reference candidates for review.

Sources:

- https://intermine.org/im-docs/docs/introduction/index
- https://pypi.org/project/intermine/

### 14. IMSR / FindMice

Use for:

- post-MVP repository availability and ordering/reference links.

Why it helps:

- IMSR lists where strains/resources are available and their resource states.

Adoption shape:

- Store IMSR/JAX/MMRRC IDs as external reference metadata.
- Do not scrape aggressively.
- Treat availability as external reference projection, not lab canonical state.

Source:

- https://findmice.org/index

## Avoid Or Treat Carefully

### Surya OCR

Why not now:

- Technically strong for OCR/layout/table recognition.
- But code is GPL and model weights have a modified nonstandard license with commercial thresholds.
- This creates licensing complexity that does not fit our current low-risk local tool direction.

Source:

- https://github.com/datalab-to/surya

### pyzbar / ZBar

Why not now:

- QR/barcode is out of MVP.
- ZBar is LGPL, which is manageable, but `zxing-cpp` looks cleaner for a future Python QR/barcode path.

### Large Colony Management Forks

Why not now:

- JCMS, MausDB, RodentSQL, MyVivarium, TopoDB, and Glams are better as workflow/schema references than backend code.
- They do not directly solve our current source-photo-review-Excel loop.

## Highest ROI Next Experiments

### Experiment A: ROI + OCR Baseline

Goal:

- Decide whether local OCR can reduce manual transcription enough to matter.

Tools:

- OpenCV or scikit-image for crop/preprocessing.
- PaddleOCR and Tesseract as competing OCR baselines.

Test set:

- 10 clear cage-card photos.
- 10 blurry/cropped photos.
- 5 mating cards with note lines.
- 5 genotype/result sheet photos.

Success measure:

- Field-level confidence and review routing are useful even when OCR is imperfect.
- OCR never writes canonical state directly.

### Experiment B: Fuzzy Matching For Strain And Genotype Review

Goal:

- Reduce review time for strain/genotype aliases without unsafe auto-accept.

Tools:

- RapidFuzz.
- Existing `My Assigned Strains`, genotype category masters, and raw OCR values.

Success measure:

- Top 3 suggestions are useful.
- Ambiguous values remain reviewable.
- Unknown values do not create masters automatically.

### Experiment C: Search Index

Goal:

- Make global search fast and evidence-aware.

Tools:

- SQLite FTS5.

Success measure:

- Search can find mouse IDs, note-line raw text, genotype results, source filenames, and review issues without broad table scans.

### Experiment D: Workbook Performance

Goal:

- Keep `.xlsx` import/export responsive as historical workbooks accumulate.

Tools:

- `openpyxl` read-only/write-only modes first.
- DuckDB/Polars only if bulk analysis gets slow.

Success measure:

- Workbook import stays non-canonical and traceable.
- Export preview remains fast enough for repeated review.

## Short Recommendation

Start with:

1. RapidFuzz.
2. SQLite FTS5.
3. OpenCV.
4. PaddleOCR as optional evaluation.
5. `openpyxl` performance tuning.

Defer:

1. QR generation/decoding.
2. DuckDB/Polars analytics.
3. MGI/IMSR automated sync.
4. PDF card generation.
5. Pedigree visualization.

Avoid for now:

1. Surya OCR because of GPL/model licensing.
2. Large legacy colony backend forks.
3. Any tool that makes OCR/Excel output canonical without review.
