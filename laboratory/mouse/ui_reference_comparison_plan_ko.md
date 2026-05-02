# UI Reference Comparison And Redesign Plan

Layer classification: export or view
Status: planning document, non-canonical
Date: 2026-05-02

## 목적

이 문서는 이전에 참고한 UI 레퍼런스 화면과 현재 MouseDB 로컬 앱을 비교하고, Mouse Colony 프로젝트의 evidence-first 원칙을 유지하는 리디자인 방향을 정리한다.

목표는 레퍼런스 화면을 그대로 복제하는 것이 아니다. 레퍼런스의 제품 완성도, 내비게이션, 정보 밀도, 시각적 위계를 받아들이되, 현재 시스템의 핵심인 원본 cage card 사진 보존, 수동 전사, 리뷰, 비교, 추적 가능한 승인 흐름을 중심에 둔다.

## 레퍼런스 화면 요약

### 1. Colony Dashboard

Colony Dashboard 레퍼런스는 성숙한 운영 도구의 shell을 보여준다.

채택할 점:
- 고정 left navigation과 top utility bar.
- colony-level KPI 카드.
- 밀도는 높지만 읽기 쉬운 visualization grid.
- alerts, active matings, weaning due, sex ratio, genotype distribution, network preview를 한 화면에서 파악할 수 있는 구성.
- 프로토타입보다 실제 운영 dashboard에 가까운 느낌.

주의할 점:
- 이미 정제되고 승인된 데이터를 전제로 한다.
- 불확실성을 예쁜 숫자 카드 뒤에 숨길 위험이 있다.
- review workflow가 안정되기 전에 dashboard 장식이 먼저 커질 수 있다.

### 2. Mouse Detail

Mouse Detail 레퍼런스는 개별 mouse record 화면의 좋은 모델이다.

채택할 점:
- mouse identity가 화면 중심에 있다.
- basic information, genotype, pedigree, timeline, cage, experiment usage, notes가 구분되어 있다.
- status badge가 record 해석을 돕는다.
- timeline이 durable history의 위치를 명확히 한다.

주의할 점:
- 기본적으로 canonical record처럼 보인다.
- 값이 raw photo, reviewed note line, predecessor Excel, manual correction 중 어디에서 왔는지 드러나지 않는다.
- 이 프로젝트에 맞추려면 source traceability indicator가 필요하다.

### 3. Strain Detail

Strain Detail 레퍼런스는 장기적으로 strain-level visualization에 유용하다.

채택할 점:
- gene, allele, strain, cross, mouse, experiment 관계를 network로 보여주는 방식.
- strain risk/utility를 compact하게 보여주는 profile/radar view.
- overview, genetic info, lineage, mice, experiments, resources, history를 나누는 tab 구조.

주의할 점:
- 현재 source evidence가 보장하는 것보다 더 큰 확실성을 암시할 수 있다.
- reliable normalized strain/genotype data가 필요하다.
- review와 acceptance flow가 충분히 신뢰 가능해진 뒤 도입해야 한다.

## 현재 앱 평가

현재 앱의 강점은 local evidence workbench로서의 성격이다.

이미 좋은 방향:
- raw cage-card photo를 보존한다.
- manual photo transcription이 있고 parsed/intermediate layer로 유지된다.
- predecessor Excel은 non-canonical view로 import된다.
- manual photo transcription과 legacy workbook row를 비교할 수 있다.
- 비교 mismatch를 Review Queue blocker로 만들 수 있다.
- 해결된 review에서 canonical candidate draft를 만들 수 있다.
- candidate draft를 적용할 때만 canonical structured state에 쓴다.
- open review item이 있으면 final export가 막힌다.
- source evidence, review history, correction, event, audit trace가 workflow에 들어가 있다.

현재 UI 약점:
- 너무 많은 section이 한 페이지에 세로로 쌓여 있다.
- 제품이라기보다 engineering MVP처럼 보인다.
- reference 수준의 product shell과 navigation이 아직 부족하다.
- 가장 중요한 workflow인 photo review가 시각적으로 충분히 우선순위를 갖지 못한다.
- core review task가 완전히 프레이밍되기 전에 dashboard 성격의 section이 먼저 보인다.
- table은 기능적이지만 decision-oriented review panel로 다듬어지지 않았다.

## 제품 방향

첫 polished screen은 일반적인 colony dashboard가 아니라 Photo Review Workbench가 되어야 한다.

이유:
- 현재 실제 입력은 최신 cage-card photo와 predecessor Excel file이다.
- 가장 위험한 동작은 불확실한 evidence로 colony state를 accept 또는 overwrite하는 것이다.
- lab workflow는 여전히 handwritten cage card를 중심으로 돌아간다.
- 제품은 clean operational state를 시각화하기 전에 review, compare, correct, accept를 도와야 한다.

권장 positioning:
- Primary product mode: evidence-first colony management.
- First screen: Photo Review Workbench.
- Secondary screens: Evidence Comparison, Review Queue, Export Readiness.
- Later screens: Mouse Detail, Strain Detail, Colony Dashboard.

## 목표 Information Architecture

### Primary Navigation

레퍼런스처럼 persistent left sidebar를 둔다.

권장 nav item:
- Dashboard
- Photo Review
- Evidence Comparison
- Review Queue
- Colony Records
- Mouse Detail
- Strain Detail
- Mating & Litters
- Genotyping
- Exports
- Settings

### Top Bar

Persistent top bar에는 다음을 둔다.
- Global search.
- Current colony selector.
- Export readiness indicator.
- Open review count.
- Help/settings affordance.

Top bar는 blocker가 있을 때 final export를 유도하지 않아야 한다.

## 권장 화면 계획

### Phase 1: App Shell

목표: 데이터 동작을 바꾸지 않고 production shell을 더한다.

변경:
- left sidebar navigation 추가.
- top utility bar 추가.
- 기존 section을 view container로 그룹화.
- 한 번에 하나의 primary view를 보여주는 구조.
- 기존 API와 test 보존.

Acceptance criteria:
- 기존 workflow verification이 통과한다.
- navigation 변경으로 canonical write가 새로 생기지 않는다.
- review, photo, comparison, candidate, export section이 계속 접근 가능하다.

### Phase 2: Photo Review Workbench

목표: latest photo review를 primary workflow로 만든다.

Layout:
- Left panel: photo inbox와 selected raw photo preview.
- Center panel: manual transcription form과 parsed note lines.
- Right panel: source status, related Excel candidates, review blockers.

중요 상태:
- Uploaded, awaiting transcription.
- Transcribed, awaiting comparison.
- Comparison review created.
- Review resolved.
- Candidate draft created.
- Candidate applied.

Rules:
- raw photo preview는 보존된 local source image endpoint에서 가져온다.
- manual transcription은 parsed/intermediate layer로 유지한다.
- uncertain/conflicting value는 reviewable 상태로 남긴다.
- OCR 또는 manual transcription만으로 canonical update를 자동 수행하지 않는다.

### Phase 3: Evidence Comparison

목표: manual photo와 predecessor Excel 비교를 decision view로 바꾼다.

권장 card field:
- photo transcription summary.
- legacy workbook candidate summary.
- matched fields.
- mismatched fields.
- review status.
- review ID.
- candidate draft status.
- source photo link/preview.
- workbook row reference.

Actions:
- Create comparison review.
- View review.
- Resolve review.
- Map to canonical candidate draft.

Rules:
- comparison은 export/view layer이다.
- review candidate는 review item layer이다.
- candidate draft는 명시적으로 apply되기 전까지 review item layer이다.

### Phase 4: Review Queue

목표: review item을 단순 table이 아니라 action view로 만든다.

권장 layout:
- Filters: open, resolved, severity, evidence availability.
- Main list: issue, source, evidence preview, status.
- Detail panel: raw source context, current value, suggested value, source note lines, resolution controls, correction logging fields.

Rules:
- final decision에는 resolution note가 필요하다.
- duplicate 또는 biologically unlikely acceptance는 계속 blocker로 남아야 한다.
- user correction은 before/after value를 보존해야 한다.

### Phase 5: Export Readiness

목표: export가 왜 막혔는지 또는 준비됐는지 명확히 보여준다.

권장 content:
- readiness status card.
- open blocker count.
- blocker preview list.
- expected export filenames.
- last export log.
- staleness indicator.

Rules:
- open review item이 있으면 final export는 계속 blocked 상태여야 한다.
- preview export는 예상 결과를 보여줄 수 있지만 final acceptance처럼 보이면 안 된다.
- export log는 blocked attempt도 기록한다.

### Phase 6: Mouse Detail

목표: 충분한 reviewed data가 생긴 뒤 Mouse Detail 레퍼런스를 source-aware하게 적용한다.

레퍼런스 대비 필수 추가:
- 주요 field별 source evidence badge.
- review status 또는 confidence indicator.
- audit trace link.
- current canonical state와 raw/parsed evidence 분리.

섹션:
- Header identity.
- Basic information.
- Genotype.
- Cage/location.
- Timeline.
- Pedigree.
- Experiment usage.
- Notes and source evidence.

### Phase 7: Strain Detail

목표: strain/genotype normalization이 강해진 뒤 Strain Detail 레퍼런스를 적용한다.

레퍼런스 대비 필수 추가:
- configurable strain/genotype masters.
- source-backed relationship edge.
- unknown 또는 low-confidence state indicator.
- strain별 review count.

섹션:
- Strain header.
- Active mice and breeders.
- Genetic network.
- Genotype distribution.
- Related experiments.
- Quick reference.
- Risk/readiness profile.

### Phase 8: Colony Dashboard

목표: evidence와 review workflow가 안정된 뒤 Colony Dashboard 레퍼런스를 적용한다.

Dashboard가 요약할 항목:
- active strains.
- alive mice.
- open reviews.
- export readiness.
- weaning due.
- active matings.
- genotyping pending.
- low stock 또는 low availability alert.

Dashboard visualization 규칙:
- chart가 accepted state, review candidate, mixed data 중 무엇을 쓰는지 표시한다.
- uncertain value를 total 안에 조용히 숨기지 않는다.

## Visual Design Direction

채택:
- light, quiet operational UI.
- persistent navigation.
- compact KPI card.
- small status badge.
- dense table with clear hierarchy.
- 반복 record나 bounded record에 card section 사용.
- timeline과 network visualization은 유용할 때 사용.

피할 것:
- marketing-style hero section.
- decorative gradient 또는 oversized visual treatment.
- 불확실성을 숨기는 clean dashboard number.
- inferred biological state를 사용자가 무심코 accept하도록 압박하는 UI.

## Data Boundary Mapping

| UI area | Layer |
| --- | --- |
| Raw photo preview | raw source |
| Manual transcription form output | parsed or intermediate result |
| Evidence comparison | export or view |
| Comparison review candidate | review item |
| Canonical candidate draft | review item |
| Applied candidate output | canonical structured state |
| Export preview | export or view |
| Export download | export or view |
| Export log | export or view |
| Audit trace | export or view |

## Implementation Order

1. App shell with sidebar and top bar.
2. Existing long page section을 view container로 전환.
3. Photo Review Workbench를 default view로 설정.
4. Evidence Comparison을 table에서 decision card로 개선.
5. Review Queue detail panel 개선.
6. Export Readiness panel 정리.
7. Source-aware Mouse Detail view 추가.
8. Source-aware Strain Detail view 추가.
9. Canonical accepted data가 충분히 성숙한 뒤 full Colony Dashboard 재검토.

## Verification Plan

매 phase마다 확인:
- `python scripts/verify-local-app.py`.
- `npm test`.
- `npm run verify`.
- desktop width browser screenshot.
- mobile/narrow layout text overlap 확인.
- raw photo, manual transcription, comparison view에서 새로운 canonical write가 생기지 않는지 확인.
- open review blocker가 final export를 계속 막는지 확인.

## Recommended Next Step

Phase 1과 Phase 2를 하나의 contained UI restructuring으로 구현한다.

작업:
- sidebar/topbar shell 추가.
- Photo Review Workbench를 첫 visible workflow로 설정.
- 기존 ID와 API call은 가능한 유지.
- 현재 local photo preview, manual transcription, review queue, evidence comparison data를 재사용.
- UI state가 기존 API로 표현 불가능한 경우가 아니라면 새 data model change는 만들지 않는다.

이렇게 하면 레퍼런스의 제품 완성도와 시각적 방향을 가져오면서도, Mouse Colony 프로젝트의 evidence-first 원칙을 유지할 수 있다.
