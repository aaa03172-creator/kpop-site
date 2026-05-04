# Review Burden Reduction Plan

## 문서 목적

이 문서는 cage-card OCR/ROI 추출 이후 사용자에게 요구되는 확인 작업이 과도해지는 문제를 검토하고, 실제 연구실 workflow에서 피로감을 줄이기 위한 제품 방향과 구현 기준을 정리한다.

분류: product/workflow design document / non-canonical planning note  
데이터 경계: review item 설계 및 export/view UX 계획  
Canonical status: non-canonical. 이 문서는 review 부담을 줄이기 위한 제품/UX 계획이며, `final_mouse_colony_prd.md`, `AGENTS.md`, adopted project documents를 대체하거나 단독으로 canonical schema/API behavior를 확정하지 않는다.
작성 기준일: 2026-05-04

## 핵심 판단

현재 시스템은 불확실성을 잘 보존하는 쪽으로 발전했지만, 사용자에게 보이는 Review Queue는 아직 "모든 불확실성"을 "즉시 사람이 확인해야 하는 일"처럼 보여준다. 이 구조는 정확도와 traceability에는 유리하지만, 실제 사용성에는 부담이 크다.

이 제품의 목적은 사람이 모든 OCR 결과를 수작업 검수하게 만드는 것이 아니라, raw photo evidence를 보존하면서 위험한 항목만 편하게 확인하도록 돕는 것이다. 따라서 다음 단계의 핵심은 review item 개수를 줄이는 것이 아니라, review 부담을 예외 중심으로 재분류하는 것이다.

## 현재 상태 요약

현재 열린 review item은 40개다.

| 유형 | 개수 | 현재 문제 |
| --- | ---: | --- |
| AI-extracted photo transcription needs review | 17 | 사진마다 1개씩 열려 있어 모든 사진을 확인해야 하는 느낌을 준다. |
| Unlabeled numeric note needs review | 12 | 숫자 note가 한 줄씩 review로 쪼개져 반복 작업처럼 보인다. |
| Outside assigned strain scope | 5 | fixture/sample 데이터가 실제 작업 review처럼 섞여 보인다. |
| Ear label needs review | 4 | 일부는 필요하지만, 사진 단위 review와 분리되어 맥락이 약하다. |
| Duplicate active mouse | 1 | 실제로 high priority로 유지해야 한다. |
| Low-confidence strain alias | 1 | strain curator가 봐야 하지만 기본 작업 화면에 섞일 필요는 낮다. |

최신 AI 추출 17장 기준:

| 분류 | 개수 | 의미 |
| --- | ---: | --- |
| assigned strain 자동 매칭 | 13 | `ApoMtg/tg`로 alias 기반 정리 완료 |
| strain attention 필요 | 4 | 빈 strain, `ApoM 7`, `Atg4M Tg/Tg` 등 |
| high attention | 6 | 낮은 confidence, 빈 strain/sex, 핵심값 누락 |
| medium attention | 6 | notes/count/DOB 등 일부 확인 필요 |
| light attention | 5 | raw value와 주요 추출이 대체로 충분함 |

## 사용자 피로를 만드는 원인

1. Review Queue가 너무 평평하다.

   High risk와 light uncertainty가 같은 "open review"처럼 보인다. 사용자는 무엇부터 봐야 하는지 알기 어렵고, 모든 항목을 확인해야 한다고 느낀다.

2. 사진 단위 맥락이 깨져 있다.

   숫자 note, ear label, AI transcription review가 따로 쪼개져 있어 같은 사진을 여러 번 확인하게 만든다.

3. 개발/fixture review가 실제 업무에 섞여 있다.

   fixture/sample review는 검증에는 필요하지만, 사용자의 오늘 업무 queue에 보이면 불필요한 피로가 된다.

4. DOB normalization 불확실성이 과도하게 전면화된다.

   raw DOB가 보존되어 있고 canonical write 전까지 정규화가 필요하지 않은 경우에도 review blocker처럼 보인다.

5. 자동 매칭된 값도 계속 의심하게 만든다.

   assigned strain alias로 exact/high-confidence match된 경우는 "확인 완료에 가까운 draft"로 보여야지, "사용자가 다시 검수할 일"처럼 보이면 안 된다.

## 제품 원칙

1. Raw evidence는 보존한다.

   원본 사진, raw OCR text, raw note line은 계속 저장한다. 자동 처리로 원본 evidence를 덮어쓰지 않는다.

2. Canonical write 전에는 위험 항목만 막는다.

   모든 uncertainty를 export blocker나 manual blocker로 올리지 않는다.

3. Review는 field 중심보다 사진 중심이어야 한다.

   사용자가 사진 한 장을 열었을 때 필요한 확인을 한 번에 끝낼 수 있어야 한다.

4. Light uncertainty는 숨기지 않고 낮은 마찰로 보인다.

   로그, badge, trace detail에는 남기되 기본 queue에서 사용자를 압박하지 않는다.

5. 사람이 할 일은 "수정"보다 "확인/예외 처리"가 기본이어야 한다.

   대부분의 사진은 "괜찮으면 넘어가기"가 가능해야 한다. 반대로 고위험 항목은 명확하게 알려야 한다.

## 제안하는 Review 레벨

### Level 1. Must Review

사용자가 반드시 봐야 하는 항목이다. export/canonical candidate 생성을 막아도 된다.

조건 예시:

- strain이 비어 있음
- sex/count가 비어 있거나 서로 충돌함
- confidence가 매우 낮음
- duplicate active mouse
- 동일 mouse ID가 서로 다른 active cage/card에 걸림
- 사진 crop 자체가 카드가 아니거나 거의 읽을 수 없음

현재 후보:

- `KakaoTalk_20260502_102059315_14.jpg`
- `KakaoTalk_20260502_102059315_01.jpg`
- `KakaoTalk_20260502_102059315_13.jpg`
- `KakaoTalk_20260502_102059315_16.jpg`
- `KakaoTalk_20260502_102059315_03.jpg`
- `KakaoTalk_20260502_102059315_04.jpg`

### Level 2. Quick Check

한 번 훑으면 되는 항목이다. 기본 queue에는 접혀 있거나 "quick check" 그룹으로 보여야 한다.

조건 예시:

- assigned strain은 자동 매칭됨
- sex/count가 있음
- raw DOB는 보존되었지만 normalized DOB가 비어 있음
- LMO 체크가 불확실함
- note line 일부가 애매하지만 canonical write에 직접 쓰이지 않음

현재 다수의 `ApoMtg/tg` 자동 매칭 사진이 여기에 해당한다.

### Level 3. Trace Only

사람에게 즉시 확인을 요구하지 않는다. trace detail이나 audit log에는 남긴다.

조건 예시:

- raw DOB가 있고 normalized DOB만 비어 있음
- assigned strain exact alias match
- LMO raw가 비어 있지만 현재 workflow에서 canonical write에 쓰지 않음
- card type이 unknown이지만 strain/sex/count/note continuity에는 영향이 낮음

### Level 4. Hidden By Default

기본 사용자 workflow에서 숨긴다.

조건 예시:

- fixture/sample parse review
- 개발 검증용 duplicate fixture
- 과거 superseded AI extraction review
- 이미 더 최신 photo transcription에 의해 대체된 review

## 구현 제안

### 1. Focus Review 기본 필터

Review Queue의 기본값을 "Open export blockers"가 아니라 "Focus Review"로 바꾼다.

Focus Review 조건:

- 실제 uploaded photo 기반
- 최신 parse_result 기반
- status open
- high attention 또는 must review 조건
- fixture/sample source 제외
- superseded 제외

예상 효과:

- 사용자가 처음 보는 review 수가 40개에서 약 4-6개 수준으로 줄어든다.
- "오늘 봐야 할 것"이 명확해진다.

### 2. 사진 단위 Review Summary 생성

현재처럼 review item을 나열하기보다 photo card에 다음 정보를 요약한다.

- "확인 필요: strain"
- "확인 필요: sex/count"
- "확인 필요: note labels"
- "참고: DOB normalized pending"
- "자동 처리됨: assigned strain ApoMtg/tg"

사용자는 사진 한 장에서 필요한 것만 보고 넘어갈 수 있어야 한다.

### 3. Unlabeled Numeric Note 그룹화

현재 숫자 note가 개별 review로 생성된다.

예:

- `1`
- `2`
- `3`
- `4`
- `5`

이를 사진 단위 하나로 묶는다.

제안:

- review issue: `Numeric note labels need review`
- current_value: `1, 2, 3, 4, 5`
- suggested_value: `Confirm as temporary labels, ignore, or map to mouse IDs`

예상 효과:

- 반복 클릭과 반복 resolution note 입력을 크게 줄인다.

### 4. Low-risk 자동 분류

다음 조건을 만족하면 기본 review queue에서 제외하거나 light review로 낮춘다.

- `matchedStrain`이 active assigned strain에 exact alias match
- sex symbol과 count가 존재
- raw DOB가 존재
- confidence >= 65
- note line이 canonical mouse creation에 직접 쓰이지 않음

이 항목은 "auto-prepared, trace retained" 상태로 남기고, export/candidate 단계에서만 다시 확인하도록 한다.

### 5. Fixture/Sample Review 숨김

사용자 기본 화면에서는 `source_name = fixtures/sample_parse_results.json` review를 숨긴다.

필요하면 Settings 또는 Developer/Diagnostics view에서만 볼 수 있게 한다.

### 6. Review Resolution 마찰 줄이기

현재 review resolve에는 resolution note 입력이 필요하다. 고위험 canonical 변경에는 맞지만, low-risk/light review에는 과하다.

제안:

- Must Review: resolution note required
- Quick Check: one-click `Looks OK` 허용, 자동 note 생성
- Trace Only: 사용자가 열지 않아도 진행 가능

자동 note 예시:

`Reviewed as low-risk OCR draft; raw photo and parsed values retained.`

## 현재 데이터에 대한 적용 예시

### Must Review 후보

| 사진 | 이유 |
| --- | --- |
| `_14.jpg` | confidence 5, 핵심 필드 대부분 비어 있음 |
| `_01.jpg` | strain/sex 빈 값, confidence 46 |
| `_13.jpg` | strain `Atg4M Tg/Tg`, sex `??`, confidence 52 |
| `_16.jpg` | strain `ApoM 7`, DOB 없음, confidence 58 |
| `_03.jpg` | confidence 46, note/DOB 확인 필요 |
| `_04.jpg` | confidence 56, sex/count와 DOB 확인 필요 |

### Quick Check 후보

| 사진 | 이유 |
| --- | --- |
| `_15.jpg` | strain `ApoMtg/tg` 자동 매칭, sex/count 있음, DOB raw 있음 |
| `_11.jpg` | strain/sex/count 양호, DOB raw 있음 |
| `_10.jpg` | strain/sex/count 양호, DOB raw 있음 |
| `_07.jpg` | strain/sex/count 양호, DOB raw 있음 |
| `_08.jpg` | strain/sex/count 양호, DOB raw 있음 |

### Trace Only 후보

아래 항목은 raw evidence가 보존되어 있으면 기본 queue에서 강하게 압박하지 않아도 된다.

- `dob_normalized` only uncertainty
- `lmo_raw` uncertainty
- `card_type` unknown

## 구현 순서 제안

1. `review_attention_level` 계산 함수 추가

   입력: review item, parse payload, photo source  
   출력: `must_review`, `quick_check`, `trace_only`, `hidden_default`

2. `/api/review-items` 응답에 attention level과 reason 추가

   기존 review item은 유지하되 UI가 부담을 줄일 수 있게 한다.

3. Review Queue 기본 필터를 Focus Review로 변경

   기본 표시: must_review만  
   토글: quick_check 포함, all review 포함

4. numeric note review 그룹화

   새 review 생성은 사진/parse 단위로 묶는다. 기존 개별 review는 supersede하거나 hidden_default로 내린다.

5. one-click quick resolution 추가

   Quick Check 항목은 `Looks OK` 버튼으로 해결 가능하게 한다.

6. fixture/sample review 기본 숨김

   사용자 workflow와 개발 검증 데이터를 분리한다.

## 성공 기준

1. 기본 화면에서 사용자가 보는 open review가 40개에서 4-6개 수준으로 줄어든다.
2. 사진 한 장에 대해 같은 맥락의 review를 여러 번 열지 않는다.
3. raw photo, raw OCR, before/after correction은 계속 trace 가능하다.
4. high-risk canonical write는 여전히 review 없이 진행되지 않는다.
5. 사용자가 "확인해야 할 것"과 "참고로 남긴 것"을 한눈에 구분할 수 있다.

## 결론

현재 extraction/ROI/matching 자체는 전보다 좋아졌지만, review UX는 아직 너무 보수적이다. 다음 제품 개선은 정확도 자체보다 "확인 부담을 줄이는 설계"가 우선이다.

권장 다음 작업은 Focus Review 모드와 attention level 계산을 도입하는 것이다. 이렇게 하면 데이터 traceability 원칙은 유지하면서도, 사용자가 실제로 확인해야 하는 작업량을 크게 줄일 수 있다.
