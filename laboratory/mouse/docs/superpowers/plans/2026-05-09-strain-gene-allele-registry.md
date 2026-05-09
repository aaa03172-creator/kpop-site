# Strain Gene Allele Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal normalized Gene/Allele/StrainAllele layer beside the existing strain registry without breaking evidence-first workflows.

**Architecture:** Keep `strain_registry.gene` and `strain_registry.allele` as legacy/raw display fields, then add canonical structured tables for genes, alleles, and strain-allele links. Manual strain creation will create source-backed normalized records when gene/allele text is provided; list APIs will expose both legacy text fields and normalized relationship arrays.

**Tech Stack:** FastAPI, SQLite, pytest, local verification script.

---

### Task 1: Schema And API Contract

**Files:**
- Modify: `app/db.py`
- Modify: `app/main.py`
- Test: `tests/test_strain_knowledge_graph.py`

- [x] Write a failing pytest that creates a strain with `gene = "Pvalb"` and `allele = "Pvalb-IRES-Cre"` and expects `/api/genes`, `/api/alleles`, and `/api/strains` to expose normalized linked records.
- [x] Add `gene_master`, `allele_master`, and `strain_allele_relationship` tables with source references, timestamps, and uniqueness constraints.
- [x] Add helper functions that upsert gene and allele records by case-insensitive text and link them to the created strain.
- [x] Add `GET /api/genes` and `GET /api/alleles`.
- [x] Extend `GET /api/strains` rows with an `alleles` array while preserving existing top-level `gene` and `allele` fields.
- [x] Run `python -m pytest tests/test_strain_knowledge_graph.py -q`.
- [x] Run `npm run verify`.
- [x] Commit exact files.

---

### Task 2: Legacy Workbook Candidate Surfacing

**Files:**
- Modify: `scripts/parse_legacy_workbooks.py`
- Modify: `app/main.py`
- Modify: `static/index.html`
- Test: `tests/test_legacy_workbook_parser.py`
- Test: `tests/test_legacy_workbook_import_api.py`
- Test: `tests/test_review_attention.py`

- [x] Parse legacy workbook strain/genotype text into `strain_registry_candidates` without inferring gene or allele values.
- [x] Keep candidate rows parsed/intermediate and source-backed; do not write canonical gene, allele, or strain-allele records from import alone.
- [x] Route legacy strain registry candidates to `Strain Curator` review.
- [x] Show candidate count and raw strain/genotype review summary in the Legacy Workbook Import UI.
- [x] Add review check targets: `Strain registry`, `Raw strain/genotype`, `Gene/allele link`, and `Workbook row evidence`.
- [x] Verify candidate display escaping in the browser MVP verifier.

---

### Task 3: Curated Review Apply Flow

**Files:**
- Modify: `app/main.py`
- Modify: `static/index.html`
- Test: `tests/test_strain_knowledge_graph.py`
- Test: `tests/test_legacy_workbook_import_api.py`
- Test: `tests/test_review_attention.py`

- [x] Add a narrow review resolution path that lets a Strain Curator create or link a strain/gene/allele relationship from an open legacy strain registry candidate.
- [x] Require explicit reviewed `strain_name`, `gene_symbol`, and `allele_name` inputs before canonical registry writes.
- [x] Preserve raw legacy workbook candidate JSON and source row evidence on the review item and source record.
- [x] Preserve before/after values in `action_log`.
- [x] Keep unresolved or partially filled candidates open rather than writing incomplete canonical records.
- [ ] Run `python -m pytest tests/test_strain_knowledge_graph.py tests/test_legacy_workbook_import_api.py tests/test_review_attention.py -q`.
- [ ] Run `npm test`, `npm run test:local`, and `npm run test:acceptance`.
