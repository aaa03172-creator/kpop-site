# Photo End-to-End 검증 계획

Layer classification: review item / test fixture. Canonical: false.

이 문서는 cage-card 자동 추출의 핵심 계약을 실제 사진 기반으로 반복 검증하기 위한 기준이다. 이 검증셋은 canonical 데이터가 아니며, 원본 사진, 원본 OCR/AI payload, 사용자가 고친 값은 별도 증거로 보존되어야 한다. 목적은 현재 자동 추출 파이프라인이 최소한의 안전장치를 유지하는지 확인하는 것이다.

## 왜 필요한가

단위 테스트만으로는 실제 사진에서 생기는 문제를 잡기 어렵다. 예를 들어 `RWM`처럼 유효하지 않은 ear label, 숫자 `1`과 prime mark의 혼동, 숫자만 있는 NOTE 줄, 낮은 OCR confidence, mating/litter 메모처럼 복잡한 NOTE 영역은 실제 사진 기반 회귀 테스트가 필요하다.

이 검증은 다음 원칙을 확인한다:

- 원본 사진은 raw source로 보존한다.
- AI/OCR 결과는 parsed/intermediate evidence이며 바로 canonical state를 만들지 않는다.
- 낮은 confidence, 불가능한 ear label, 애매한 note line은 review item으로 남긴다.
- 명확한 값은 auto-fill될 수 있지만 source photo와 raw note line trace를 잃지 않는다.
- export readiness는 review blocker를 고려해야 한다.

## 현재 Seed Cases

| Case ID | 목적 | 기대 동작 |
| --- | --- | --- |
| `rwm_impossible_ear_label` | `318 RWM` 같은 불가능한 ear label을 자동 확정하지 않는다. | 해당 note item은 `needs_review`로 남고, 명확한 `319 L'`, `320 R'L'`는 각각 `L_PRIME`, `R_PRIME_L_PRIME`으로 auto-fill될 수 있다. |
| `numeric_notes_are_not_mouse_ids` | NOTE 영역의 `1`-`6` 숫자 줄을 mouse ID로 조용히 오해하지 않는다. | 숫자 note label은 `needs_review`로 남고, review target에 `Numeric note label`과 `Note line anchor`가 포함된다. |
| `digit_prime_ear_label_confusion` | `300 R1`처럼 prime mark가 숫자 1로 보이는 후보를 검토 대상으로 둔다. | `300 R1`은 `needs_review`로 남고, 주변의 명확한 `L'`, `R'L'`는 보조값으로 채울 수 있다. |
| `low_confidence_card_blocks_export` | confidence가 매우 낮은 사진을 일반 잡음처럼 숨기지 않는다. | `must_review` open review가 생성되고, `raw_strain`, `sex_raw`, `mouse_count`가 uncertain field로 남는다. |
| `mating_note_lines_remain_reviewable` | mating/litter처럼 보이는 복잡한 NOTE 줄을 원문 증거로 보존한다. | `26.7.21 - 4p`, `26.48 - 10p` 같은 줄은 reviewable note item으로 남고 mouse count/notes review target이 생성된다. |

Seed case 정의는 `config/photo_e2e_validation_cases.json`에 둔다. 이 manifest는 정답 테이블이 아니라 회귀 방지 계약이다.

## 실행 방법

```powershell
python scripts/verify-photo-e2e-cases.py
```

npm 스크립트로도 실행할 수 있다.

```powershell
npm run test:photo-e2e
```

기계가 읽기 쉬운 결과가 필요하면 다음처럼 실행한다.

```powershell
python scripts/verify-photo-e2e-cases.py --json
```

## 운영 원칙

- 사진 파일은 로컬 `data/photos`의 원본을 사용한다.
- 검증은 최신 `ai_photo_extraction` parse를 대상으로 한다.
- manifest는 canonical 정답 테이블이 아니라 회귀 방지 계약이다.
- 사람이 최종 교정한 값이 생기면 별도 correction/event/structured state에 남기고, 이 검증셋에는 자동화가 지켜야 할 안전 계약만 둔다.
- 새 case를 추가할 때는 반드시 목적을 한 줄로 적고, 너무 많은 필드를 한 번에 강제하지 않는다.
- 외부 OCR, LLM, 또는 inference service를 새로 호출하지 않는다. 검증은 로컬에 저장된 사진과 SQLite parse 결과를 사용한다.

## 다음 확장 후보

- 사용자가 교정 완료한 사진을 기준으로 human-confirmed fixture를 별도로 만든다.
- ROI별 crop 검증을 추가해서 OCR 이전 단계 실패와 정규화 이후 단계 실패를 분리 채점한다.
- strain master 매칭에서 normalized strain이 raw strain과 어떻게 다른지 별도 diff로 표시한다.
- export blocker가 실제 Excel export 버튼 상태와 연결되는지 browser E2E로 확인한다.
