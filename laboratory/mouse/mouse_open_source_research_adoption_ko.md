# Mouse Colony Open Source Research Adoption Note

## Document Status

Layer classification: design guidance / non-canonical reference adoption note.

This document adapts the external mouse colony management research reports in:

- `C:/Users/User/Downloads/deep-research-report.md`
- `C:/Users/User/Downloads/마우스 관리 시스템 개발 조사 보고.docx`

It does not define canonical product behavior or final schema. Canonical product behavior should continue to follow `final_mouse_colony_prd.md`, `AGENTS.md`, and later adopted project documents.

## Our Current Product Context

우리 제품은 지금 당장 범용 vivarium SaaS나 QR-first colony database가 아니다. 현재 방향은 다음에 더 가깝다.

1. 사용자는 기존처럼 animal room에서 handwritten cage card를 작성한다.
2. 사용자는 나중에 cage card photo, genotype sheet, Excel workbook을 업로드한다.
3. 시스템은 원본 사진과 workbook row를 raw evidence로 보존한다.
4. OCR/ROI/Excel parsing 결과는 parsed or intermediate result로 둔다.
5. 확실한 값만 정책에 따라 auto-fill하고, 불확실하거나 충돌하는 값은 review item으로 보낸다.
6. 승인된 값은 mouse, card snapshot, mating, litter, genotype, event state로 승격한다.
7. 기존 lab Excel format은 canonical source가 아니라 export/view로 생성한다.

따라서 외부 오픈소스의 좋은 부분도 이 흐름에 맞을 때만 가져온다.

## Adoption Summary

| Source | 가져올 것 | 보류할 것 | 피할 것 |
| --- | --- | --- | --- |
| TopoDB | cage/mouse/experiment 연결, audit/versioning 사고방식, CSV/PDF export 참고 | Rails UI/stack 직접 사용 | genotype/strain free-text 중심 모델 반복 |
| MyVivarium | QR/cage card/task/reminder/workflow 개념, cage card read model 아이디어 | QR/mobile mutation은 post-MVP | MVP를 QR-first로 바꾸는 것 |
| JCMS | mature husbandry workflow, normalized relational model, controlled vocabulary 사고방식 | legacy schema 상세 분석 | Access/JBoss/ActiveX 기반 fork |
| MausDB | 대형 facility phenotyping/worklist 관점 | phenotype scheduling post-MVP | MVP에 대형 시설 기능 끌어오기 |
| RodentSQL | mouse ID 중심의 단순 workflow, cage card/barcode 개념 | 논문 수준 workflow 참고 | 공개 repo를 실제 backend source로 보는 것 |
| Glams | mouse view/cage view 이원화, drag/move UX 아이디어 | UI reference only | Python 2.7/MySQL 코드 재사용 |
| mousecolonytools | Sanger genotyping, pedigree helper 사고방식 | 별도 companion tool 검토 | GPL R package를 core backend에 embed |
| Open Pedigree | 후속 pedigree viewer/export target | post-MVP adapter | MVP에서 visual pedigree editor 직접 구현 |
| nprcgenekeepr | pedigree validation, kinship/inbreeding QC 사고방식 | algorithm reference | lab workflow보다 genetic optimization을 먼저 앞세우기 |
| MGI/IMSR | gene/allele/strain canonical reference, external IDs, periodic sync | full catalog sync 자동화는 staged rollout | local strain/genotype names를 hard-code |

## Corrected Interpretation Of The Reports

두 보고서의 큰 결론, 즉 "기존 backend를 fork하지 말고 Python 기반 greenfield로 가자"는 우리 상황에도 맞다. 다만 DOCX 보고서는 몇 가지를 현재 PRD보다 앞서간다.

- QR/mobile workflow는 좋은 참고지만, 우리 MVP의 primary workflow가 아니다.
- PaperPipe/ResearchGraph 연동은 장기 확장 지점이지, MouseDB 초기 제품 목적이 아니다.
- MouseDB는 먼저 photo-grounded colony state-change tracker가 되어야 한다.
- Excel은 기존 lab handoff format으로 계속 중요하지만 source of truth는 아니다.
- Cage card `I.D` field는 stable cage ID가 아니므로, QR/cage UUID 표현은 user-facing cage identity로 쓰면 안 된다.

정리하면, 외부 조사는 "무엇을 만들 수 있는가"의 후보군이고, 현재 PRD는 "지금 무엇을 먼저 만들어야 하는가"의 기준이다.

## MVP Adoption Plan

### 1. Evidence-First Intake

Adopt from:

- our PRD and reference adoption notes;
- TopoDB/MyVivarium attachment and card workflows;
- JCMS audit mindset.

Implementation direction:

- `photo_log`, uploaded workbook, genotype sheet image는 raw source다.
- OCR text, ROI crops, parsed note lines, parsed Excel rows는 parsed/intermediate다.
- 모든 parsed field는 raw value, normalized candidate, confidence, source anchor를 가진다.
- parsing이 실패해도 원본 photo/workbook은 보존한다.
- external OCR/LLM을 사용할 때는 필요한 photo와 최소 context만 보낸다.

### 2. Card Snapshot, Not Stable Cage Truth

Adopt from:

- MyVivarium cage card read model;
- TopoDB cage-centric workflow;
- our PRD's card snapshot clarification.

Implementation direction:

- `card_snapshot`은 특정 photo 또는 Excel row에서 관찰된 cage/card state다.
- `card_id_raw`는 카드에 적힌 `I.D` 원문이다.
- `record_id` 또는 `card_snapshot_id`는 hidden internal key다.
- visible workflow는 photo, strain, DOB, sex/count, mouse IDs, note lines 중심으로 유지한다.
- QR token이 필요해지는 시점에도 user-facing stable cage ID처럼 노출하지 않는다.

### 3. Mouse ID And Note Line Continuity

Adopt from:

- RodentSQL's mouse-ID-centered workflow;
- our PRD's "mouse IDs and note-line evidence as continuity anchors";
- Glams' conceptual distinction between mouse view and cage view.

Implementation direction:

- note lines are primary evidence, not loose comments.
- note items should preserve raw text, strike-through state, parsed mouse IDs, ear label raw notation, normalized ear code, confidence, source photo region.
- duplicate active mouse ID is a high-risk review item.
- move/death/separation/litter/genotype changes should become events, not quiet row overwrites.

### 4. Review-Gated Canonical Writer

Adopt from:

- JCMS transaction and controlled vocabulary mindset;
- TopoDB audit/versioning;
- our existing review queue design.

Implementation direction:

- canonical updates happen only through explicit policy or review resolution.
- correction flow records before value, after value, source evidence, actor, time, and reason.
- duplicate active mouse conflicts require a movement decision, not a generic "accept" button.
- partial writes are blocked: state update, event creation, review resolution, and action/correction log should be one transaction.

### 5. Event Timeline As Durable History

Adopt from:

- external reports' recognition that current-state tables are not enough;
- our project principle that cage/card records are snapshots and durable history is events.

Implementation direction:

- `mouse_event` is the durable history layer.
- current columns are projections or convenience fields.
- event payloads should include source link, confidence/review status, related entity, previous/new values where relevant.
- core event types should cover born, separated/weaned, moved, assigned_to_mating, litter_recorded, sample_collected, genotype_recorded, dead/euthanized, correction_applied, note_added, attachment_added.

### 6. Genotype And Strain Configuration

Adopt from:

- MGI/IMSR canonical reference direction;
- mousecolonytools/nprcgenekeepr as algorithmic references;
- our rule that strain/genotype/protocol/date logic must be configurable.

Implementation direction:

- keep raw strain/genotype text separate from matched normalized value.
- unknown strain or genotype category becomes review, not automatic master creation.
- `genotype_result` is assay evidence; interpreted genotype is a projection.
- strain target genotypes, allowed categories, date rules, and protocol constraints should come from master/config tables.
- MGI/IMSR IDs should be supported as optional-but-preferred external IDs, but full sync can be staged after the photo-review-export loop is solid.

### 7. Excel As Export/View

Adopt from:

- lab's existing separation and animalsheet workflow;
- TopoDB/MyVivarium export patterns.

Implementation direction:

- existing workbooks can be imported as previous snapshots or template references.
- parsed Excel rows remain review inputs until accepted.
- generated Excel should come from accepted structured state.
- export preview must show blockers and stale export warnings.
- final `.xlsx` generation should be explicit, not automatic after every parse.

## Post-MVP Adoption Plan

These are useful, but should not pull focus from the current vertical slice.

1. QR read-only cage/card view
   - Use MyVivarium as reference.
   - Start with read-only card view before mobile mutation.

2. Task and reminder workflow
   - Useful after event model stabilizes.
   - Reminders should derive from configurable rules, not hard-coded wean/genotype dates.

3. MGI/IMSR catalog sync
   - Start with manual external IDs and curated strain master.
   - Add report ingest when local alias/review flow is working.

4. Pedigree export/viewer
   - First provide CSV/JSON pedigree export.
   - Later evaluate Open Pedigree adapter or custom viewer.

5. API/MCP wrapper
   - Keep service layer independent now.
   - Expose API/MCP only after CLI/service JSON contracts are stable.

6. ResearchGraph integration
   - Do not embed PaperPipe in MouseDB.
   - Preserve external IDs, source evidence, experiment refs, and exportable JSON so ResearchGraph can connect later.

## Non-Adoption Decisions

The following should not be adopted for our current product direction.

- Do not fork JCMS, MausDB, RodentSQL, MyVivarium, TopoDB, or Glams as the backend.
- Do not make QR/barcode required for MVP.
- Do not treat the cage card `I.D` field as a stable cage ID.
- Do not make Excel import authoritative over photo-backed accepted state.
- Do not hard-code strain names, genotype categories, protocols, mating rules, or date rules.
- Do not turn litter rows like `F1`, `F2`, pup counts, or crossed-out notes into mouse records unless mouse ID evidence supports it.
- Do not send full records to external OCR/LLM services when a minimized payload is enough.
- Do not add rich pedigree visualization before parentage, litter, and event data are reliable.

## Recommended Development Order

1. Source photo and workbook evidence store.
2. Manual/fixture OCR and ROI parsed fields.
3. Note-line parser with raw/normalized separation.
4. Review queue for low confidence, unknown strain/genotype, count mismatch, duplicate active mouse, date conflict.
5. Canonical candidate writer with source links and before/after correction log.
6. Mouse event timeline and audit trace.
7. Excel preview/export from accepted structured records.
8. Strain/genotype/rule master screens.
9. Optional external OCR/LLM extraction with confirmation and payload minimization.
10. Post-MVP QR read-only view, task/reminder, MGI/IMSR sync, pedigree export, API/MCP.

## Short Brief For Future Codex Work

When implementing features from the external research, use this filter:

```text
Does this help preserve source evidence, parse uncertain handwritten records, route risk to review, write traceable events, or generate familiar Excel outputs?
```

If yes, it is probably relevant to the current product.

If it mainly adds QR-first operation, IoT monitoring, rich dashboards, pedigree visualization, PaperPipe coupling, or large facility scheduling, it is probably post-MVP.

## Source Notes

External facts checked during review:

- MGI batch tools page reports last database update `04/21/2026` for MGI 6.24.
- Open Pedigree is LGPL-2.1, browser-based, and supports PED, LINKAGE, GEDCOM, BOADICEA, and GA4GH Pedigree/FHIR import.
- GLAMS is a 2015 Python 2 era browser-based animal management system with MIT license metadata on PyPI; it should be treated as UI/workflow reference only.
- JAX states JCMS is no longer being developed and unsupported.
- MyVivarium's public materials frame IoT as optional and QR/mobile as useful workflow support, not a requirement for our MVP.
