# Review Burden Reduction Progress

분류: implementation progress note  
데이터 경계: review item UX, parsed/intermediate review aids, export/view gate  
작성 시각: 2026-05-04 11:27:58 +09:00

## 목적

사용자가 cage-card 사진 기반 OCR/AI 추출 결과를 편하게 검토할 수 있도록, 모든 불확실성을 같은 무게의 수작업 검토로 보이게 하지 않고 실제로 확인해야 할 항목만 앞에 배치한다.

핵심 방향은 다음과 같다.

- raw photo와 raw OCR evidence는 계속 보존한다.
- review item은 없애지 않고 attention level로 나눈다.
- export를 막는 기준은 전체 open review가 아니라 Focus Review로 좁힌다.
- 사용자는 필요한 항목만 빠르게 보고, quick/trace 항목은 나중에 확인할 수 있게 한다.

## 구현 완료

### 1. Attention level

`review_attention_level`을 도입해 review item을 네 단계로 분류했다.

- `must_review`: 기본 Focus Review에 표시되고 final export를 막는다.
- `quick_check`: 빠른 확인용. 기본 export blocker는 아니다.
- `trace_only`: audit/trace에는 남지만 기본적으로 사용자를 압박하지 않는다.
- `hidden_default`: fixture/sample처럼 기본 업무 queue에서는 숨기는 항목이다.

현재 실제 데이터 기준 분포:

- open review 전체: 40
- Focus Review / must_review: 7
- Quick Check: 20
- Trace Only: 5
- Hidden Default: 8

### 2. Export gate 변경

기존에는 open review 전체가 final export를 막는 구조였지만, 현재는 `must_review`만 export blocker로 계산한다.

현재 실제 데이터 기준:

- export blocker: 7
- open review: 40
- quick/trace/hidden 항목은 reviewable 상태로 남지만 export를 과도하게 막지 않는다.

Export 화면 문구도 Focus Review blocker 기준으로 바꿨다.

### 3. Review Queue UX

Review Queue 기본 필터를 `Focus Review`로 변경했다.

추가된 UI:

- Focus / Quick / Trace / Hidden count summary
- `Quick Check`, `Trace Only`, `All Open Reviews` 필터
- 상세 패널 위치 표시: 예시 `Focus Review 1/7`
- `Previous` / `Next` 이동
- 상세 패널 `Open source photo`
- 카드 목록의 `Photo` 버튼
- Quick Check 항목의 안전한 `Looks OK` 버튼
- resolve 후 가능한 다음 review 자동 선택

데이터를 변경하는 버튼은 기존 resolve API를 사용하며, resolution note와 before/after correction trace를 보존한다.

### 4. Check target 요약

Focus Review 카드마다 사용자가 무엇을 확인해야 하는지 바로 알 수 있도록 `review_check_targets`를 API에 추가했다.

예시:

- Low OCR confidence
- Strain field
- Sex/count field
- Raw strain text
- Mouse count
- DOB
- Assigned strain match

카드와 상세 패널에 `Check` 요약으로 표시된다.

### 5. Numeric note 안전성

숫자만 있는 note line은 mouse ID로 만들지 않고 review item으로 보낸다.

현재 기준:

- grouped value는 `1, 2, 3`처럼 보기 좋게 표시한다.
- raw note line `1 2 3`과 note item anchor는 유지한다.
- count note로 확정해도 canonical mouse record를 임의로 만들지 않는다.

### 6. ROI/image 안정화

ROI crop 이미지가 동시에 요청될 때 cache 파일 읽기/쓰기 경합으로 500이 날 수 있어, ROI cache 생성과 이미지 읽기를 lock으로 보호했다.

## 검증 완료

최근 검증 결과:

- `npm run verify` 통과
- Python tests: 56 passed
- 브라우저 직접 확인:
  - Focus Review 7개 표시
  - 카드별 `Photo` 버튼 7개 표시
  - `Check` 요약 표시
  - `Previous` / `Next` 이동 정상
  - `Photo` 클릭 시 Photo Review 화면으로 이동 및 해당 사진 자동 선택
  - Export blocker 7개 표시
  - 브라우저 4xx/5xx 에러 없음

## 현재 변경 파일

주요 변경 파일:

- `app/main.py`
- `static/index.html`
- `tests/test_review_attention.py`
- `scripts/verify-local-app.py`
- `ui_image_usage_improvement_plan_ko.md`

현재 작업 트리에는 임시 모바일 스크린샷 파일도 남아 있다.

- `tmp-structure-mobile-photo.png`
- `tmp-structure-mobile-photo-after.png`
- `tmp-structure-mobile-records.png`

임시 스크린샷은 검증 산출물로 보이며, 커밋/정리 여부는 별도 판단이 필요하다.

## 남은 판단 지점

1. Focus Review 7개를 실제로 사용자가 확인하고 해결할지 결정해야 한다.
2. Quick Check 20개 중 자동 `Looks OK`로 안전하게 닫을 수 있는 범위를 더 넓힐지 판단해야 한다.
3. Export를 실제 파일로 생성하기 전, Focus Review blocker 7개는 여전히 남아 있다.
4. 임시 스크린샷 파일을 보존할지 삭제할지 결정해야 한다.
5. 현재 UI 변경 중 모바일/구조 정리 변경도 포함되어 있어, 최종 commit 전에 변경 범위를 한번 더 확인해야 한다.

