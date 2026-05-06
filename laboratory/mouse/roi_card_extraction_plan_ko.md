# Cage Card ROI Extraction Plan

## Document Status

Layer classification: implementation planning / non-canonical project note.

이 문서는 cage card 사진에서 값을 더 안정적으로 추출하기 위한 ROI crop 및 카드 영역별 분할 추출 계획이다. Canonical 제품 요구사항은 `final_mouse_colony_prd.md`, `AGENTS.md`, `design.md`, `mvp_vertical_slice_plan.md`를 따른다. 이 문서는 canonical schema나 최종 product behavior를 단독으로 정의하지 않는다.

## 의도

현재 전체 사진 한 장을 그대로 vision model에 전달하는 방식은 다음 항목에서 정확도가 낮다.

- 작은 성별 기호: `♂`, `♀`
- 숫자와 영문 혼동: `O/0`, `I/l/1`, `S/5`, `Z/2`, `B/8`, `G/6`
- ear mark: prime, circle, combined mark
- 손글씨 mouse ID
- NOTE 영역의 취소선, 덧쓴 글씨, 자유 메모

카드 양식 자체는 고정이고, 각 영역에 들어갈 값의 종류도 제한적이다. 따라서 사진 전체를 한 번에 읽기보다 카드 영역을 검출하고, 카드 기준 normalized ROI를 잘라 필드별로 제한된 추출을 수행하면 정확도와 review traceability를 높일 수 있다.

핵심 목표는 자동 확정이 아니라 **더 좋은 parsed/intermediate evidence**를 만드는 것이다. ROI 추출 결과는 canonical mouse state를 직접 쓰지 않고, review/candidate/apply 흐름을 계속 거친다.

## 핵심 가정

- 실험실 cage card 양식은 제한된 수의 고정 템플릿이다.
- 카드 색상은 blue 또는 yellow 계열이며, 색상은 card detection의 힌트로 쓸 수 있다.
- 사진 촬영 위치, 회전, 잘림, 가림은 일정하지 않다.
- 따라서 ROI 좌표는 원본 사진 좌표가 아니라 **카드 사각형을 upright 보정한 뒤의 카드 내부 비율 좌표**로 정의한다.
- NOTE 영역은 구조화 필드보다 훨씬 자유롭고 지저분할 수 있으므로 line evidence capture 중심으로 다룬다.

## Data Boundary Map

| Artifact | Boundary | Notes |
| --- | --- | --- |
| Original uploaded photo | raw source | 절대 삭제하거나 crop으로 대체하지 않는다. |
| Detected card polygon | parsed or intermediate result | 사진 내 카드 위치 추정값. 틀릴 수 있으므로 reviewable evidence로 남긴다. |
| Upright normalized card image | cache / parsed result | ROI 생성을 위한 파생 이미지. 원본 증거가 아니다. |
| ROI crop image | parsed or intermediate result | 필드별 추출 근거. source photo와 좌표를 반드시 보존한다. |
| Field extraction result | parsed or intermediate result | raw value, normalized candidate, confidence, source ROI를 포함한다. |
| NOTE line parse | parsed or intermediate result | raw line text를 보존하고 type은 candidate로만 둔다. |
| Low confidence/conflict item | review item | canonical write 전에 사용자가 확인해야 한다. |
| Accepted correction | review item plus action log | before/after와 source ROI를 보존한다. |

## Pipeline Overview

1. Upload source photo.
2. Store original photo as raw source.
3. Detect card candidate:
   - color mask: blue/yellow card paper
   - line/rectangle hints
   - fallback: ask model to identify visible card bounds if deterministic detection is weak
4. Normalize card:
   - rotate upright
   - perspective-correct if enough card corners are visible
   - if only partial card is visible, keep partial-card mode
5. Classify template:
   - `blue_structured_card`
   - `yellow_note_dense_card`
   - `partial_or_occluded_card`
   - `unknown_card`
6. Generate ROI crops using template preset.
7. Extract field values from each ROI with field-specific prompts and validators.
8. Merge ROI results into one parsed transcription payload.
9. Create review items for low-confidence, missing, conflicting, biologically unlikely, or free-text evidence.
10. Show source photo, card polygon, ROI crop, raw extracted value, normalized candidate, and review status together.

## Template: Blue Structured Card

Blue structured cards contain a repeated grid with labels such as `Strain`, `Sex`, `D.O.B`, `I.D`, `Mating date`, `LMO`, and `Note`. After upright normalization, the card can use a shared ROI preset.

### ROI Preset Draft

Coordinates are normalized to the upright card rectangle.

| ROI label | Approx x | Approx y | Approx w | Approx h | Extraction target | Validation |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `strain` | 0.14 | 0.02 | 0.58 | 0.12 | `raw_strain`, `matched_strain` | fuzzy match against My Assigned Strains and strain registry |
| `sex` | 0.14 | 0.14 | 0.20 | 0.12 | `sex_raw`, `sex_normalized`, `sex_count_raw` | `♂`, `♀`, `♂♀`, count text, unclear |
| `dob` | 0.46 | 0.14 | 0.27 | 0.12 | `dob_raw`, `dob_normalized` | date/range pattern, otherwise review |
| `id` | 0.14 | 0.26 | 0.48 | 0.12 | `id_raw`, possible card/mating ID | short text, prefix+digits, raw-preserving |
| `mating_date` | 0.14 | 0.38 | 0.48 | 0.12 | `mating_date_raw`, normalized date candidate | mating card only; missing is not always error |
| `lmo` | 0.62 | 0.26 | 0.34 | 0.24 | `lmo_raw`, `lmo_mark` | Y/N/check/blank/unclear |
| `biohazard_icon` | 0.78 | 0.02 | 0.18 | 0.18 | `hazard_mark_present` | supporting evidence only |
| `note_block` | 0.03 | 0.50 | 0.94 | 0.45 | `raw_note_lines[]`, line candidates | raw line preservation first |

The initial preset should be treated as a starting calibration. It should be visible/editable in development tooling before being trusted broadly.

### Field-Specific Extraction Rules

`strain`
- Preserve raw handwriting exactly as visible.
- Match only against configured assigned strain names and aliases.
- Do not create a new confirmed strain from OCR alone.

`sex`
- Preserve visible symbol/text.
- `♂` means male, `♀` means female.
- If both symbols or counts are present, keep raw count text and route ambiguity to review.

`dob`
- Preserve raw date text.
- Normalize only when the pattern is clear.
- Ranges such as `25.09.06-19` should retain both raw and normalized candidate range.

`id`
- Do not treat card `I.D` as stable cage ID.
- Preserve raw text, including prefixes and ambiguous characters.
- Ambiguous `O/0` or `I/1` should be noted in `symbol_confusions`.

`lmo`
- Preserve visible `Y/N`, check marks, circles, or blanks.
- Do not infer biological meaning beyond raw mark candidate.

## Template: Yellow Note-Dense Card

Yellow cards in the current sample set are often NOTE-heavy and may be photographed partially. They should prioritize note evidence capture over structured field extraction.

| ROI label | Extraction target | Notes |
| --- | --- | --- |
| `note_left_column` | `raw_note_lines[]` | Preserve line order if visible. |
| `note_right_column` | `raw_note_lines[]` | Preserve line order if visible. |
| `red_annotations` | `raw_annotation_text`, `annotation_candidate_type` | Examples such as red `AD`; route to review. |
| `header_if_visible` | visible strain/id/date candidates | Only extract fields that are actually visible. |
| `lmo_if_visible` | raw LMO mark candidate | Optional. |

Yellow card output should tolerate partial visibility. Missing structured fields should be `missing_or_occluded`, not hallucinated.

## NOTE Handling

NOTE is not a narrow structured field. It can contain mouse IDs, ear labels, litter notes, counts, dates, extra comments, corrections, strike-throughs, and mistakes. The goal is **line evidence capture**, not automatic cleanup.

Each note line should produce:

| Field | Description |
| --- | --- |
| `raw_line_text` | Visible line text exactly as read. |
| `line_number` | Order within ROI/column. |
| `source_roi_label` | `note_block`, `note_left_column`, or `note_right_column`. |
| `parsed_type` | `mouse_item`, `litter_event`, `count_note`, `free_text_note`, `unknown`. |
| `parsed_mouse_display_id` | Candidate only. |
| `parsed_ear_label_raw` | Raw ear mark text. |
| `parsed_ear_label_code` | Alias-normalized candidate only. |
| `parsed_count` | Count candidate when applicable. |
| `strike_status` | `none`, `single`, `double`, `unclear`. |
| `confidence` | Field confidence. |
| `needs_review` | True for ambiguity, conflict, low confidence, or free text. |
| `review_reason` | Human-readable reason. |

Rules:
- Do not drop unreadable or messy lines.
- Do not merge separate visible lines unless the card clearly wraps one line.
- Do not invent mouse IDs from numeric-only temporary labels.
- Preserve crossed-out or overwritten text as evidence and route it to review.
- Free-form comments should become `free_text_note`, not parsing errors.

## Review UI Requirements

The reviewer should be able to see:

- original source photo;
- detected card polygon;
- upright normalized card preview;
- ROI crop for each extracted field;
- extracted raw value;
- normalized candidate;
- confidence;
- `symbol_confusions`;
- review action needed;
- trace back to source photo and ROI coordinates.

For NOTE lines, review detail should show the note ROI crop and highlight the line when possible. Full line highlighting can be deferred, but ROI-level crop evidence should be part of the first implementation.

## Implementation Plan

### Phase 1: Preset And Evidence Model

- Add ROI preset configuration file for card templates.
- Add ROI extraction result shape to API payloads.
- Store source photo ID, card polygon, ROI label, normalized coordinates, confidence, and raw crop metadata.
- Do not require full computer-vision detection yet; allow model-assisted or manually approximated card bounds.

### Phase 2: Crop Generation

- Generate upright card image when card bounds are available.
- Generate ROI crop images for structured fields and note blocks.
- Add local endpoints for ROI crop preview.
- Keep crops as derived parsed/intermediate artifacts, not raw source.

### Phase 3: Field-Specific AI Extraction

- Send full card plus ROI crops to the model.
- Use field-specific instructions:
  - sex ROI reads sex/count only;
  - dob ROI reads date only;
  - id ROI reads visible ID text only;
  - note ROI reads line-by-line evidence.
- Merge crop outputs into the existing transcription payload.
- Store `raw_visible_text_lines`, `symbol_confusions`, field confidence, and ROI source references.

### Phase 4: Review Integration

- Show ROI crop evidence in Review Queue detail.
- Route low-confidence and conflicting fields to review.
- Ensure corrections preserve before/after and source ROI.
- Ensure canonical apply still requires reviewed candidate flow.

### Phase 5: Calibration And Test Set

- Use the current uploaded sample photos as a calibration set.
- Maintain a small set of expected human-read values for each representative card.
- Test:
  - blue upright card;
  - blue partial card;
  - rotated card;
  - yellow note-dense card;
  - occluded/taped field;
  - messy NOTE with crossed-out lines.

## Risks And Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Card detection fails due to crop/occlusion | Missing fields | partial-card mode; show missing ROI as review item |
| Fixed ROI is misaligned after perspective distortion | Wrong extraction | detect card polygon and perspective-correct before ROI |
| Tape or cage plastic obscures text | Low accuracy | confidence/review routing; preserve raw photo |
| NOTE parsing over-interprets messy text | Bad candidates | raw line preservation; conservative `unknown`/`free_text_note` |
| Model reads plausible but invisible values | Data integrity risk | require raw_visible_text_lines and ROI evidence; review before canonical writes |
| More API calls increase latency/cost | Slower upload | batch ROI crops per photo into one model request where possible |

## Acceptance Criteria

- Uploaded photo remains raw source evidence.
- ROI extraction never writes canonical mouse state directly.
- Each extracted field includes source photo ID and ROI label.
- Low-confidence or conflicting values create review items.
- NOTE lines preserve raw text even when parsing fails.
- UI shows field value beside ROI crop evidence.
- Photo selection updates the displayed extracted fields and ROI evidence together.
- Export readiness remains blocked by unresolved review items.
