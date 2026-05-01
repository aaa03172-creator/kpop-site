# MouseDB CLI-First 설계 리뷰

## Document Status

Layer classification: design review / non-canonical project note.

이 문서는 MouseDB를 PaperPipe 및 개인 Research Assistant와 나중에 연결하기 위한 CLI-first 설계안을 검토하고, 현재 mouse colony 프로젝트 문서에 반영할 권장 원칙을 정리한다. Canonical 제품 요구사항은 계속 `final_mouse_colony_prd.md`를 따른다.

## 검토 대상 요약

MouseDB는 strain, allele, genotype, mouse 개체, cage, mating, litter, mouse event를 관리하는 독립형 도구로 제안되었다.

장기 구조:

- PaperPipe: 논문, 문헌, method 파이프라인
- MouseDB: strain, colony, mouse 개체 관리 시스템
- Research Assistant: PaperPipe와 MouseDB를 호출하는 control layer

핵심 방향은 적절하다. MouseDB는 PaperPipe 내부 모듈이 아니라 독립 도구로 개발하고, 초기에는 Python, SQLite, Typer 기반 CLI로 시작하되 나중에 API 또는 MCP server로 감쌀 수 있게 설계하는 것이 좋다.

## 좋은 설계 결정

- Strain과 Mouse를 분리한다.
- Mouse 테이블은 현재 상태 중심으로 가볍게 유지한다.
- 자세한 개체 이력은 MouseEvent에 쌓는다.
- 모든 주요 CLI 명령은 `--json` 출력을 지원한다.
- PaperPipe와 직접 결합하지 않고 Research Assistant가 control layer에서 호출한다.
- 삭제보다 archive/status 변경을 우선한다.
- MVP와 non-goals가 분리되어 있어 웹앱 과확장을 막는다.
- 자동 이벤트 생성 규칙을 초기에 명시해 timeline과 auditability의 기반을 만든다.

## 주요 보완 권장안

### 1. 데이터 경계를 명확히 유지한다

MouseDB가 순수 CLI 도구로 시작하더라도 이 프로젝트의 핵심은 cage card photo, Excel row, OCR/parse result, review, correction, canonical state의 경계를 보존하는 것이다.

새 테이블, 파일, 출력 shape를 추가할 때는 다음 중 하나로 분류한다.

- raw source
- parsed or intermediate result
- canonical structured state
- review item
- event history
- export or view
- cache

경계가 애매하면 canonical이 아닌 것으로 취급한다.

### 2. Source/evidence traceability를 MVP부터 심는다

모든 중요한 canonical record와 event는 가능하면 원천 evidence로 거슬러 올라갈 수 있어야 한다.

권장 최소 필드:

```text
source_type
source_id
source_label
confidence
reviewed_status
raw_value
normalized_value
```

예:

```json
{
  "event_type": "moved",
  "source_type": "cli",
  "source_id": null,
  "confidence": 1.0,
  "reviewed_status": "accepted"
}
```

사진, Excel import, genotyping sheet에서 온 값은 source photo, note item, imported Excel row로 trace 가능해야 한다.

### 3. MouseEvent를 더 auditable하게 만든다

기본 MouseEvent 필드에 다음을 추가하는 것을 권장한다.

```text
source_type
source_id
confidence
reviewed_status
previous_value
new_value
```

MouseEvent는 append-only history에 가깝게 운용한다. correction이나 inferred state change는 조용히 기존 값을 덮어쓰기보다 before/after가 남는 correction event 또는 correction log로 표현한다.

### 4. 상태 변경과 이벤트 생성은 같은 transaction으로 처리한다

다음과 같은 명령은 반드시 하나의 database transaction 안에서 처리해야 한다.

- `cage move-mouse`: Mouse.current_cage_id 업데이트 + moved event 생성
- `genotype record`: GenotypeResult 생성 + genotyped event 생성
- `mating create`: Mating 생성 + paired event 생성
- `litter create`: Litter 생성 + litter_produced event 생성
- `mouse update --status sacrificed`: status 변경 + sacrificed event 생성

원칙:

```text
State-changing commands that update current structured state and create MouseEvent records must run in a single database transaction. Partial writes are not allowed.
```

### 5. GenotypeResult와 current_genotype_summary를 분리한다

`Mouse.current_genotype_summary`는 사람이 보기 좋은 display/cache/view로 취급한다. genotype의 source of truth는 `GenotypeResult` row이다.

MVP에서는 `experiment-ready --genotype "PV-Cre+"` 같은 문자열 검색을 허용할 수 있지만, 내부적으로는 나중에 allele/result/zygosity 조건 검색으로 확장 가능해야 한다.

권장 문장:

```text
current_genotype_summary is a derived display field, not the authoritative genotype source.
GenotypeResult rows are the source of truth for genotype calls.
```

### 6. Controlled vocabulary는 중앙화하고 교체 가능하게 둔다

status, allele type, genotype category, event type을 코드 곳곳에 흩뿌리면 안 된다.

MVP에서는 Python enum 또는 constants로 시작할 수 있지만, 다음 조건을 지켜야 한다.

- 한 곳에 모은다.
- fixture/seed/config로 교체 가능하게 둔다.
- 특정 strain name, genotype category, protocol, date rule은 hard-code하지 않는다.
- 장기적으로 DB-backed `ControlledVocabulary` 또는 master table로 옮길 수 있게 한다.

### 7. 외부 ID는 안정적이고 재사용하지 않는다

내부 numeric id와 외부 user/tool-facing id를 분리하는 방향은 좋다.

권장 외부 ID:

```text
Strain: STR-0001
Gene: GENE-0001
Allele: AL-0001
Mouse: M-2026-0001
Cage: C-001
Mating: MAT-2026-001
Litter: LIT-2026-001
Event: EVT-2026-0001
GenotypeResult: GT-2026-0001
```

추가 원칙:

- 외부 ID는 unique indexed field로 둔다.
- archive된 record의 ID를 재사용하지 않는다.
- ID 생성은 `utils/ids.py` 같은 단일 모듈에서만 수행한다.
- seed/demo에서는 deterministic ID가 필요할 수 있으므로 정책을 명시한다.

### 8. Delete보다 archive를 기본 사용자 동작으로 둔다

CLI에서 destructive delete를 일반 workflow로 노출하지 않는 편이 좋다.

권장 명령:

```text
mousedb strain archive STR-0001
mousedb mouse archive M-2026-0231
mousedb cage archive C-014
```

삭제가 필요하더라도 개발/maintenance 전용 명령으로 분리하고, 기본 문서에서는 archive/status 변경을 권장한다.

### 9. Experiment-ready search는 review 상태와 warning을 포함한다

실험 후보 검색은 단순히 조건에 맞는 mouse를 찾는 것에서 끝나면 안 된다. genotype pending, inconclusive, low-confidence source, unresolved review item, biologically unlikely conflict가 있으면 후보 결과에 표시해야 한다.

권장 JSON shape:

```json
{
  "mouse_id": "M-2026-0231",
  "eligibility": "candidate",
  "warnings": []
}
```

나중에 제외된 개체까지 보고 싶을 때:

```text
mousedb experiment-ready ... --include-excluded --json
```

### 10. Service layer를 CLI보다 중요하게 둔다

나중에 API/MCP로 감싸려면 CLI가 business logic을 직접 가지면 안 된다.

권장 흐름:

```text
CLI -> schemas/input validation -> services -> repositories -> models/db
```

나중에는 같은 service layer를 다음처럼 재사용한다.

```text
MCP/API -> schemas/input validation -> services -> repositories -> models/db
```

### 11. Migration 전략을 명시한다

개인 도구 MVP에서는 `metadata.create_all()`로 시작할 수 있지만, mouse colony data는 장기 데이터가 쌓이는 도구이므로 schema migration 전략이 필요하다.

권장:

- 아주 작은 prototype: `mousedb init`에서 table 생성
- 실사용 MVP: Alembic migration 도입

최소한 README에 schema version과 migration/upgrade 방향을 명시한다.

## 현재 프로젝트 문서에 반영할 핵심 문장

다음 문장들은 Codex 또는 구현자에게 강하게 제시할 가치가 있다.

```text
Do not build a large web application yet.
Build a clean, testable, CLI-first MouseDB core that can later support the web app, API, or MCP server.
The CLI JSON output is a public contract.
Every important command must support --json output.
Do not hard-code PaperPipe integration.
Design MouseDB as an independent tool that can later be wrapped by API or MCP.
Keep Mouse records lightweight and store detailed history in MouseEvent.
All state-changing commands must preserve traceability and should create MouseEvent records when they change mouse-relevant state.
MouseEvent is append-only by default.
Corrections should preserve previous/new values instead of silently rewriting history.
```

한국어 요약:

```text
지금은 거대한 웹앱을 먼저 만들지 말고,
나중에 PaperPipe/Research Assistant가 호출할 수 있는
깔끔한 CLI-first MouseDB core를 만들어라.

MouseDB는 독립 도구로 유지하고,
모든 주요 명령은 stable JSON 출력을 지원해야 한다.

Mouse 테이블은 가볍게 유지하고,
자세한 이력은 MouseEvent에 쌓는다.

상태 변경은 source evidence, before/after, event history를 남기며
partial write 없이 transaction으로 처리한다.
```

## 권장 반영 위치

- `final_mouse_colony_prd.md`: Research Assistant / MouseDB 독립 도구 방향, CLI JSON contract, event/transaction/traceability 원칙
- `mvp_vertical_slice_plan.md`: 구현 순서에 service layer, transaction, stable JSON, evidence fields 추가
- `reference_adoption_notes.md`: PaperPipe는 직접 결합하지 않고 Research Assistant control layer에서 호출한다는 통합 방향
- 미래 `README.md`: CLI command contract, JSON examples, demo workflow, non-goals

## 결론

MouseDB CLI-first 설계안은 방향이 좋다. 다만 실험실 데이터 도구답게 evidence, review, transaction, append-only event 원칙을 MVP부터 넣어야 한다.

가장 중요한 반영 사항:

1. source/evidence traceability 필드 추가
2. 상태 변경 + MouseEvent 생성은 single transaction
3. MouseEvent는 append-only history에 가깝게 운용
4. `current_genotype_summary`는 view/cache이고 `GenotypeResult`가 source of truth
5. CLI JSON 출력은 나중에 Research Assistant/MCP가 의존할 public contract로 취급
