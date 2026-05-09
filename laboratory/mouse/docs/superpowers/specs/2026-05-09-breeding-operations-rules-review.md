# Breeding Operations Rules Review

Layer classification: non-canonical implementation planning note.

## Source Workbooks Reviewed

- `20260504 ApoM TgTg animal sheet_updated.xlsx`: export/view source for mating cage blocks, litter rows, and handwritten operational notes.
- `20260504 ApoM TgTg separation status workbook`: export/view source for separated or maintenance cage summaries.
- `20260407 assignment distribution workbook`: raw assignment reference for responsible people, strain text, and expected cage counts.

These workbooks can suggest configurable rules, but they must not silently overwrite photo-backed records or become canonical state by themselves.

## Rule Classification

### General Lab Workflow Rules

These appear broadly useful across strains, but should still be stored as configurable policy values rather than hard-coded branches.

- A card or workbook block with both male and female parent rows plus a mating date is a mating cage candidate.
- A card or workbook block with only male or only female animals, count summaries, and DOB groups is a separated or maintenance cage candidate.
- In animal sheet style workbooks, a row with a new `Cage No.` starts a mating cage block.
- Within a mating block, sex-labeled parent rows represent parent mice.
- Within a mating block, `F1`, `F2`, `F3`, etc. represent litter events.
- Pup count strings such as `7p`, `9p`, and `10p` should parse as litter or current-pup counts.
- Litter statuses such as `separated` and `dead` should create breeding event candidates, not individual mouse rows.
- If a mating block has a `Pubs` value such as `26.04.20 9p`, it is an open or current litter candidate until linked to a separated cage/card.

### Configurable Breeding Thresholds

The reviewed animal sheet notes suggest these defaults. They should be editable and visible as assumptions.

| Rule key | Suggested default | Review behavior |
| --- | ---: | --- |
| `mating_parent_ratio` | 1 male : 2 female | Warn when a new mating setup differs, but do not block. |
| `mating_parent_age_min_days` | about 60 days | Flag too-young parent candidates. |
| `mating_parent_age_preferred_max_days` | about 120 days | Prefer younger candidates when replacing parents. |
| `no_birth_review_after_days` | 60 days | Review mating cages with no litter/current-pup evidence after this window. |
| `parent_replacement_review_after_days` | 365 days | Review parents older than one year. |
| `litter_separation_due_after_days` | 30 days | Mark litter separation due soon. |
| `litter_separation_overdue_after_days` | 45 days | Mark litter separation overdue. |
| `litter_separation_high_overdue_after_days` | 60 days | High-priority review. |
| `separation_batch_max_dob_span_days` | 14 days | Group nearby DOBs but review wider spans. |

These thresholds should produce recommendations such as `separation_due`, `separation_overdue`, `no_birth_review`, and `replace_parents_review`. They should not automatically sacrifice, replace, or close records.

### Strain-Specific Candidate Rules

These must not be promoted to global rules.

- Notes such as "all pups are Tg" are candidate strain-specific configuration only. They are not safe as a general genotype rule because genotype categories and inheritance expectations change by strain or cross.
- ApoM-related raw strings from the distribution workbook, such as `ApoMtg/+`, `ApoMtg/tg`, `ApoM+/-`, and compound crosses containing ApoM, are strain alias candidates. They should go through assignment-scope review before being accepted.
- Example notes about maintaining a fixed number of mating cages for one strain should become a configurable strain or project target, not a universal colony rule.

## Workbook-Specific Extraction Rules

### Animal Sheet

Extract as parsed/intermediate breeding evidence:

- cage number,
- strain,
- parent sex,
- parent mouse ID and ear-label text,
- parent genotype text,
- parent DOB raw text,
- mating date,
- litter label,
- pup count,
- litter DOB raw text,
- litter status,
- current `Pubs` value,
- right-side operational note text.

Review triggers:

- litter DOB earlier than mating date;
- first litter too soon after mating unless the mating date may be a late-entered or inherited value;
- litter DOBs within the same cage that appear out of order;
- multiple litter dates within a very short window that may indicate same birth batch or transcription ambiguity;
- parent rows missing one male or at least one female;
- current `Pubs` value that is older than separation threshold and still not linked to a separated cage.

### Separation Status Workbook

Extract as parsed/intermediate maintenance evidence:

- strain raw text,
- genotype or cross label,
- sex and count from values such as `male 8p` or `female 8p`,
- DOB raw text or DOB range,
- genotype count columns,
- genotyping workflow notes such as "genotyping not started" or "genotyping in progress",
- sampling or age-cleanup notes.

Review triggers:

- sex/count total does not reconcile with genotype count columns when count columns are populated;
- DOB range wider than the configured separation batch maximum;
- old maintenance groups past cleanup review age;
- genotyping status present without linked individual mouse/sample records.

### Distribution Workbook

Extract as assignment-scope candidates, not colony state:

- institution or section block,
- responsible person, carrying merged cells downward,
- raw strain/mating type text,
- expected cage count,
- expected mating cage count or subtotal formulas.

Review triggers:

- assigned strain appears in distribution workbook but not in `My Assigned Strains`;
- current photo/workbook records contain a strain not present in the active assignment scope;
- expected cage counts differ greatly from accepted current records.

## Recommended Product Behavior

1. Preserve each workbook as raw source.
2. Parse rows into non-canonical evidence records with sheet name, row number, and cell coordinates.
3. Present extracted rules as reviewable configuration candidates.
4. Let the user accept, edit, or ignore rule candidates.
5. Apply accepted rules only as visible assumptions in parsing, review, dashboard next-actions, and export previews.

## Near-Term Implementation Priority

1. Add configurable breeding operation thresholds.
2. Use litter DOB/current-pup dates to show separation due and overdue states.
3. Use mating date plus no-birth window to show no-birth review.
4. Use parent DOB/age to show replacement review.
5. Keep genotype inheritance notes as strain-specific candidate settings only, not global logic.
