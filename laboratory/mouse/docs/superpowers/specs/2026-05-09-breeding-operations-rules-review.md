# Breeding Operations Rules Review

Layer classification: non-canonical implementation planning note.

## Source Workbooks Reviewed

- `20260504 ApoM TgTg animal sheet_updated.xlsx`: export/view source for mating cage blocks, litter rows, and handwritten operational notes.
- `20260504 ApoM TgTg separation status workbook`: export/view source for separated or maintenance cage summaries.
- `20260407 assignment distribution workbook`: raw assignment reference for responsible people, strain text, and expected cage counts.

These workbooks can suggest configurable rules, but they must not silently overwrite photo-backed records or become canonical state by themselves.

## Rule Classification

### Rule Strength Levels

Use rule strength explicitly so extracted patterns do not accidentally become biological truth or irreversible operations.

| Strength | Meaning | Allowed behavior |
| --- | --- | --- |
| Source structure | Workbook/photo layout pattern that helps parse rows or note lines. | Use for extraction with source coordinates and confidence. |
| Evidence candidate | Pattern that suggests cage type, litter event, parent row, genotype assumption, or assignment scope. | Store as parsed/intermediate evidence and show why it was inferred. |
| Review trigger | Threshold or conflict that asks the user to check a record. | Create review items or next-action suggestions only. |
| Adopted policy | User-approved strain, project, or facility setting. | Apply visibly to review, filtering, and export readiness. |
| Prohibited automation | Rule that would sacrifice, replace, close, delete, or overwrite records without review. | Never execute automatically. |

### General Lab Workflow Rules

These appear broadly useful across strains, but should still be stored as configurable policy values rather than hard-coded branches. Most of them are evidence candidates, not deterministic classifications.

- A card or workbook block with both male and female parent rows plus a mating date is a mating cage candidate.
- A card or workbook block with only male or only female animals, count summaries, and DOB groups is a separated or maintenance cage candidate.
- In animal sheet style workbooks, a row with a new `Cage No.` starts a mating cage block.
- Within a mating block, sex-labeled parent rows represent parent mice.
- Within a mating block, `F1`, `F2`, `F3`, etc. represent litter events.
- Pup count strings such as `7p`, `9p`, and `10p` should parse as litter or current-pup counts.
- Litter statuses such as `separated` and `dead` should create breeding event candidates, not individual mouse rows.
- If a mating block has a `Pubs` value such as `26.04.20 9p`, it is an open or current litter candidate until linked to a separated cage/card.

### Conflict And Overfitting Review

The same visible pattern can mean different things depending on source type, recency, and accepted strain policy. The parser should keep these as reviewable signals instead of forcing a single answer.

| Rule area | Possible conflict | Safer interpretation |
| --- | --- | --- |
| Mixed male/female cage means mating | A maintenance or holding cage may temporarily contain both sexes in a source note, or a card may carry stale parent text. | Treat as mating candidate only when supported by mating date, parent-style rows, or active litter evidence. |
| Single-sex cage means maintenance | A mating workflow can temporarily split one sex, and separated pups are also single-sex. | Classify as separated/maintenance candidate with lower confidence unless DOB/count/genotyping evidence supports it. |
| `F1`, `F2`, `F3` mean litter rows | These tokens can also be filial generation notation outside the animal-sheet mating block context. | Interpret as litter labels only inside an identified mating block or source layout that uses them that way. |
| `Pubs` value means active litter | The value may be historical, stale, or already resolved by a separated/dead status elsewhere. | Treat as current litter candidate only when no newer linked separation/death evidence exists. |
| `separated` or `dead` means litter event status | Similar words can appear in free-text notes about individual mice or cleanup. | Store both the raw note and normalized event candidate, with source context and review when ambiguous. |
| Missing litter evidence means no birth | OCR/import can miss handwritten notes or a source may be out of date. | Trigger no-birth review only when source recency and absence of current-pup/litter evidence are both clear. |
| Parent age threshold means replace | Older parents may still be productive, and colony goals may justify keeping them. | Create replacement review only; reduce severity when recent litter evidence exists. |
| Separation age threshold means overdue | Facility protocol, strain growth, genotyping timing, and cage availability can vary. | Use editable due/overdue bands and show the assumed policy used. |
| Distribution expected cage counts are target truth | Distribution sheets describe assignment scope and planning counts, not observed colony state. | Use as assignment-scope comparison, not as proof that records are missing or extra. |

### Configurable Breeding Thresholds

The reviewed animal sheet notes suggest these candidate values. They should be editable, visible as assumptions, and scoped by strain/project/facility when adopted.

| Rule key | Candidate value | Review behavior |
| --- | ---: | --- |
| `mating_parent_ratio` | 1 male : 2 female | Warn when a new mating setup differs from the adopted policy, but allow single-pair and other approved ratios. |
| `mating_parent_age_min_days` | about 60 days | Flag too-young parent candidates; do not infer invalidity from age alone. |
| `mating_parent_age_preferred_max_days` | about 120 days | Prefer younger candidates when recommending replacements, if an adopted policy asks for this. |
| `no_birth_review_after_days` | 60 days | Review mating cages with no linked litter/current-pup evidence after this window and with recent enough source coverage. |
| `parent_replacement_review_after_days` | 365 days | Review parents older than one year; lower urgency if recent litter evidence exists. |
| `litter_separation_due_after_days` | about 30 days | Mark litter separation due soon using the adopted facility/strain policy. |
| `litter_separation_overdue_after_days` | about 45 days | Mark separation overdue, but keep it as a review item. |
| `litter_separation_high_overdue_after_days` | about 60 days | High-priority review, not automatic cleanup. |
| `separation_batch_max_dob_span_days` | about 14 days | Group nearby DOBs but review wider spans; do not split source groups without user confirmation. |

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
6. Resolve conflicts by evidence strength and source recency, then send unresolved cases to review instead of choosing silently.

## Near-Term Implementation Priority

1. Add configurable breeding operation thresholds.
2. Use litter DOB/current-pup dates to show separation due and overdue states.
3. Use mating date plus no-birth window to show no-birth review.
4. Use parent DOB/age to show replacement review.
5. Keep genotype inheritance notes as strain-specific candidate settings only, not global logic.
6. Add conflict metadata to review items: source field, conflicting field, assumed rule, confidence, and suggested action.
