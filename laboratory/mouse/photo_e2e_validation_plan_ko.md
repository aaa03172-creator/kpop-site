# 실사진 End-to-End 검증셋

## 의도

이 문서는 cage-card 자동 추출의 핵심 계약을 실제 사진으로 반복 검증하기 위한 기준이다. 이 검증셋은 canonical 데이터가 아니라 `review item / test fixture`다. 원본 사진, 원본 OCR/AI payload, 사용자가 고친 값은 별도 증거로 보존하고, 이 문서는 현재 자동 추출 파이프라인이 최소한의 안전장치를 유지하는지 확인한다.

## 왜 필요한가

단위 테스트만으로는 실제 사진에서 생기는 문제를 잡기 어렵다. 특히 `RWM`처럼 있을 법하지 않은 ear label, 숫자 `1`과 prime mark의 혼동, 숫자만 있는 NOTE 줄, 낮은 OCR confidence, mating/litter 메모처럼 지저분한 NOTE 영역은 실제 사진 기반 회귀 테스트가 필요하다.

## 현재 seed cases

- `rwm_impossible_ear_label`: `318 RWM` 같은 불가능한 ear label은 자동 확정하지 않고 review로 남긴다.
- `numeric_notes_are_not_mouse_ids`: NOTE에 적힌 `1`-`6` 숫자 줄은 mouse ID로 조용히 승격하지 않는다.
- `digit_prime_ear_label_confusion`: `300 R1`처럼 prime mark와 숫자 1이 섞인 후보는 review로 남기고, 주변의 명확한 `L'`, `R'L'`는 자동 보조값으로 채운다.
- `low_confidence_card_blocks_export`: confidence가 매우 낮은 사진은 must-review로 올려 export 차단 대상이 된다.
- `mating_note_lines_remain_reviewable`: mating/litter처럼 보이는 NOTE 줄은 원문 라인을 보존하고 불확실한 값은 review 대상으로 둔다.

## 실행 방법

```powershell
python scripts/verify-photo-e2e-cases.py
```

또는 npm 스크립트로 실행한다.

```powershell
npm run test:photo-e2e
```

기계가 읽기 쉬운 결과가 필요하면 다음처럼 실행한다.

```powershell
python scripts/verify-photo-e2e-cases.py --json
```

## 운영 원칙

- 사진 파일은 `data/photos`의 로컬 원본을 사용한다.
- 검증은 최신 `ai_photo_extraction` parse를 대상으로 한다.
- manifest는 정답 테이블이 아니라 회귀 방지 계약이다.
- 사람의 최종 교정값이 생기면 별도 correction/event/structured state에 남기고, 이 검증셋에는 “자동화가 지켜야 할 안전 계약”만 넣는다.
- 새 케이스를 추가할 때는 반드시 목적을 한 줄로 적고, 너무 많은 필드를 한 번에 강제하지 않는다.

## 다음 확장 후보

- 사용자가 교정 완료한 사진을 기준으로 human-confirmed fixture를 따로 만든다.
- ROI별 crop 품질 점검을 추가해서 “OCR 이전 단계”와 “정규화 이후 단계”를 분리 채점한다.
- strain master와 매칭된 normalized strain이 raw strain과 어떻게 다른지 별도 diff로 표시한다.
