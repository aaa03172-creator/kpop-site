# Selective Normalization Controls Plan

분류: product/workflow design document / non-canonical planning note
데이터 경계: review item UX, parsed/intermediate transcription, normalized candidate selection
작성 기준일: 2026-05-04

## 목적

사용자가 cage-card 사진, OCR/AI draft, Excel import review를 확인할 때 직접 기입해야 하는 값을 줄이고, 후보 범위가 제한된 값은 선택형 컨트롤로 고르게 한다. 단, 선택값은 raw evidence를 덮어쓰지 않는다.

## 원칙

1. Raw evidence는 그대로 보존한다.

   사진에서 보이는 원문, OCR raw text, manual transcription raw value, Excel cell value는 수정하지 않는다.

2. 선택값은 normalized 또는 matched candidate로 저장한다.

   예: `sex_raw = "♀ 8"`은 그대로 두고, reviewer가 `female`을 선택하면 `sex_normalized = "female"`로 별도 저장한다.

3. 후보가 제한된 필드는 직접 입력보다 선택을 우선한다.

   카드 타입, 성별 해석, LMO/Y/N, note-line 해석, genotype status, assigned strain match는 select, segmented control, combobox를 우선 사용한다.

4. Master가 필요한 값은 하드코딩하지 않는다.

   Strain, genotype, protocol, status vocabulary는 DB/config/API에서 가져온다. 후보에 없는 값은 unmatched/review 경로로 보낸다.

## 우선 적용 대상

- Manual transcription form
  - card type select
  - assigned strain match select from active assigned strains
  - sex normalized select
  - LMO/Y/N select

- Review detail correction
  - numeric note: count note / mouse item / reviewed note / ignored note
  - ear label: normalized label candidate 선택
  - AI photo draft: check targets 기반 필드 선택

- Excel import review
  - strain candidate 선택
  - genotype/status candidate 선택
  - row action 선택: accept / reject / map to canonical candidate

## 저장 정책

- `raw_*` 값은 사용자가 선택형 normalized 값을 바꿔도 유지한다.
- `matched_*`, `*_normalized`, review decision, correction after value는 before/after action log에 남긴다.
- canonical write 전에는 선택값도 review item 또는 parsed/intermediate state로 취급한다.
- export blocker는 선택되지 않았거나 conflicting/high-risk인 값만 막는다.

## 이번 구현 절편

Manual transcription UI에 다음 선택 컨트롤을 추가한다.

- `matched_strain`: active assigned strain 목록에서 선택. 비워두면 raw strain을 matched 후보로 사용한다.
- `sex_normalized`: blank/use raw, male, female, mixed, unknown, not_visible.
- `lmo_raw`: blank/not recorded, Y, N, unknown, not_visible.

백엔드는 `sex_normalized`를 optional payload로 받아 card snapshot에 raw sex와 별도 저장한다. 기존 raw sex 기반 자동 normalize는 fallback으로 유지한다.

## Implemented follow-up: ear-label review select

- Review detail now treats `Ear label needs review` as a bounded correction flow.
- The reviewer chooses one normalized ear-label code from a select control instead of typing a free-form reviewed value.
- Supported MVP choices are `R_PRIME`, `L_PRIME`, `R_CIRCLE`, `L_CIRCLE`, combined two-side codes, `NONE`, and `UNREADABLE`.
- The raw note text and raw ear-label token remain unchanged.
- The selected normalized code updates only `card_note_item_log` as parsed/intermediate evidence and records an action-log before/after trace.
- Canonical mouse state is still not overwritten by this review action.

## Implemented follow-up: mixed sex implies mating card

- If the visible sex/count evidence contains both male and female symbols or words, the normalized sex value is `mixed`.
- A `mixed` sex interpretation defaults the parsed/intermediate card type to `Mating` when the current card type is blank, unknown, or `Separated`.
- This is a review-time operational inference only. The raw sex text remains unchanged, and canonical mating records are still created through the source-backed mating workflow.
