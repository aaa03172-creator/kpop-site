# Mouse Colony MVP Acceptance Matrix

Layer classification: implementation verification / non-canonical project note.

이 문서는 현재 Mouse Colony MVP가 handwritten cage-card 기반 colony tracking의 핵심 흐름을 어느 정도 충족하는지 확인하기 위한 acceptance matrix이다. Canonical 제품 요구사항은 `final_mouse_colony_prd.md`와 `AGENTS.md`를 따른다. 이 문서는 구현 상태를 사람이 검토하기 위한 비정규화된 확인표이며, 데이터베이스나 API의 source of truth가 아니다.

## 검증 원칙

- Raw photo, Excel row, manual transcription은 raw source 또는 parsed evidence로 남긴다.
- Parsed/intermediate 값은 review, correction, 또는 명시적 apply 없이 canonical mouse state를 갱신하지 않는다.
- Mouse continuity는 mouse ID와 note-line evidence를 중심으로 추적한다.
- Cage/card records는 snapshot이고, durable history는 event/action/correction으로 남긴다.
- Export는 source of truth가 아니라 canonical/reviewed state에서 생성되는 view이다.
- `evals/cage_card_skill_gym/`은 non-canonical safety eval layer이다. Probe는 review/test fixture이며 runtime, DB, API, canonical state, 또는 최종 workflow를 정의하지 않는다.

## Acceptance Matrix

| ID | 영역 | Acceptance Criterion | 현재 상태 | 자동 검증 근거 |
| --- | --- | --- | --- | --- |
| A01 | Source Photo | 사진 업로드는 raw source로 저장되고 원본 bytes/image endpoint로 조회된다. | Done | `scripts/verify-local-app.py` photo upload/image assertions, `Photo image endpoint should return the preserved raw upload bytes` |
| A02 | Photo Review | 업로드된 사진은 transcription review candidate를 만들고, 승인 기반 AI extraction은 reviewable parsed evidence로 저장한다. | Done | `Photo review candidate should be visible in Review Queue`, `AI extraction should save parsed note evidence`, `Extract & Save Review` |
| A03 | Photo Transcription Boundary | manual/AI photo transcription은 parsed/intermediate이며 canonical mouse를 직접 만들지 않는다. | Done | `created_mouse_candidates == 0`, `Manual photo transcription should stay parsed/intermediate` |
| A04 | Card Snapshot | manual transcription은 `card_snapshot`을 만들고 photo/parse/note summary trace를 가진다. | Done | `/api/card-snapshots`, `card_snapshot_id` assertions |
| A05 | Note Evidence | note line은 raw text, parsed type, interpreted status, normalized ear label을 분리 보존한다. | Done | `/api/note-items` assertions |
| A06 | Review Evidence | Review detail은 note item, card snapshot, raw photo evidence를 보여준다. | Done | `Review Note Evidence`, `review_note_summary`, `image_url` assertions |
| A07 | Label Correction | 숫자-only note label은 count/mouse/note/ignore로 review correction 가능하다. | Done | `note_label_decision`, `count_note` assertions |
| A08 | Correction Trace | review correction은 before/after를 `correction_log`와 `action_log`에 남긴다. | Done | `parsed_label`, `correction_log`, `correction_applied` assertions |
| A09 | Evidence Comparison | photo-backed manual transcription과 predecessor Excel row를 비교하고 review item을 만들 수 있다. | Done | `/api/evidence-comparison` and review-candidates assertions |
| A10 | Canonical Draft | resolved comparison review는 canonical candidate draft를 만들지만 아직 canonical write가 아니다. | Done | `Canonical candidate should remain a draft` assertions |
| A11 | Apply Preview | canonical candidate apply preview는 write 대상, mouse/event, duplicate risk를 보여주고 state를 바꾸지 않는다. | Done | `/apply-preview`, `Canonical candidate apply preview should not write mouse state` assertions |
| A12 | Canonical Apply | draft apply는 note-line trace가 있는 mouse records와 events를 생성한다. | Done | `canonical_candidate_applied` assertions |
| A13 | Apply Audit/Void | applied candidate는 audit 가능하고 삭제 없이 voided 상태/event로 되돌릴 수 있다. | Done | `/audit`, `/void`, `canonical_candidate_voided`, `Re-voiding a voided canonical candidate should be blocked` assertions |
| A14 | Cage Movement | cage move는 current assignment와 movement event/action에 함께 기록한다. | Done | `mouse_cage_moved`, active/ended assignment assertions |
| A15 | Breeding/Litter | mating, litter, offspring, weaning 흐름은 parent/litter/source/event trace를 남긴다. | Done | mating/litter/offspring/weaning assertions |
| A16 | Genotyping | genotyping request/result는 record/event/action과 mouse latest state를 갱신한다. | Done | genotyping dashboard/record/event assertions |
| A17 | Export Readiness | open review blockers가 있으면 final export를 막고 blocker context를 보여준다. | Done | export preview/blocker/export-log assertions, `blocked_review_items`, `review_blockers` |
| A18 | Final Exports | review blockers 해소 후 CSV/XLSX export가 생성되고 traceability sheet/context를 포함한다. | Done | ready CSV, separation XLSX, animal sheet XLSX assertions, `Ready CSV export should succeed`, `Ready separation XLSX export should succeed` |
| A19 | Dashboard/Views | dashboard, mouse detail, strain detail, records views는 hard-coded demo data 없이 API state로 렌더된다. | Done | UI string and anti-demo assertions |
| A20 | Data Boundaries | source, parsed, review, canonical, export/view boundary가 주요 응답에 명시된다. | Mostly Done | API boundary assertions across source/parsed/review/canonical/export flows |
| A21 | Safety Eval Layer | cage-card workflow safety probes는 non-canonical fixture로 실행되며 raw evidence, review routing, traceability, no-direct-canonical-write 원칙을 확인한다. | Done | `npm run test:cage-card-skill-gym` |
| A22 | Photo Evidence Ledger | photo/card/note evidence item은 source photo, raw observed text, confidence, reviewability, linked mouse/event trace를 보존한다. | Done | `tests/test_photo_evidence_ledger_schema.py`, `photo_evidence_item`, `review_evidence_link` |
| A23 | Genotype Evidence Enforcement | genotype result confirmation은 source photo, photo evidence item, 또는 source record 없이 canonical genotype state를 갱신하지 않는다. | Done | `tests/test_genotyping_evidence_enforcement.py`, `Genotype result confirmation requires evidence` |
| A24 | High-Risk Mouse Event Evidence | death, sacrificed, moved, weaned 같은 high-risk mouse event는 source evidence 없이 canonical event를 생성하지 않는다. | Done | `tests/test_mouse_event_evidence_enforcement.py`, `High-risk mouse events require evidence` |
| A25 | Validation Report Artifact | canonical apply/export 전 validation report artifact가 pass/block 상태와 source refs를 남긴다. | Done | `tests/test_artifact_workflow.py`, `validation_report` |
| A26 | Export Manifest Artifact | CSV/XLSX export는 export_manifest artifact로 validation report, source refs, state watermark, filename을 추적한다. | Done | `tests/test_artifact_workflow.py`, `export_manifest` |
| A27 | Strain Gene/Allele Registry | Strain creation preserves legacy gene/allele text while creating source-backed normalized gene, allele, and strain-allele link records. | Done | `tests/test_strain_knowledge_graph.py`, `scripts/verify-local-app.py`, `Strain creation should populate the normalized gene registry`, `strain_allele_relationship` |

## 주요 Gap / 다음 검증 후보

| Gap ID | 내용 | 권장 다음 작업 |
| --- | --- | --- |
| G01 | 실제 브라우저에서 fixture가 아닌 사용자 사진 업로드, AI extraction, review resolve, apply/export까지 수행하는 full E2E 자동화가 아직 약하다. | Playwright 또는 in-app browser 기반 photo extraction E2E 추가 |
| G02 | Review detail은 evidence를 보여주지만 crop/ROI 사진 근거와 note-line highlight는 아직 제한적이다. | note line crop 또는 photo annotation 흐름 검토 |
| G03 | configurable masters 일부는 구현됐지만 status/event/genotype category 전체가 master화된 것은 아니다. | controlled vocabulary registry 확장 |
| G04 | Experiment traceability 설계는 있지만 MVP 자동 흐름에는 아직 얇게 연결되어 있다. | experiment-mouse link MVP 추가 |
| G05 | Batch upload progress/workbench queue는 `upload_batch`, `/api/upload-batches`, release preview, close flow로 구현되었다. 다만 실제 브라우저 E2E에서 업로드 batch 전체 흐름을 검증하는 보강은 남아 있다. | G01의 browser E2E에 batch upload flow 포함 |

## 현재 Go / No-Go 판단

Personal MVP 기준으로는 **Go에 가깝다**.

이유:

- source photo -> parsed transcription -> review/correction -> canonical candidate -> apply/void -> export readiness 흐름이 연결되어 있다.
- raw evidence와 normalized/canonical state boundary가 대부분 유지된다.
- high-risk rewrite는 review/correction/action/evidence gate를 거치도록 되어 있다.
- CSV/XLSX export는 blocker와 readiness 검증을 거친다.
- Batch upload는 raw source batch로 묶이고 release preview가 canonical write 없이 closure readiness를 점검한다.

다만 실제 운영 투입 전에는 G01을 우선 보강하는 것이 좋다. 특히 실제 브라우저에서 photo upload, optional AI extraction approval, review resolution, candidate apply, export readiness가 한 번에 이어지는지 확인해야 한다.
