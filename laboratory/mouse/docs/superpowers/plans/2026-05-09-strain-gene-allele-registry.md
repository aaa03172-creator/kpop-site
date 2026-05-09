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
- [ ] Commit exact files.
