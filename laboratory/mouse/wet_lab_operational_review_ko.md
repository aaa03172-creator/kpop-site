# Wet Lab Operational Review For Mouse Colony System

## Document Status

Layer classification: operational review / non-canonical project note.

작성일: 2026-05-03

이 문서는 15년 경력의 바이오 분야 wet lab 선임연구원 관점에서 Mouse Strain / Colony Management System 구상을 검토한 운영 보강안이다. Canonical 제품 요구사항은 `final_mouse_colony_prd.md`, `AGENTS.md`, `design.md`, `mouse_strain_colony_system_design_ko.md`, `mvp_vertical_slice_plan.md`를 따른다. 이 문서는 schema나 API response를 단독으로 확정하지 않고, 실제 업무에서 발생할 수 있는 허점, 오류, 추가 고려사항, 페르소나, workflow 우선순위를 정리한다.

## 1. Executive Summary

현재 구상은 방향이 좋다. 특히 다음 원칙은 실제 mouse colony 운영에서 매우 중요하다.

- Strain과 Mouse를 분리한다.
- 원본 cage card 사진과 Excel row를 raw evidence로 보존한다.
- OCR, ROI crop, AI draft, Excel import 결과는 parsed/intermediate candidate로 둔다.
- 불확실하거나 충돌하는 값은 review queue로 보낸다.
- 확정된 값만 canonical Mouse, Cage, Mating, Litter, Genotype, Experiment state에 반영한다.
- durable history는 MouseEvent와 action/correction log로 남긴다.
- Excel은 source of truth가 아니라 import/export view로 취급한다.

다만 실제 wet lab에서는 기술적 구조보다 운영 습관이 더 큰 리스크다. 시스템이 실패하는 대표 이유는 다음이다.

- 입력 항목이 너무 많아서 꾸준히 쓰이지 않는다.
- cage card snapshot을 현재 상태로 착각한다.
- genotype pending mouse가 실험에 섞인다.
- mouse ID, ear mark, note-line evidence가 모호한데도 자동 확정된다.
- Excel import가 기존 canonical state를 조용히 덮어쓴다.
- review queue가 쌓이기만 하고 처리되지 않는다.
- strain naming과 genotype category가 사람마다 다르게 쓰인다.
- correction history 없이 현재값만 바뀐다.

따라서 이 시스템은 "연구원을 대신해 확정하는 자동화"가 아니라 "연구원이 빠르고 정확하게 확인하도록 돕는 evidence-grounded back-office system"으로 설계되어야 한다.

## 2. Updated Operating Assumption

중요한 전제: 동물실 안에서 직접 입력할 일은 거의 없을 것으로 본다.

따라서 이 제품은 animal room real-time entry app이 아니다. 실제 운영 형태는 다음에 가깝다.

```text
동물실에서 기존 방식대로 cage card 작성
        ↓
사진, 메모, Excel 확보
        ↓
랩/오피스에서 업로드
        ↓
사진, Excel, 수기 기록 review
        ↓
확정된 내용만 canonical state와 event history에 반영
        ↓
Dashboard, search, experiment planning, Excel export에 활용
```

이 전제에서는 장갑을 끼고 동물실에서 빠르게 누르는 UI보다, 다음 화면이 더 중요하다.

- Review Workbench
- Photo Evidence Viewer
- Candidate Apply Preview
- Correction Log
- Strain Registry
- Mouse List and Detail
- Experiment Availability
- Export Center
- Dashboard

첫 화면도 넓은 dashboard보다 review desk 성격이 강해야 한다.

예시:

```text
Photos without transcription: 7
Pending review: 18
High-risk conflicts: 3
Genotype pending: 12
Weaning due candidates: 4
Ready exports: 2
```

## 3. Data Lifecycle In Practice

시스템 안에 들어온 데이터는 곧바로 정답 DB가 되면 안 된다. 실제 업무에서는 다음 생명주기를 가져야 한다.

```text
Raw Source
사진, Excel, 수기 입력, genotype sheet
        ↓
Parsed / Intermediate
OCR text, ROI crop, note-line parse, normalized candidate
        ↓
Review Item
low confidence, conflict, impossible date, ambiguous mouse ID
        ↓
Canonical State
Strain, Mouse, Cage/Card snapshot, Mating, Litter, GenotypeResult
        ↓
Event / Action Log
born, moved, paired, separated, genotyped, corrected, used_in_experiment
        ↓
View / Export
dashboard, timeline, pedigree, experiment list, Excel export
```

핵심은 "보이는 값", "해석한 값", "확정한 값"을 분리하는 것이다.

예시:

```text
raw_visible_text: "M023?"
normalized_candidate: "M0231"
confidence: 0.68
needs_review: true
source_photo_id: PHOTO-0012
source_roi: id_raw
canonical_mouse_id: not applied yet
```

위와 같이 저장해야 한다. 반대로 OCR 결과를 바로 `mouse_id = M0231`로 넣으면 위험하다.

## 4. Major Wet Lab Failure Modes

### 4.1 Mouse ID Ambiguity

Mouse ID는 가장 강한 continuity anchor지만, 동시에 가장 흔한 오류 지점이다.

실제 랩에서는 다음이 섞인다.

- `M0231`
- `231`
- `PV-Ai14-231`
- `MT318`
- ear punch 번호
- note-line temporary number
- cage card `I.D` field
- Excel row number

권장 원칙:

- `display_id`와 internal `mouse_id`를 분리한다.
- 숫자만 있는 값은 절대 자동으로 canonical mouse와 merge하지 않는다.
- 같은 display ID가 다른 연도, strain, litter, cage에서 재사용될 가능성을 고려한다.
- note-line mouse ID는 source photo와 line number까지 같이 저장한다.
- ambiguous `O/0`, `I/1/l`, `S/5`, `Z/2`, `B/8`, `G/6`는 symbol confusion으로 review에 보낸다.

### 4.2 Cage Card Snapshot Versus Current State

Cage card 사진은 현재 상태의 증거가 아니라 특정 시점의 snapshot이다.

실제 동물실에서는 다음이 흔하다.

- card가 늦게 수정된다.
- 이전 mating 정보가 남아 있다.
- weaning 후 note만 고치고 header는 그대로 둔다.
- dead/transferred mouse가 card note에 남아 있다.
- 임시 메모가 official record처럼 보인다.
- 여러 마우스가 분리되면서 card와 Excel이 잠시 어긋난다.

권장 원칙:

- `card_snapshot`과 `current_cage`를 분리한다.
- cage/card 사진은 raw source plus parsed snapshot으로 남긴다.
- 현재 상태를 바꿀 때는 apply preview를 거치고 event를 생성한다.
- `last_verified_at` 또는 `last_seen_source_at`를 둔다.
- 오래된 snapshot에서 나온 값은 stale warning을 붙인다.

### 4.3 Genotype Status Risk

Genotype은 확정값처럼 보이지만 실제로는 상태가 있다.

필요 상태:

- not_requested
- requested
- sample_collected
- pending
- failed
- inconclusive
- repeat_requested
- confirmed
- superseded

권장 원칙:

- experiment assignment는 기본적으로 confirmed genotype만 허용한다.
- pending/inconclusive genotype mouse는 warning 또는 blocker를 둔다.
- genotype result에는 method, sample ID, performed_by, confirmed_by, test_date를 둔다.
- 이전 genotype과 충돌하면 자동 overwrite하지 않고 review로 보낸다.
- genotype summary는 view/cache이고 원본 결과는 allele별 GenotypeResult로 보존한다.

### 4.4 Breeding Complexity

Mating은 pair로 시작해도 되지만 실제 케이스는 더 복잡하다.

고려할 예외:

- trio breeding
- female 교체
- male 교체
- temporary separation
- failed pregnancy
- cannibalization
- pups found dead
- foster/cross-foster
- unknown sire
- retired breeder가 card에는 active처럼 남아 있음
- litter born date와 DOB가 서로 맞지 않음

권장 원칙:

- Mating table은 현재 운영 상태를 담고, 세부 변화는 MatingEvent 또는 MouseEvent로 남긴다.
- Litter는 birth event와 weaning event를 별도로 둔다.
- litter count와 실제 created mouse count가 다르면 review item을 만든다.
- breeder age, low fertility, poor maternal care 등은 strain risk와 breeder risk 모두에 반영한다.

### 4.5 Excel Import Risk

기존 Excel은 source of truth가 아니라 사람이 편집한 view인 경우가 많다.

위험한 상황:

- 현재 상태표와 과거 이력이 한 sheet에 섞인다.
- row가 mouse인지 cage인지 litter인지 애매하다.
- 같은 mouse가 여러 sheet에 다른 상태로 존재한다.
- 수식/색상/merged cell이 의미를 가진다.
- Excel export를 다시 import할 때 중복이 생긴다.

권장 원칙:

- Excel import는 canonical write가 아니라 parsed/review candidate 생성으로 취급한다.
- imported row number, workbook filename, sheet name, raw cell payload를 저장한다.
- import source와 export artifact를 구분한다.
- stale export warning을 둔다.
- Excel에서 들어온 변경은 before/after preview 없이 canonical state를 덮어쓰면 안 된다.

## 5. Additional Data To Consider

### 5.1 Strain

Strain은 정교해야 한다. Mouse보다 더 오래 살아남는 지식 베이스이기 때문이다.

추가 권장 필드:

- official nomenclature
- common aliases
- stock number
- source institution
- genetic background detail
- backcross generation
- maintain_as: heterozygous / homozygous / hemizygous / breeder_only
- cryo_backup_status
- health_or_phenotype_concern
- breeding_scheme_note
- genotyping_protocol_version
- IACUC/protocol linkage
- active owner or project
- archive reason

### 5.2 Mouse

Mouse table은 가볍게 유지하되, 실무상 필요한 anchor는 있어야 한다.

추가 권장 필드:

- display_id
- ear tag / ear punch / tattoo / microchip
- approximate_dob flag
- origin: in_house / imported / transferred
- generation / backcross note
- usable_from_age
- usable_until_age
- health_flags
- do_not_use flag
- last_verified_at
- review_blocker_count

### 5.3 Cage / Card Snapshot

동물실에서 직접 입력하지 않더라도 card snapshot과 위치 정보는 중요하다.

추가 권장 필드:

- room
- rack
- side
- slot
- cage capacity warning
- cage purpose: breeding / holding / quarantine / experiment
- card_snapshot_date
- photo_source_id
- last_verified_at

### 5.4 Mating / Litter

추가 권장 필드:

- plug date if used
- expected birth window
- actual birth date
- pups found dead
- culled count
- sexing date
- weaning target date
- weaning completed date
- genotype sample collected date
- offspring mouse creation status
- litter review status

### 5.5 Experiment

실험 재현성을 위해 ExperimentMouse 연결이 중요하다.

추가 권장 필드:

- protocol number
- approved genotype/age/sex criteria
- group assignment
- sample ID
- tissue collected
- terminal_or_non_terminal_use
- prior use restriction
- use date
- result reference
- exclusion reason

## 6. Persona Model

책임 분담은 필요하지만, MVP에서 복잡한 permission system부터 만들 필요는 없다. 먼저 persona를 업무 역할, queue ownership, action log 관점으로 쓰는 것이 좋다.

권장 persona:

```text
1. Strain Curator
2. Colony Reviewer
3. Experiment Planner
4. Data / Export Manager
```

### 6.1 Strain Curator

역할:

- strain 이름 정리
- official name, common name, aliases 관리
- gene/allele 확인
- source/stock number 기록
- breeding note 관리
- genotyping protocol note 관리
- strain status 관리
- cryo backup 여부 확인

중요 화면:

- Strain Registry
- Strain Detail
- Strain Risk
- Protocol / Source Evidence

### 6.2 Colony Reviewer

역할:

- photo transcription review
- mouse ID ambiguity 확인
- card snapshot 확인
- cage movement 적용 여부 판단
- mating/litter 기록 확인
- genotype pending 확인
- correction log 남기기

중요 화면:

- Review Workbench
- Photo Evidence Viewer
- Candidate Apply Preview
- Correction Log
- Mouse Timeline

이 시스템에서 가장 중요한 persona다. 시스템 신뢰도는 Colony Reviewer workflow가 얼마나 빠르고 명확한지에 크게 좌우된다.

### 6.3 Experiment Planner

역할:

- 조건에 맞는 mouse 검색
- age, sex, genotype, strain 조건 확인
- experiment group 배정
- genotype confirmed 여부 확인
- review blocker가 있는 mouse 제외
- experiment mouse list export 생성

중요 화면:

- Experiment Availability
- Mouse Search
- Experiment Detail
- Export Readiness

### 6.4 Data / Export Manager

역할:

- Excel export 생성
- colony snapshot export
- genotyping queue export
- experiment mouse list export
- backup/archive 확인
- stale export warning 확인

중요 화면:

- Export Center
- Export Readiness
- Audit Log
- Archive View

### 6.5 MVP Implementation Of Personas

MVP에서는 permission보다 traceability가 중요하다.

권장 최소 필드:

```text
ReviewItem
- assigned_role
- assigned_to
- priority
- status

ActionLog
- action_type
- performed_by
- performed_role
- before_value
- after_value
- source_evidence
- created_at

ExportLog
- generated_by
- generated_role
- source_filter
- readiness_status
- created_at
```

나중에 필요하면 role-based permissions를 붙인다.

예:

- Strain Curator만 strain archive 가능
- Colony Reviewer만 canonical apply 가능
- Experiment Planner만 experiment assignment 가능
- Data Manager만 official export 가능

## 7. Recommended Back-Office Workflow

### 7.1 Strain Setup

1. Strain 생성.
2. official name, common name, alias 입력.
3. Gene/Allele 연결.
4. source, stock number, background 입력.
5. breeding scheme, genotype protocol note 입력.
6. status를 active/planned/importing 등으로 설정.
7. owner/persona 지정.

목표:

- 나중에 mouse나 card 사진이 들어왔을 때 strain matching 기준을 제공한다.
- OCR/AI가 임의 strain을 만들지 못하게 한다.

### 7.2 Photo Upload And Evidence Processing

1. 동물실에서 기존 방식으로 cage card 작성.
2. 사진을 찍고 랩/오피스에서 업로드.
3. 원본 사진을 raw source로 저장.
4. ROI/card crop을 생성하되 parsed/intermediate evidence로 저장.
5. field별 raw value, normalized candidate, confidence, source ROI를 표시.
6. 자동 확정하지 않고 review queue 또는 candidate draft로 보낸다.

목표:

- 원본 사진은 항상 보존한다.
- crop과 OCR 결과는 review 보조자료로만 쓴다.

### 7.3 Review And Apply

1. Review Workbench에서 issue를 우선순위별로 본다.
2. source photo, ROI crop, raw text, current canonical value, proposed value를 함께 본다.
3. Accept, Correct, Dismiss, Mark uncertain 중 하나를 선택한다.
4. 적용 전 apply preview를 본다.
5. 적용하면 canonical state update와 event/action log가 함께 생성된다.

목표:

- 사람의 확인 없이 high-risk state change가 들어가지 않게 한다.
- 모든 correction은 before/after와 evidence를 남긴다.

### 7.4 Colony Maintenance Review

주간 또는 실험 전 review에서 확인할 항목:

- low stock strain
- no active breeder
- old breeder
- pending genotype
- weaning due
- litter count mismatch
- cage/card stale snapshot
- mouse with review blocker
- strain inactive but alive mice exist

목표:

- 시스템을 단순 기록 보관소가 아니라 운영 점검 도구로 쓴다.

### 7.5 Experiment Planning

1. Experiment 생성.
2. 조건 검색: strain, genotype, sex, age, status, prior use.
3. review blocker, genotype pending, stale verification warning 확인.
4. mouse를 group에 배정.
5. sample ID와 use date를 기록.
6. 사용 후 used_in_experiment, sample_collected, sacrificed/dead/transferred event를 남긴다.

목표:

- 실험 결과가 특정 mouse, genotype, litter, parent, source photo까지 추적 가능하게 한다.

### 7.6 Export

1. Export Center에서 목적별 export 선택.
2. readiness check 실행.
3. blocker가 있으면 export를 막거나 warning을 표시.
4. export artifact와 generated_by, filter, timestamp를 기록.
5. Excel은 공유용 view로 쓰고, 다시 import할 경우 source evidence로 취급한다.

목표:

- 외부 공유는 기존 Excel workflow를 유지하되, 시스템 내부 truth와 혼동하지 않는다.

## 8. Review Prioritization

Review queue는 쌓이기 쉽다. 따라서 priority가 필요하다.

High priority:

- experiment assignment 관련 충돌
- genotype conflict
- mouse ID ambiguity
- dead/sacrificed mouse가 active처럼 보임
- cage overcrowding
- weaning due
- low stock with no breeder
- no source evidence for important state change

Medium priority:

- DOB ambiguity
- strain alias mismatch
- litter count mismatch
- old breeder candidate
- stale cage/card snapshot
- genotype pending but not yet assigned to experiment

Low priority:

- free text note
- old archived card
- low-confidence memo with no operational consequence
- optional phenotype note

## 9. Warning And Blocker Rules

Warning은 너무 많으면 무시된다. 따라서 blocker와 warning을 분리해야 한다.

Blocker candidate:

- mouse ID missing for canonical apply
- duplicate active mouse display ID without resolution
- genotype conflict before experiment assignment
- sacrificed/dead mouse assigned to experiment
- canonical update without source evidence
- apply preview has unresolved high-risk review item

Warning candidate:

- stale card snapshot
- genotype pending
- approximate DOB
- low confidence normalized candidate
- strain alias not fully matched
- breeder age high
- low stock risk

Informational:

- free text note added
- export generated
- photo uploaded
- ROI preview generated

## 10. MVP Reframing

동물실 안에서 입력하지 않는다는 전제를 반영하면 MVP 우선순위는 다음과 같다.

### Stage 1: Strain Registry Plus Evidence

- strain CRUD
- gene/allele/alias
- source and stock number
- breeding/genotyping notes
- active/planned/archive status

### Stage 2: Photo Evidence And Manual Transcription

- photo upload
- original photo preservation
- ROI preview
- manual transcription
- raw versus normalized fields
- photo review queue

### Stage 3: Review, Correction, Apply Preview

- review item creation
- correction before/after
- apply preview
- canonical write only after review
- action/event log

### Stage 4: Mouse, Cage/Card Snapshot, Event Timeline

- mouse current state
- card snapshot
- current cage/card link
- mouse timeline
- moved, separated, genotyped, used_in_experiment events

### Stage 5: Breeding, Litter, Genotype Queue

- mating
- litter
- offspring generation candidate
- weaning due
- genotype request/result status

### Stage 6: Experiment Planning And Export

- experiment search
- readiness check
- experiment-mouse assignment
- Excel export
- export log and stale export warning

Dashboard and visualization are useful, but Review Workbench and Export Readiness should come first.

## 11. Practical Acceptance Criteria

다음 항목을 통과하면 실제 업무에 들어갈 최소 기반이 있다고 볼 수 있다.

- 원본 photo가 저장되고 crop/ROI가 원본을 대체하지 않는다.
- 사진에서 나온 값은 raw value와 normalized candidate로 분리된다.
- low-confidence 또는 conflict 값은 review item이 된다.
- canonical apply 전에 before/after preview가 있다.
- canonical apply 후 MouseEvent 또는 ActionLog가 남는다.
- correction은 before/after와 source evidence를 보존한다.
- Excel import는 canonical overwrite가 아니라 review candidate를 만든다.
- export 전에 readiness/blocker check가 있다.
- mouse detail에서 source photo/note line/card snapshot으로 거슬러 올라갈 수 있다.
- genotype pending mouse가 실험용 confirmed mouse처럼 보이지 않는다.
- card snapshot과 current mouse state가 UI에서 구분된다.
- persona/role은 최소한 assigned_role, performed_by, generated_by로 남는다.

## 12. Recommended Next Product Decisions

다음 결정을 먼저 해야 구현이 흔들리지 않는다.

1. `last_verified_at`을 Mouse, CardSnapshot, Cage status 중 어디에 둘지 결정한다.
2. Persona를 permission이 아니라 queue ownership/action log로 먼저 구현할지 확정한다.
3. Genotype status vocabulary를 master table 또는 configurable list로 둔다.
4. Experiment assignment blocker 기준을 정한다.
5. Excel export readiness 기준을 업무별로 나눈다.
6. Review priority rule을 high/medium/low로 고정한다.
7. ROI crop evidence를 review detail까지 연결할 범위를 정한다.
8. Canonical apply가 반드시 event/action log를 생성하도록 transaction boundary를 정한다.

## 13. Final Recommendation

이 시스템은 "마우스 목록 DB"가 아니라 "사진 증거 기반 colony state review system"으로 가야 한다.

동물실 안에서 입력하지 않는다면, 제품의 중심은 Dashboard가 아니라 Review Workbench다. 사진, Excel, 수기 메모가 들어오면 시스템은 자동으로 colony state를 바꾸지 말고, evidence를 정리하고, 불확실성을 드러내고, 사람이 확정한 변경만 event와 canonical state에 반영해야 한다.

가장 중요한 한 문장:

> 시스템은 연구원을 대신해 생물학적 사실을 확정하는 도구가 아니라, 원본 증거와 후보 해석을 나란히 보여주고, 검토된 변경만 안전하게 적용하는 back-office colony review system이어야 한다.
