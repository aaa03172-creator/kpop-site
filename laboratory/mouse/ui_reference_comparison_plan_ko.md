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

## Generated Mockup Review

Layer classification: export or view
Status: visual reference review, non-canonical
Generated image location: `C:\Users\User\.codex\generated_images\019de2df-1d85-7d30-bbbb-ed71b447de50`

아래 이미지는 구현 사양이 아니라 UI 방향 검토용 visual reference이다. 화면 안의 날짜, ID, 개체 수, strain, genotype, 파일명은 모두 예시이며 canonical state나 실제 colony 기록으로 취급하지 않는다.

### Generated Pages

| Page | Generated image | Review decision |
| --- | --- | --- |
| Early Photo Review Workbench | `ig_0c032b98dc1209df0169f56f96fc20819199f05236d1af761c.png` | 초기 방향 검토용. 이후 생성된 Photo Review Workbench가 더 좋다. |
| Early Dashboard | `ig_0c032b98dc1209df0169f570359a988191b319b6870d93e871.png` | 초기 방향 검토용. 이후 생성된 Dashboard가 더 좋다. |
| Colony Dashboard | `ig_0c032b98dc1209df0169f5718e12f88191919da8cbbb9c96fe.png` | 장기 목표 reference로 채택. 구현 우선순위는 낮음. |
| Photo Review Workbench | `ig_0c032b98dc1209df0169f5725053888191b00067f215b80fc1.png` | Phase 1-2의 핵심 reference로 채택. |
| Evidence Comparison | `ig_0c032b98dc1209df0169f5730f34688191bf1b191eb1d98612.png` | Phase 3 reference로 채택. |
| Review Queue | `ig_0c032b98dc1209df0169f573bec3d88191b8b79a02b65628ef.png` | Phase 4 reference로 강하게 채택. |
| Mouse Detail | `ig_0c032b98dc1209df0169f5751ac5d48191b1e0f363a858d33d.png` | Phase 6 reference로 채택. |
| Strain Detail | `ig_0c032b98dc1209df0169f575cfa3c48191b28ad6af5db5d403.png` | Phase 7 reference로 채택. |

### Overall Review

생성된 mockup들은 기존 레퍼런스 이미지의 장점인 shell, topbar, KPI, 카드 밀도, 상태 badge를 잘 가져왔다. 동시에 현재 MouseDB의 핵심 원칙인 raw photo, parsed/intermediate, review item, canonical candidate, export blocker를 UI에 드러내는 방향도 비교적 잘 반영했다.

가장 좋은 방향:
- Photo Review Workbench를 첫 화면으로 둔다.
- Review Queue는 list/detail split view로 만든다.
- Evidence Comparison은 table 중심이되, 오른쪽 evidence inspector를 붙인다.
- Mouse Detail과 Strain Detail은 source-backed 상세 화면으로 후속 구현한다.
- Colony Dashboard는 accepted canonical state가 충분히 쌓인 뒤 최종 운영 화면으로 다듬는다.

주의할 점:
- 생성 이미지의 텍스트는 일부 AI가 만든 placeholder이므로 그대로 복사하지 않는다.
- 생성 이미지의 생물학적 관계, 날짜, genotype, count는 실제 기록이 아니다.
- UI가 너무 깔끔해 보이면 unresolved evidence가 accepted state처럼 보일 수 있다.
- dashboard 수치는 반드시 accepted state, review candidate, mixed state 중 무엇인지 표시해야 한다.
- raw photo와 predecessor Excel 사이의 priority를 시각적으로 계속 유지해야 한다.

## Page-by-Page Review

### Colony Dashboard Mockup

좋은 점:
- reference #1과 유사한 운영 dashboard 밀도가 나온다.
- accepted state only 안내와 review blocker panel이 있어 evidence-first 원칙과 충돌하지 않는다.
- KPI, heatmap, age chart, sex ratio, readiness, alerts 구성이 균형적이다.
- 좌측 navigation과 topbar가 제품 느낌을 만든다.

개선할 점:
- Dashboard가 너무 앞에 오면 사용자가 검토 전 데이터를 이미 확정된 상태로 오해할 수 있다.
- `canonical candidates 339`처럼 숫자가 과도하게 확정적으로 보이는 표현은 실제 구현에서 조심해야 한다.
- 초기 제품에서는 Dashboard를 default로 두지 않는다.

결론:
- 장기 dashboard target으로 유지.
- Phase 8에서 구현.
- Phase 1에서는 shell, KPI 스타일, readiness warning만 일부 차용.

### Photo Review Workbench Mockup

좋은 점:
- 현재 제품 단계에 가장 잘 맞는 화면이다.
- raw photo preview가 중앙에 있어 원본 사진이 primary evidence라는 점이 명확하다.
- Photo Inbox, Manual Transcription, Parsed Note Lines, Next Actions가 한 흐름에 놓여 있다.
- `Does not write canonical mouse state` 경고가 좋다.
- 실제 사용자가 사진을 보면서 전사하고, 비교와 review blocker로 넘기는 흐름이 자연스럽다.

개선할 점:
- note line 입력과 parsed note line 결과 사이의 관계를 더 직접적으로 연결하면 좋다.
- `Compare`, `Create blocker`, `Map candidate` 버튼은 조건별 disabled/enabled 상태가 필요하다.
- 사진 preview는 확대, 회전, fit/actual size 같은 조작이 필요할 수 있다.

결론:
- Phase 1-2의 핵심 구현 reference로 채택.
- 첫 화면 default는 이 방향이 가장 좋다.

### Evidence Comparison Mockup

좋은 점:
- table과 right-side inspector 조합이 좋다.
- manual transcription과 predecessor Excel candidate의 차이가 한눈에 보인다.
- matched/mismatched fields가 review 판단을 쉽게 만든다.
- Excel이 predecessor view일 뿐 source of truth가 아니라는 경고가 포함되어 있다.
- review state와 candidate draft 상태가 같은 행에 있어 workflow continuity가 좋다.

개선할 점:
- row action은 `Create review`, `View review`, `View candidate`, `No action needed`처럼 상태별로 정확히 갈라야 한다.
- Excel row snapshot은 실제 workbook source cell reference를 더 명확히 보여줘야 한다.
- `exact match`도 자동 canonical write로 이어지면 안 된다는 표시가 필요하다.

결론:
- Phase 3 reference로 채택.
- 기존 Evidence Comparison table을 decision table + evidence inspector로 발전시킨다.

### Review Queue Mockup

좋은 점:
- 가장 실제 업무 화면에 가깝다.
- left list와 right detail split view가 review 처리에 적합하다.
- raw source evidence, current value, suggested/context value, note lines, resolution controls가 한 화면에 있다.
- export blocker 이유가 명확하다.
- correction log preview가 있어 before/after 기록 원칙과 잘 맞는다.

개선할 점:
- resolution note required 상태를 더 강하게 표현해야 한다.
- `Accept legacy` 같은 선택지는 lab policy상 위험하므로, 실제 UI에서는 “legacy를 참고값으로 채택”인지 “canonical 후보로 매핑”인지 더 엄밀하게 표현해야 한다.
- review resolve와 canonical apply는 같은 화면에 있더라도 분리된 단계임을 계속 보여줘야 한다.

결론:
- Phase 4 reference로 강하게 채택.
- Review Queue는 단순 table보다 split detail 방식으로 재설계한다.

### Mouse Detail Mockup

좋은 점:
- reference #2보다 현재 프로젝트 원칙에 더 잘 맞게 source evidence와 audit trace가 포함되어 있다.
- Basic Information, Source Evidence, Genotype, Cage, Timeline, Notes, Audit Trace 구성이 좋다.
- canonical record가 어떤 raw photo, parse, review, candidate를 거쳐 만들어졌는지 보인다.
- field-level provenance를 표시하기 좋은 구조다.

개선할 점:
- header에서 어떤 값이 accepted이고 어떤 값이 needs review인지 더 강하게 표시해야 한다.
- ear label처럼 review가 필요한 필드는 card 내부에서도 warning 상태가 필요하다.
- Audit Trace는 상세 화면 하단에 두되, 필요하면 drawer로 열 수 있어야 한다.

결론:
- Phase 6 reference로 채택.
- Mouse Detail은 source-aware detail view로 구현한다.

### Strain Detail Mockup

좋은 점:
- reference #3의 network 중심 구성을 잘 유지하면서 evidence layer를 추가했다.
- raw source, parsed/intermediate, review, candidate, canonical legend가 좋다.
- strain-level open reviews가 시각적으로 드러난다.
- related reviews와 quick reference가 실무적으로 유용하다.

개선할 점:
- genotype distribution category는 hard-code하지 않고 configurable master에서 와야 한다.
- network edge는 reviewed evidence와 pending/unreviewed evidence를 더 엄격히 구분해야 한다.
- radar score는 review aid일 뿐 canonical state가 아니라는 문구를 유지해야 한다.

결론:
- Phase 7 reference로 채택.
- Strain Detail은 genotype/strain normalization이 어느 정도 안정된 뒤 구현한다.

## Updated Implementation Priority

생성 이미지를 검토한 뒤 우선순위를 다음처럼 조정한다.

1. App shell: sidebar, topbar, view container.
2. Photo Review Workbench: raw photo preview 중심의 첫 화면.
3. Review Queue split detail: review resolution을 실제 업무 화면으로 승격.
4. Evidence Comparison decision table + evidence inspector.
5. Export Readiness panel: blockers, filenames, export log.
6. Mouse Detail source-aware view.
7. Strain Detail evidence network view.
8. Colony Dashboard accepted-state operational view.

핵심 변경:
- 기존 계획에서는 Evidence Comparison을 Review Queue보다 먼저 개선하는 순서였지만, 생성 mockup 검토 후 Review Queue split detail을 더 앞당긴다.
- 이유는 실제 사용자 행동이 “차이를 발견한다”보다 “리뷰를 해결한다”에 더 오래 머무르기 때문이다.
- Photo Review Workbench와 Review Queue가 안정되면 Evidence Comparison은 자연스럽게 decision support view가 된다.

## Updated Next Step

다음 구현은 Phase 1-2에 Phase 4의 일부를 섞어 진행한다.

Scope:
- sidebar/topbar shell 추가.
- Photo Review Workbench를 default view로 배치.
- Review Queue를 list/detail split layout으로 재배치하되, 기존 resolve API를 그대로 사용.
- Evidence Comparison은 우선 현재 table을 유지하고, selected row inspector는 다음 phase로 넘긴다.

Non-goals:
- Mouse Detail 전체 구현.
- Strain Detail network 구현.
- Dashboard chart 전체 구현.
- 새로운 canonical schema 추가.
- 자동 OCR 또는 외부 inference 연동.

Verification:
- 기존 `python scripts/verify-local-app.py` 유지.
- 기존 `npm run verify` 유지.
- desktop screenshot으로 Photo Review Workbench 확인.
- open review blocker가 final export를 계속 막는지 확인.
- raw photo, manual transcription, comparison view에서 canonical write가 발생하지 않는지 확인.
