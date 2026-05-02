# Mouse Colony MVP Acceptance Matrix

Layer classification: implementation verification / non-canonical project note.

이 문서는 현재 MVP가 수기 cage-card 기반 colony tracking의 핵심 흐름을 어느 정도 만족하는지 확인하기 위한 acceptance matrix이다. Canonical 제품 요구사항은 `final_mouse_colony_prd.md`와 `AGENTS.md`를 따른다.

## 검증 원칙

- Raw photo, Excel row, manual transcription은 source 또는 parsed evidence로 남아야 한다.
- Parsed/intermediate 값은 review/correction 또는 명시적 apply 없이 canonical mouse state를 쓰지 않는다.
- Mouse continuity는 mouse ID와 note-line evidence를 중심으로 추적한다.
- Cage/card records는 snapshot이고, durable history는 event/action/correction으로 남긴다.
- Export는 source of truth가 아니라 canonical/reviewed state에서 생성되는 view이다.

## Acceptance Matrix

| ID | 영역 | Acceptance Criterion | 현재 상태 | 자동 검증 근거 |
| --- | --- | --- | --- | --- |
| A01 | Source Photo | 사진 업로드는 raw source로 저장되고 원본 bytes/image endpoint로 재조회된다. | Done | `scripts/verify-local-app.py` photo upload/image assertions |
| A02 | Photo Review | 업로드된 사진은 transcription review candidate를 생성하고, 승인 기반 AI extraction은 draft를 reviewable parsed evidence로 저장한다. | Done | `Photo review candidate should be visible in Review Queue`, `AI extraction should save parsed note evidence` |
| A03 | Photo Transcription Boundary | manual/AI photo transcription은 parsed/intermediate이며 canonical mouse를 직접 만들지 않는다. | Done | `created_mouse_candidates == 0` assertion |
| A04 | Card Snapshot | manual transcription은 `card_snapshot`을 만들고 photo/parse/note summary trace를 가진다. | Done | `/api/card-snapshots` assertions |
| A05 | Note Evidence | note line은 raw text, parsed type, interpreted status, normalized ear label을 분리 보존한다. | Done | `/api/note-items` assertions |
| A06 | Review Evidence | Review detail은 note item, card snapshot, raw photo evidence를 보여준다. | Done | `Review Note Evidence`, `review_note_summary`, `image_url` assertions |
| A07 | Label Correction | 숫자-only note label은 count/mouse/note/ignore로 review correction 가능하다. | Done | `note_label_decision`, `count_note` assertions |
| A08 | Correction Trace | review correction은 before/after를 `correction_log`와 `action_log`에 남긴다. | Done | `parsed_label`, `correction_applied` assertions |
| A09 | Evidence Comparison | photo-backed manual transcription과 predecessor Excel row를 비교하고 review item을 만들 수 있다. | Done | `/api/evidence-comparison` and review-candidates assertions |
| A10 | Canonical Draft | resolved comparison review는 canonical candidate draft를 만들며 아직 canonical write가 아니다. | Done | `Canonical candidate should remain a draft` assertions |
| A11 | Apply Preview | canonical candidate apply preview는 write 전 mouse/event/duplicate risk를 보여주고 state를 바꾸지 않는다. | Done | `/apply-preview` no-write assertions |
| A12 | Canonical Apply | draft apply는 note-line trace가 있는 mouse records와 events를 생성한다. | Done | `canonical_candidate_applied` assertions |
| A13 | Apply Audit/Void | applied candidate는 audit 가능하고 삭제 없이 voided 상태/event로 되돌릴 수 있다. | Done | `/audit`, `/void`, `canonical_candidate_voided` assertions |
| A14 | Cage Movement | cage move는 current assignment와 movement event/action을 같이 기록한다. | Done | `mouse_cage_moved`, active/ended assignment assertions |
| A15 | Breeding/Litter | mating, litter, offspring, weaning 흐름은 parent/litter/source/event trace를 남긴다. | Done | mating/litter/offspring/weaning assertions |
| A16 | Genotyping | genotyping request/result는 record/event/action과 mouse latest state를 갱신한다. | Done | genotyping dashboard/record/event assertions |
| A17 | Export Readiness | open review blockers가 있으면 final export를 막고 blocker context를 보여준다. | Done | export preview/blocker/export-log assertions |
| A18 | Final Exports | review blockers 해소 후 CSV/XLSX export가 생성되고 traceability sheet/context를 포함한다. | Done | ready CSV, separation XLSX, animal sheet XLSX assertions |
| A19 | Dashboard/Views | dashboard, mouse detail, strain detail, records views는 hard-coded demo data 없이 API state로 렌더한다. | Done | UI string and anti-demo assertions |
| A20 | Data Boundaries | source, parsed, review, canonical, export/view boundary가 주요 응답에 명시된다. | Mostly Done | API boundary assertions across source/parsed/review/canonical/export flows |

## 주요 Gap / 다음 검증 후보

| Gap ID | 내용 | 권장 다음 작업 |
| --- | --- | --- |
| G01 | 실제 브라우저에서 fixture가 아닌 사용자가 사진 업로드, AI extraction 저장, review resolve, apply/export까지 수행하는 full E2E 자동화가 아직 약하다. | Playwright 또는 in-app browser 기반 photo extraction E2E 추가 |
| G02 | Review detail은 evidence를 보여주지만 crop/ROI 수준의 이미지 근거는 아직 없다. | note line crop 또는 photo annotation 후보 검토 |
| G03 | Configurable masters 일부는 구현됐지만 status/event/genotype category 전체가 master화된 것은 아니다. | controlled vocabulary registry 추가 |
| G04 | Experiment traceability는 장기 설계에는 있으나 MVP 자동 흐름에는 아직 약하다. | experiment-mouse link MVP 추가 |
| G05 | Batch upload progress는 workbench queue 수준이며 batch_id 기반 progress model은 아직 없다. | upload batch table/view 추가 |

## 현재 Go / No-Go 판단

Personal MVP 기준으로는 **Go에 가깝다**.

이유:
- source photo -> parsed transcription -> review/correction -> canonical candidate -> apply/void -> export readiness 흐름이 연결되어 있다.
- raw evidence와 normalized/canonical state의 boundary가 대부분 유지된다.
- high-risk rewrite는 review/correction/action log를 거치도록 되어 있다.
- CSV/XLSX export는 blocker와 readiness 검증을 거친다.

다만 실제 운영 투입 전에는 G01과 G05를 우선 보강하는 것이 좋다.
