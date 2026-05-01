# Mouse Strain / Colony Management System 확장 설계안

## 문서 상태

Layer classification: design guidance / non-canonical project document.

이 문서는 마우스 strain registry, colony tracking, breeding 이력, genotype 결과, 실험 사용 이력, 시각화 방향을 정리한 확장 설계안이다. 최종 canonical 제품 요구사항은 `final_mouse_colony_prd.md`와 이후 채택되는 프로젝트 문서를 따른다.

이 문서의 목적은 다음과 같다.

- Strain, Mouse, Event, Experiment의 역할을 분리한다.
- 원본 사진, Excel row, OCR 결과, 사용자 수정, canonical state의 데이터 경계를 명확히 한다.
- low-confidence, conflict, biologically unlikely record를 review workflow로 보내는 기준을 잡는다.
- MVP에서 무엇을 먼저 만들고, 무엇을 나중으로 미룰지 정리한다.

## 1. 한 줄 정의

이 시스템은 단순한 "마우스 목록 DB"가 아니라, 마우스 strain 정보, 실제 개체 정보, breeding 이력, genotype 결과, 실험 사용 이력을 연결해서 관리하는 Mouse Strain Knowledge Graph + Colony Tracking System이다.

더 짧게 말하면:

> 랩이 보유한 마우스 strain과 실제 개체의 관계, 이력, breeding 상태, 실험 사용 여부를 추적하는 마우스 자산 지도이자 디지털 족보 시스템.

## 2. 핵심 철학

### 2.1 네 가지 중심 개념

이 시스템은 네 가지 개념을 중심으로 설계한다.

| 개념 | 의미 | 예시 |
| --- | --- | --- |
| Strain | 설계도, 계통, 유전적 라인 | PV-Cre, Ai14, C57BL/6J |
| Mouse | 실제 개체 | M0231, PV-Ai14-001 |
| Event | 개체 또는 colony에서 발생한 이력 | born, weaned, genotyped, moved, sacrificed |
| Visualization | 관계와 흐름을 이해하기 위한 지도 | network graph, pedigree, timeline |

Strain과 Mouse는 반드시 분리한다.

예:

- `PV-Cre`는 strain 또는 line이다.
- `Ai14`는 strain 또는 reporter line이다.
- `M0231`은 실제 마우스 개체이다.
- `M0231`의 genotype은 `PV-Cre+`, `Ai14+` 같은 결과이다.
- `M0231`의 이력은 born, weaned, genotyped, used in experiment, sacrificed 같은 event로 남긴다.

### 2.2 설계 원칙

핵심 원칙은 다음과 같다.

> Strain은 정교하게, Mouse는 가볍게, Event는 확장 가능하게, Visualization은 지도처럼 만든다.

처음부터 모든 정보를 Mouse 테이블에 넣으면 시스템이 금방 무거워진다. Mouse는 현재 상태를 빠르게 보기 위한 개체 카드로 유지하고, 자세한 변화와 이력은 MouseEvent 또는 action log에 쌓는다.

## 3. 데이터 경계 원칙

이 시스템은 cage card 사진, Excel import, OCR/LLM parsing, 사용자 correction, export가 모두 섞일 수 있다. 따라서 테이블, 파일, API response, UI 상태를 추가할 때 반드시 데이터 경계를 먼저 분류한다.

| Boundary | 의미 | 예시 |
| --- | --- | --- |
| raw source | 원본 증거 | cage card photo, imported Excel file, genotyping sheet image |
| parsed or intermediate result | 원본에서 추출된 비확정 결과 | OCR text, parsed note line, normalized DOB candidate |
| canonical structured state | 사용자가 확인했거나 정책상 확정된 구조화 상태 | confirmed mouse, strain, cage, genotype result |
| canonical event history | durable history | born event, moved event, genotyped event, correction event |
| review item | 확인이 필요한 문제 또는 제안 | low-confidence strain, duplicate mouse ID, impossible date |
| export or view | canonical state에서 생성한 출력 | Excel export, dashboard table, report preview |
| cache | 재계산 가능한 성능 보조 데이터 | dashboard count cache, current summary cache |

경계가 애매하면 기본값은 non-canonical이다. 특히 OCR, LLM, Excel import 결과는 그대로 canonical state가 되면 안 된다.

## 4. Source Evidence와 Traceability

### 4.1 SourceRecord를 초반부터 둔다

원본 cage card 사진과 Excel row는 시스템의 raw evidence이다. 모든 중요한 값은 가능하면 source photo, note line, imported row 중 하나로 거슬러 올라갈 수 있어야 한다.

권장 테이블:

```text
SourceRecord
- source_record_id
- source_type: photo / excel_row / manual_entry / genotyping_sheet / other
- source_uri
- source_label
- captured_at
- imported_at
- raw_payload
- checksum
- note
- created_at
```

예:

- source photo: `photo_2026_0501_001.jpg`
- imported Excel row: workbook filename + sheet name + row number
- manual entry: entered by user, timestamp, reason

### 4.2 Canonical 값에는 evidence link가 필요하다

다음 값들은 source evidence와 연결되어야 한다.

- strain raw text와 matched strain
- mouse display ID
- DOB 또는 DOB range
- sex/count
- ear label raw notation과 normalized code
- genotype raw result와 normalized result
- cage movement
- death/sacrifice/transfer
- experiment assignment

가능한 구현 방식:

```text
FieldEvidence
- evidence_id
- entity_type
- entity_id
- field_name
- source_record_id
- source_region
- raw_value
- parsed_value
- normalized_value
- confidence
- accepted_by
- accepted_at
```

MVP에서는 별도 `FieldEvidence` 테이블이 부담되면 각 parsed/canonical row에 `source_record_id`, `source_note_item_id`, `confidence`, `raw_value`를 최소 필드로 둔다.

## 5. Review와 Correction 원칙

### 5.1 ReviewItem은 선택 기능이 아니라 안전 장치다

다음 항목은 자동 확정하지 않고 review로 보낸다.

- OCR confidence가 낮은 값
- 알 수 없는 strain 또는 genotype category
- 기존 canonical state와 충돌하는 값
- biologically unlikely date
- duplicate active mouse ID
- card count와 note line count 불일치
- dead/sacrificed mouse가 다시 active로 나타나는 경우
- genotype result가 configured category 밖에 있는 경우
- external OCR/LLM payload가 안전한지 애매한 경우

권장 테이블:

```text
ReviewItem
- review_item_id
- entity_type
- entity_id
- issue_type
- severity
- status: open / in_review / resolved / dismissed
- source_record_id
- raw_value
- current_value
- suggested_value
- evidence
- resolution_note
- created_at
- resolved_at
```

### 5.2 CorrectionLog는 before/after를 보존한다

사용자 correction이나 inferred state change는 조용히 덮어쓰지 않는다. 반드시 before/after를 남긴다.

권장 테이블:

```text
CorrectionLog
- correction_id
- entity_type
- entity_id
- field_name
- before_value
- after_value
- reason
- source_record_id
- review_item_id
- corrected_by
- corrected_at
```

예:

- raw strain `PV Cr`를 `PV-Cre`로 correction
- mouse status `alive`를 `sacrificed`로 correction
- cage `C012`를 `C014`로 correction
- ear label `R°`와 `R'` ambiguity를 review 후 확정

## 6. Canonical State와 Current Field

### 6.1 current_* 필드는 편리하지만 위험하다

Mouse에는 다음과 같은 current field가 필요하다.

```text
current_cage_id
current_status
current_use
current_genotype_summary
```

하지만 이 값들은 event history, genotype result, cage movement와 불일치할 수 있다. 따라서 성격을 명확히 정한다.

| 값 | 권장 성격 |
| --- | --- |
| MouseEvent / ActionLog | canonical event history |
| Mouse.current_status | canonical current state, 단 event/correction과 동기화 |
| Mouse.current_cage_id | event-derived current state 또는 cache |
| Mouse.current_use | canonical current state, 변경 시 event 기록 |
| Mouse.current_genotype_summary | GenotypeResult에서 계산한 derived view 추천 |
| Dashboard count | derived view/cache |
| Excel export | export/view |

### 6.2 추천 정책

MVP에서는 `mouse_master`가 최신 accepted state를 저장하고, 모든 중요한 상태 변경은 action log 또는 MouseEvent에 함께 남긴다.

권장 규칙:

- current state를 바꾸는 모든 action은 event 또는 correction log를 남긴다.
- event만 추가하고 current state를 갱신하지 못한 partial write를 방지한다.
- current field와 event가 충돌하면 review item을 만든다.
- genotype summary는 직접 수정 가능한 원본값이 아니라 genotype result에서 만든 요약으로 취급한다.

## 7. 권장 도메인 모델

### 7.1 핵심 테이블

권장 핵심 테이블:

```text
Strain
Gene
Allele
StrainAllele
Mouse
Cage
Mating
MatingMouse
Litter
GenotypeResult
MouseEvent
Experiment
ExperimentMouse
SourceRecord
ReviewItem
CorrectionLog
Protocol
ControlledVocabulary
```

처음부터 모두 구현할 필요는 없다. 하지만 설계상 경계는 미리 잡아두는 것이 좋다.

### 7.2 Strain

Strain은 실제 개체가 아니라 유전적 라인 또는 계통 정보이다.

예:

- C57BL/6J
- PV-Cre
- Ai14
- Camk2a-Cre
- Rosa26-floxed-stop-tdTomato
- GeneX flox

권장 필드:

```text
Strain
- strain_id
- strain_name
- common_name
- official_name
- strain_type
- background
- source
- source_id
- status
- description
- breeding_difficulty
- genotyping_complexity
- phenotype_summary
- special_handling_note
- owner
- date_acquired
- date_archived
- created_at
- updated_at
```

권장 status:

| Status | 의미 |
| --- | --- |
| active | 현재 colony에서 유지 중 |
| planned | 도입 또는 생성 예정 |
| importing | 외부에서 도입 중 |
| quarantine | quarantine 또는 검역 상태 |
| frozen | sperm/embryo로 보존 |
| archived | 기록만 남기고 운영하지 않음 |
| discontinued | 더 이상 유지하지 않음 |
| lost | colony 소실 |

### 7.3 Gene

```text
Gene
- gene_id
- gene_symbol
- full_name
- organism
- description
- external_reference
- created_at
- updated_at
```

예:

- Pvalb
- Rosa26
- Camk2a
- Slc17a7
- Gad2

### 7.4 Allele

```text
Allele
- allele_id
- gene_id
- allele_name
- allele_type
- description
- inheritance
- zygosity_options
- genotyping_protocol_id
- created_at
- updated_at
```

권장 allele type:

- wildtype
- Cre
- Flp
- flox
- knockout
- knockin
- reporter
- conditional
- transgenic
- humanized
- point_mutation
- other

### 7.5 StrainAllele

하나의 strain은 여러 allele을 가질 수 있고, 하나의 allele도 여러 strain/background에 존재할 수 있다. 따라서 중간 연결 테이블을 둔다.

```text
StrainAllele
- strain_allele_id
- strain_id
- allele_id
- default_zygosity
- note
```

예:

- Strain: PV-Cre, Allele: Pvalb-IRES-Cre, Default zygosity: Het 또는 Hemizygous
- Strain: Ai14, Allele: Rosa26-LSL-tdTomato, Default zygosity: Het

### 7.6 Mouse

Mouse는 실제 개체이다. Mouse 테이블은 가볍게 유지하고, 세부 이력은 MouseEvent에 기록한다.

```text
Mouse
- mouse_id
- display_id
- strain_id
- sex
- date_of_birth
- approximate_age
- father_id
- mother_id
- litter_id
- current_cage_id
- current_status
- current_use
- current_genotype_summary
- owner
- note
- source_record_id
- created_at
- updated_at
```

권장 status:

- alive
- weaning_pending
- genotyping_pending
- available
- reserved
- breeder
- experimental
- retired
- sacrificed
- dead
- transferred
- missing
- archived

권장 use:

- stock
- breeder
- experimental
- control
- reserved
- retired
- unknown

### 7.7 Cage

```text
Cage
- cage_id
- cage_label
- location
- rack
- shelf
- cage_type
- status
- note
- created_at
- updated_at
```

권장 status:

- active
- empty
- breeding
- experimental
- quarantine
- archived

### 7.8 Mating과 MatingMouse

처음 설계에서 `male_mouse_id`, `female_mouse_id`, `second_female_mouse_id`를 Mating에 직접 넣는 방식도 MVP에서는 가능하다. 하지만 trio 이상, breeder 교체, 중간 분리, 기간별 참여를 표현하려면 `MatingMouse` 연결 테이블이 더 안전하다.

권장 구조:

```text
Mating
- mating_id
- mating_label
- strain_goal
- expected_genotype
- start_date
- end_date
- status
- purpose
- note
- created_at
- updated_at
```

```text
MatingMouse
- mating_mouse_id
- mating_id
- mouse_id
- role: male / female
- joined_date
- removed_date
- note
```

권장 Mating status:

- planned
- active
- pregnant_expected
- litter_born
- ended
- failed
- retired
- archived

### 7.9 Litter

```text
Litter
- litter_id
- litter_label
- mating_id
- birth_date
- number_born
- number_alive
- number_weaned
- weaning_date
- status
- note
- source_record_id
- created_at
- updated_at
```

권장 status:

- born
- pre_weaning
- weaning_due
- weaned
- genotyping_pending
- completed
- archived

Litter에서 offspring mouse를 생성할 때는 partial write를 특히 조심한다.

권장 흐름:

1. Litter 생성
2. number_born 기록
3. offspring draft 생성
4. mouse ID 확정
5. sex, cage, status 입력
6. Mouse canonical record 생성
7. born MouseEvent 생성

태어난 수는 알지만 개별 ID가 아직 없을 수 있으므로, `offspring draft` 또는 `pending mouse` 상태를 고려한다.

### 7.10 GenotypeResult

하나의 mouse는 여러 allele에 대해 genotype 결과를 가질 수 있다.

```text
GenotypeResult
- genotype_result_id
- mouse_id
- allele_id
- sample_id
- source_record_id
- test_date
- result
- zygosity
- method
- status
- performed_by
- confirmed_by
- confidence
- note
- created_at
- updated_at
```

권장 result:

- positive
- negative
- wildtype
- heterozygous
- homozygous
- hemizygous
- flox_plus
- flox_flox
- plus_plus
- unknown
- pending
- failed
- inconclusive

Genotype summary는 이 테이블에서 계산하는 view로 두는 것이 좋다.

### 7.11 MouseEvent

MouseEvent는 이 시스템의 핵심 테이블이다.

```text
MouseEvent
- event_id
- mouse_id
- event_type
- event_date
- related_entity_type
- related_entity_id
- source_record_id
- details
- created_by
- created_at
```

권장 event type:

- born
- weaned
- ear_tagged
- tail_biopsy
- genotyping_requested
- genotyped
- moved
- paired
- separated
- litter_produced
- assigned_to_experiment
- used_in_experiment
- sample_collected
- treated
- observed
- retired
- sacrificed
- dead_found
- transferred
- archived
- note_added
- correction_applied

예:

```text
Mouse M0231

2026-01-04 | born | LIT-2026-0081
2026-01-25 | weaned | moved to C-012
2026-01-28 | tail_biopsy | sample T-0231
2026-02-03 | genotyped | PV-Cre+, Ai14+
2026-03-12 | moved | C-012 to C-014
2026-04-08 | used_in_experiment | EXP-2026-041
2026-04-09 | sacrificed | tissue collected
```

### 7.12 Experiment와 ExperimentMouse

```text
Experiment
- experiment_id
- experiment_code
- experiment_name
- project_name
- experiment_type
- start_date
- end_date
- pi
- researcher
- description
- status
- note
- created_at
- updated_at
```

```text
ExperimentMouse
- experiment_mouse_id
- experiment_id
- mouse_id
- group_name
- role
- use_date
- sample_id
- result_reference
- note
```

Experiment와 Mouse는 many-to-many 관계이다. 한 마우스가 여러 실험, 샘플, 분석 결과에 연결될 수 있으므로 별도 연결 테이블이 필요하다.

### 7.13 Protocol

Allele에 `genotyping_protocol` 문자열을 직접 넣는 것보다 별도 Protocol 테이블을 두는 것이 좋다.

```text
Protocol
- protocol_id
- protocol_name
- protocol_type
- version
- document_uri
- status
- note
- created_at
- updated_at
```

Allele과 Protocol은 many-to-many가 될 수 있다.

### 7.14 ControlledVocabulary

strain status, allele type, mouse status, event type, genotype category, protocol type, date rule 등을 코드에 하드코딩하지 않는다.

간단한 공통 master:

```text
ControlledVocabulary
- vocabulary_id
- category
- value
- label
- description
- active
- sort_order
- created_at
- updated_at
```

MVP에서는 enum처럼 시작할 수 있지만, 코드에 특정 strain 이름이나 genotype category를 박아두면 안 된다.

## 8. 운영 Workflow

### 8.1 Strain 등록 흐름

1. Strain 생성
2. Gene 연결
3. Allele 연결
4. Background 입력
5. Source 입력
6. Breeding, phenotype, handling note 입력
7. Status를 active로 설정
8. 필요하면 My Assigned Strains에 추가

### 8.2 Photo / Excel 기반 intake 흐름

1. SourceRecord 생성
2. OCR 또는 Excel row parsing
3. raw value와 normalized candidate 저장
4. confidence와 source evidence 저장
5. validation 실행
6. review item 생성 또는 auto-fill policy 적용
7. 사용자 확인
8. canonical state 또는 event 생성
9. correction/action log 생성
10. export preview 갱신

### 8.3 Mouse 등록 흐름

필수 입력은 최소화한다.

필수:

- mouse ID 또는 display ID
- sex
- date of birth 또는 approximate age
- strain 또는 raw strain text
- current cage
- status

선택:

- father
- mother
- litter
- genotype
- owner
- experiment
- detailed note
- source evidence

### 8.4 Breeding 흐름

1. Male mouse 선택
2. Female mouse 선택
3. Mating 생성
4. Expected genotype 입력
5. Litter born 기록
6. Offspring draft 또는 mouse 생성
7. Weaning 기록
8. Genotyping 요청
9. Genotype result 기록
10. 실험용, breeder, stock으로 분류

### 8.5 Experiment 흐름

1. Experiment 생성
2. 조건에 맞는 mouse 검색
3. Mouse를 experiment group에 배정
4. Use date 기록
5. Sample ID 연결
6. Experiment 완료 후 mouse status 업데이트
7. MouseEvent에 `used_in_experiment` 기록

## 9. Validation과 Warning

초기 warning은 단순하고 직접적인 것부터 시작한다.

권장 warning:

- weaning due
- genotyping pending
- low stock
- no active breeder
- old breeder
- cage overcrowding
- experiment-ready mice available
- strain inactive but mice alive
- mouse assigned to experiment but genotype unknown
- dead/sacrificed mouse appears active
- genotype result conflicts with existing result

Low stock 예:

```text
조건:
- 특정 strain의 alive mouse 수가 5마리 이하
- active breeder가 없음
- frozen backup이 없음

결과:
- Low stock warning
- Review 또는 planning action 제안
```

Weaning due 예:

```text
조건:
- litter birth date로부터 21일 이상 지남
- litter status가 아직 pre_weaning

결과:
- Weaning due warning
```

## 10. Risk Score

Risk score는 처음부터 자동화할 필요는 없다. MVP에서는 수동 평가 또는 간단한 rule-based 점수로 시작할 수 있다.

요소:

- low_stock_score
- breeder_age_score
- breeding_difficulty_score
- genotyping_complexity_score
- phenotype_uncertainty_score
- no_backup_score
- experimental_importance_score

간단한 예:

```text
colony_risk_score =
  low_stock_score
+ breeder_age_score
+ breeding_difficulty_score
+ genotyping_complexity_score
+ no_backup_score
```

점수의 의미는 한 방향으로 통일한다. 예를 들어 높을수록 "운영 부담 또는 위험이 큼"으로 정의한다.

## 11. 주요 화면

### 11.1 Dashboard

목적: 현재 colony 상태를 빠르게 파악한다.

구성:

- active strain 수
- alive mouse 수
- active mating 수
- weaning due litter 수
- genotyping pending mouse 수
- low stock strain 수
- recent events
- open review items
- export readiness

### 11.2 Strain List

필터:

- strain name
- gene
- allele type
- background
- source
- status
- breeding difficulty
- genotyping complexity
- owner

컬럼:

- Strain name
- Gene / allele
- Background
- Status
- Alive mice
- Active breeders
- Breeding difficulty
- Colony risk
- Owner
- Last updated

### 11.3 Strain Detail

구성:

- 기본 정보
- 관련 gene / allele
- 현재 colony 현황
- active mouse 목록
- active mating 목록
- genotype distribution
- breeding notes
- phenotype notes
- risk score
- radar chart
- network graph
- related experiments
- documents / protocols
- event history

### 11.4 Mouse List

필터:

- mouse ID
- strain
- genotype
- sex
- age
- cage
- status
- use
- owner
- date of birth
- experiment assignment

컬럼:

- Mouse ID
- Strain
- Genotype
- Sex
- Age
- Cage
- Status
- Use
- Father
- Mother
- Owner
- Last event

### 11.5 Mouse Detail

구성:

- 기본 정보
- genotype 정보
- 부모 정보
- litter 정보
- cage 정보
- current status
- timeline
- experiment usage
- offspring
- notes
- attachments
- source evidence
- correction history

### 11.6 Review Queue

Review Queue는 OCR/Excel/수기 입력에서 생긴 불확실성을 처리하는 화면이다.

구성:

- source image 또는 Excel row evidence
- parsed raw value
- normalized suggestion
- current canonical value
- issue type과 severity
- before/after preview
- apply reviewed changes
- dismiss with reason

### 11.7 Export Center

Excel export는 source of truth가 아니라 canonical state에서 생성한 view이다.

구성:

- export type
- selected strain 또는 scope
- blocked review count
- record count
- last generated time
- stale export warning
- preview
- download

## 12. Visualization

### 12.1 Network Graph

목적: strain, gene, allele, mouse, cage, mating, litter, experiment 간 관계를 보여준다.

노드:

- Gene
- Allele
- Strain
- Mouse
- Cage
- Mating
- Litter
- Experiment
- Protocol
- Source

Edge:

- Gene has allele Allele
- Allele included in Strain
- Strain has Mouse
- Mouse born from Litter
- Litter produced by Mating
- Mating uses Mouse
- Mouse located in Cage
- Mouse used in Experiment
- Strain from Source
- Allele uses Protocol

### 12.2 Pedigree Tree

목적: 부모-자식 관계, littermate, breeder 성과를 보여준다.

활용:

- 특정 mouse의 부모 확인
- 특정 breeder가 생산한 offspring 확인
- phenotype 문제가 parent line과 관련 있는지 확인
- littermate control 찾기
- inbreeding 또는 backcross 기록 확인

### 12.3 Mouse Timeline

목적: 한 마우스의 생애 이벤트를 시간순으로 보여준다.

예:

```text
2026-01-04 | Born | Litter L0081
2026-01-25 | Weaned | Cage C012
2026-01-28 | Tail biopsy | Sample T0231
2026-02-03 | Genotyped | PV-Cre+, Ai14+
2026-03-12 | Moved | C012 -> C014
2026-04-08 | Used in experiment | EXP-2026-041
2026-04-09 | Sacrificed | Tissue collected
```

### 12.4 Radar Chart

Radar chart는 strain 특성 비교용으로 사용한다. 관계성 파악에는 network graph를 우선한다.

운영 리스크 radar:

- Breeding difficulty
- Genotyping complexity
- Colony risk
- Cost burden
- Handling difficulty

실험 가치 radar:

- Experimental relevance
- Phenotype strength
- Data reliability
- Availability
- Background purity

### 12.5 Heatmap

목적: genotype, age, sex, strain별 분포를 한눈에 보여준다.

예:

```text
                 3-6 weeks   6-10 weeks   10-20 weeks   >20 weeks
PV-Cre+ Ai14+        4           8             12            3
PV-Cre- Ai14+        2           5              7            1
WT                   6           9              4            0
```

### 12.6 Sankey Diagram

목적: breeding에서 experiment까지 흐름을 보여준다.

예:

```text
Mating Pair
  -> Litter
  -> Genotyped mice
  -> Selected experimental mice
  -> Experiment groups
  -> Samples / datasets
```

## 13. MVP 권장 범위

### 13.1 1단계: Evidence-first Strain Registry

필수 기능:

- strain 등록
- strain 검색
- gene / allele 등록
- background 기록
- source 기록
- status 관리
- breeding note 기록
- genotyping note 기록
- strain list view
- strain detail view
- source evidence link

목표:

- 랩에 어떤 strain이 있는지 알 수 있다.
- 각 strain의 source와 status를 알 수 있다.
- 각 strain의 gene/allele 정보를 알 수 있다.

### 13.2 2단계: Mouse 개체 카드

필수 기능:

- mouse 등록
- mouse ID 관리
- sex 기록
- DOB 또는 approximate age 기록
- strain 연결
- cage 연결
- current status 관리
- genotype summary 표시
- mouse list view
- mouse detail view

목표:

- 특정 strain에 실제 mouse가 몇 마리 있는지 알 수 있다.
- 각 mouse가 어떤 cage에 있는지 알 수 있다.
- 각 mouse의 status를 알 수 있다.

### 13.3 3단계: SourceRecord, ReviewItem, CorrectionLog

필수 기능:

- cage card photo 또는 Excel row를 raw source로 저장
- parsed/intermediate value와 canonical value 분리
- low-confidence/conflict 값을 review로 보냄
- correction before/after 보존
- source evidence에서 canonical value까지 trace 가능

목표:

- 데이터 신뢰성의 뼈대를 초반부터 확보한다.
- OCR, Excel import, 사용자 수정이 canonical state를 조용히 망가뜨리지 않게 한다.

### 13.4 4단계: MouseEvent timeline

필수 기능:

- mouse event 추가
- born, weaned, genotyped, moved, used_in_experiment, sacrificed 기록
- timeline 표시
- recent events 표시

목표:

- 개체별 이력을 시간순으로 볼 수 있다.
- Mouse 테이블을 복잡하게 만들지 않고 이력을 확장한다.

### 13.5 5단계: Genotyping, Breeding, Litter

필수 기능:

- genotype result 기록
- mating pair/group 등록
- litter 등록
- offspring mouse 생성
- weaning due 표시
- active mating list
- litter list

목표:

- breeding pair와 litter를 추적한다.
- 태어난 mouse를 litter와 연결한다.
- genotype 결과와 실험 가능 여부를 연결한다.

### 13.6 6단계: Dashboard와 Visualization

필수 기능:

- colony dashboard
- mouse timeline
- strain network graph
- pedigree tree
- radar chart

목표:

- 데이터를 표가 아니라 관계와 흐름으로 이해한다.

## 14. 처음부터 넣지 않아도 되는 기능

초기 MVP에서는 아래 기능을 미룬다.

- 복잡한 자동 genotype prediction
- 완전한 breeding outcome simulation
- barcode scanner 연동
- 동물실 장비 연동
- 전자 결재
- 완전한 LIMS 기능
- 복잡한 권한 관리
- 모든 실험 데이터 파일 저장
- 자동 보고서 생성
- AI 추천 기능

## 15. 처음부터 꼭 넣는 것이 좋은 기능

초반부터 넣어야 하는 기반:

- 고유 ID 체계
- strain과 mouse 분리
- source evidence 보존
- parsed value와 canonical value 분리
- review queue
- correction before/after log
- mouse event log
- status 관리
- 검색 기능
- 필수/선택 입력 분리
- CSV/Excel export
- note 기능
- created_at / updated_at

## 16. ID 체계

랩에서 이미 쓰는 ID 체계가 있다면 우선 존중한다. 내부 ID는 사용자에게 과도하게 노출하지 않는다.

권장 예:

```text
Strain ID: STR-0001
Mouse ID: M-2026-0001
Cage ID: C-001
Mating ID: MAT-2026-001
Litter ID: LIT-2026-001
Experiment ID: EXP-2026-001
SourceRecord ID: SRC-2026-0001
ReviewItem ID: REV-2026-0001
```

User-facing continuity anchor:

- handwritten mouse display ID
- strain
- DOB 또는 DOB range
- ear label
- cage card photo
- note-line evidence
- source Excel row

## 17. 검색 기능

검색 가능한 항목:

- mouse ID
- strain name
- gene
- allele
- genotype
- cage
- mating ID
- litter ID
- experiment code
- owner
- note
- source photo label
- sample ID
- review issue type

예시 검색어:

- `PV-Cre`
- `Ai14`
- `Pvalb`
- `Cre+`
- `C014`
- `M0231`
- `genotyping pending`
- `female 8 weeks PV-Cre+`
- `experiment-ready`
- `low stock`

## 18. 외부 OCR, LLM, Inference 사용 원칙

외부 서비스 사용 전에는 payload를 최소화한다.

원칙:

- source photo 전체가 필요하지 않으면 ROI 또는 필요한 text만 보낸다.
- colony 전체 record를 보내지 않는다.
- internal IDs, owner, project metadata는 필요 없으면 제외한다.
- 외부 inference 결과는 parsed/intermediate result로만 저장한다.
- 외부 결과가 canonical state를 직접 만들거나 덮어쓰면 안 된다.
- payload 안전성이 애매하면 local-only로 처리하고 사용자 승인을 받는다.

## 19. 구현 시 주의할 failure path

반드시 점검할 failure path:

- photo upload는 성공했지만 parse result 생성 실패
- parse retry로 duplicate review item 또는 duplicate mouse 생성
- review resolution은 성공했지만 canonical update 실패
- canonical update는 성공했지만 event/action log 생성 실패
- event 추가는 성공했지만 current state 갱신 실패
- litter 생성 중 offspring 일부만 생성
- genotype result import 중 sample 일부만 매칭
- export 생성 실패 후 stale export가 최신처럼 보임
- Excel import가 photo-backed canonical state를 덮어씀

권장 방어:

- transaction 사용
- idempotent import key 사용
- source checksum 사용
- review status와 export readiness 분리
- partial failure를 review item 또는 processing error로 표시

## 20. 최종 권장 방향

이 시스템은 처음부터 거대한 LIMS로 만들면 실패할 가능성이 높다. 현실적인 순서는 다음과 같다.

1. Strain DB로 시작한다.
2. Source evidence와 review/correction 뼈대를 얇게 넣는다.
3. Mouse 개체 카드를 붙인다.
4. MouseEvent로 이력을 쌓는다.
5. Genotyping, breeding, litter를 연결한다.
6. Dashboard와 network graph로 시각화한다.

핵심 문장:

> Strain은 configurable knowledge base로 관리하고, Mouse는 최소 current state를 가진 개체 카드로 유지하며, 모든 변화는 source evidence와 연결된 event/correction history로 남긴다. 불확실하거나 충돌하는 값은 review layer에 머물게 하고, dashboard와 export는 canonical state에서 파생된 view로 취급한다.

최종 형태:

```text
Mouse Strain Knowledge Graph
+ Mouse Colony Management
+ Breeding Tracker
+ Genotype Tracker
+ Experiment Traceability
+ Visualization Dashboard
```

가장 짧은 표현:

> 랩의 마우스 자산 지도이자 strain과 개체의 디지털 족보 시스템.
