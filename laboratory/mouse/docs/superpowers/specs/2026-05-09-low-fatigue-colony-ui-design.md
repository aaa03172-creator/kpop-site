# Low-Fatigue Colony UI Design

## Document Status

Layer classification: design guidance / non-canonical product documentation.

Data boundary: this document defines UI responsibility, review visibility, and information hierarchy rules. It does not define canonical database tables, final API response shapes, or export schemas.

Canonical status: non-canonical. Canonical behavior remains governed by `final_mouse_colony_prd.md`, `AGENTS.md`, and adopted project documents. If this document conflicts with canonical product rules, call out the mismatch before implementation.

## Design Goal

The mouse colony app should preserve rich evidence while showing the user only the information needed for the current decision.

The database may store photos, OCR text, note lines, normalized values, review decisions, card snapshots, mouse records, events, and Excel export history. The default UI should not require the user to inspect all of that at once.

The primary UX goal is:

> Make the next action obvious, reduce fatigue, and preserve traceability.

## Adoption Decisions From Product Review

Adopt now:

- photo-first cage card review;
- mouse ID centered tracking;
- card snapshots with multiple mouse rows;
- accepted event history;
- configurable strain, genotype, and date rules;
- low-fatigue review levels;
- in-app colony schedule;
- Excel-like export preview;
- evidence ledger with source photos as primary evidence.

Adopt as optional or phased follow-up:

- Google Calendar sync as an external mirror for selected schedule tasks;
- related mice and simple pedigree panel;
- multi-generation pedigree graph;
- richer task notifications;
- generated labels or printed cards after the handwritten workflow is stable.

Do not adopt for the initial direction:

- barcode or QR code workflows as a required input path;
- printed cage-card-first workflows;
- external calendar as source of truth;
- direct canonical database editing inside an Excel-like grid;
- AI breeding recommendations as a core MVP workflow;
- facility-wide billing, per-diem, rack/room enterprise operations;
- large analytics dashboards that expose every warning by default.

## Core Model

### Cage Card As Source Snapshot

A cage card photo is not a single mouse record.

One handwritten cage card can include multiple mouse rows, note-line IDs, mating or litter notes, and inferred state changes. The UI should treat it as:

- raw source photo;
- card snapshot observed at a point in time;
- review grouping unit;
- source for one or more mouse rows;
- source for proposed events.

### Mouse ID As Continuity Unit

Mouse ID is the main continuity anchor.

Mouse detail, current status, and timeline views should center on the mouse display ID and its accepted event history. Cage card snapshots appear as evidence links in that history, not as the durable identity of the mouse.

### Accepted State Vs Proposed State

The UI must keep proposed or uncertain changes separate from accepted colony state.

- `Focus Review` shows proposed, uncertain, conflicting, or biologically unlikely items.
- `Colony State` shows accepted current state and small anomaly badges.
- `Colony Schedule` shows accepted and derived colony tasks by due timing.
- `Mouse Timeline` shows accepted events by default.
- `Related Mice` or `Pedigree` shows family and breeding relationships derived from accepted events.
- `Evidence Ledger` shows source evidence and trace links.
- `Excel Export` shows whether accepted state is exportable.

## Information Visibility Rules

### Must Review

Show by default in `Focus Review`.

Use for records that block canonical state changes or export until the user decides:

- duplicate active mouse ID;
- same mouse ID tied to conflicting active cage/card records;
- missing or conflicting sex/count where it affects colony state;
- strain not matched to configured assigned-strain or strain master;
- biologically unlikely date or event order;
- unreadable source photo or crop that prevents reliable extraction;
- proposed event that would overwrite high-risk accepted state.

### Quick Check

Show in `Focus Review`, but visually lighter than `Must Review`.

Use for records that need quick confirmation but should not look like serious errors. The user-facing helper text should emphasize action, such as `Needs quick confirmation`, rather than broad risk language such as `Low risk`.

- uncertain sex or count when source evidence is mostly present;
- normalized DOB missing while raw DOB is preserved;
- note-line interpretation needs selection;
- low-risk assigned-strain alias match;
- LMO or checkbox-style marks that need bounded interpretation.

### Trace Only

Hide by default from decision queues.

Use for uncertainty that should remain traceable but usually does not require immediate user action:

- accepted exact alias match with source retained;
- raw DOB present while normalized DOB is deferred;
- source photo and OCR retained for audit;
- already superseded extraction results;
- prior Excel row used only as import/export reference.

### Hidden By Default

Keep out of normal lab workflow screens unless the user opens diagnostics or developer views:

- fixture/sample records;
- cache artifacts;
- repeated internal validation artifacts;
- stale exports that are not relevant to current export readiness;
- low-level parser diagnostics.

## Page Responsibilities

### Focus Review

Question answered: `What needs my decision today?`

This is the only page that should show detailed decision work.

Default unit: card-level grouped review.

Each expanded card review should show:

- source photo/card identifier;
- source photo preview with clear zoom/open affordance;
- card date or observed date if available;
- review level: `Must Review`, `Quick Check`, or `Trace Only`;
- reason summary;
- `Mouse rows` table with one row per parsed mouse or note-line mouse candidate;
- row-level status and issue;
- card-level action when applicable;
- collapsed evidence sections.

Recommended row fields:

- mouse display ID;
- strain;
- sex;
- DOB;
- current status candidate;
- issue;
- row action.

Recommended row actions:

- `Confirm`;
- `Correct`;
- `Resolve conflict`;
- `Send to review`;
- `Dismiss with reason`.

Recommended card-level actions:

- `Apply confirmed rows only`;
- `Hold card`;
- `Open source photo`;
- `View proposed events`.

Collapsed sections:

- `Evidence`;
- `Raw OCR`;
- `Note lines`;
- `Proposed events`;
- `Review history`.

Rule: if a card has multiple mouse rows and only one row is problematic, highlight only the problematic row. Do not make the entire card look equally dangerous unless the card-level source itself is unreliable.

Rule: `Trace Only` counts should not appear as primary workload. They may be available as a filter or secondary status, but the default workload summary should emphasize `Must Review` and `Quick Check`.

Rule: the source photo should not feel decorative. In review contexts, it is primary evidence and should be large enough to inspect or one click away from a zoomed view.

Rule: row-level issue labels and suggested decision summaries should not repeat the same text at the same weight. If both are shown, the row should state the issue and the lower summary should explain why it matters or what resolution is proposed.

### Colony State

Question answered: `What is active now?`

This page shows accepted current colony state. It should not repeat the review queue.

Show by default:

- active cages/cards count;
- active mouse count;
- current strain/status grouping;
- accepted active card or cage rows;
- small anomaly badges such as `2 conflicts` or `1 DOB gap`;
- links to `Focus Review` for unresolved issues.

Do not show by default:

- detailed blocker lists;
- raw OCR;
- all source evidence;
- proposed event details;
- review decision controls.

Rule: `Colony State` can indicate that something needs attention, but the actual decision belongs in `Focus Review`.

Rule: top-level state numbers should stay realistic and modest in sample data. The page should feel like an operational current-state view, not an inflated analytics dashboard.

### Colony Schedule

Question answered: `What needs to happen when?`

This page or panel shows dated colony work derived from accepted events and configured rules. It should make separation, weaning, genotyping, mating checks, and follow-up work visible without turning the product into a noisy calendar dashboard.

Default layout:

- `Due now`;
- `Due soon`;
- `Later`;
- optional calendar view;
- compact optional Google Calendar sync status.

Task examples:

- separation or weaning due;
- genotype due;
- mating check due;
- litter expected;
- litter recorded follow-up;
- breeder retirement or refresh check;
- cage card photo follow-up;
- Excel export due or stale;
- high-priority review deadline.

Each schedule task should show:

- task type;
- due date;
- recorded source date when relevant;
- affected mouse IDs, litter, mating, or card snapshot;
- current task status;
- source event;
- due-date rule used;
- evidence link.

Task statuses:

- `due_now`;
- `due_soon`;
- `later`;
- `overdue`;
- `blocked_by_review`;
- `done`;
- `dismissed_with_reason`.

Rules:

- schedule tasks are derived from accepted colony events and configurable rules, not from hard-coded date logic;
- task due dates should be traceable back to a source event, rule, and evidence;
- schedule detail should make recorded dates and due dates easy to compare, for example `Recorded separation: 2025-02-24` and `Next action due: 2025-03-10`;
- proposed or low-confidence dates should go through `Focus Review` before creating required schedule tasks;
- the default view should be a workload list, not a dense month calendar;
- external calendar sync should be visually secondary to the in-app due list.

### Mouse Timeline

Question answered: `How did this mouse get here?`

This page centers on one mouse display ID and its accepted durable history.

Show by default:

- mouse ID;
- current accepted status;
- strain;
- sex;
- DOB;
- genotype status;
- current card/cage reference;
- accepted event timeline.

Timeline events may include:

- born;
- separated;
- moved;
- genotyped;
- assigned to mating;
- litter recorded;
- dead;
- used;
- closed.

Each event should link to evidence but not expand raw evidence by default.

Rule: proposed events should remain in `Focus Review` until accepted. If timeline needs to show them, they must be clearly labeled as proposed and visually separated from accepted events.

Rule: links from `Mouse Timeline` to `Evidence Ledger` should be labeled as evidence links, such as `Open supporting evidence`. The timeline itself remains the home for chronological event history.

### Related Mice And Pedigree

Question answered: `How is this mouse related to other mice?`

This should begin as a tab or panel within `Mouse Timeline`, not as a large standalone graph in the first version.

Show by default:

- sire if known;
- dam if known;
- litter siblings;
- offspring;
- related mating records;
- genotype/strain summary;
- uncertain relationship status where applicable;
- evidence links for relationship claims.

Later expansion may add a multi-generation pedigree graph, but the first version should prioritize readable immediate relationships over a complex visualization.

Rules:

- pedigree relationships should be derived from accepted mating, litter, and parent-child events;
- inferred or uncertain parentage should be reviewable and visually distinct from accepted relationships;
- evidence should remain linked, but raw OCR or photo details should not be expanded by default.

### Evidence Ledger

Question answered: `Where did this value come from?`

This page is the evidence search and audit surface.

It should support two modes:

- related evidence for the current mouse, card, review item, or export row;
- all evidence search.

Evidence records may include:

- source photo;
- ROI/crop;
- OCR text;
- parsed note line;
- imported Excel row;
- review decision;
- proposed changeset;
- accepted event;
- export manifest.

Trace status labels:

- `Linked`;
- `Pending`;
- `Superseded`;
- `Rejected`;
- `Exported`.

Rule: source photo should remain visually primary when evidence is related to a card/photo review. OCR, note lines, and Excel rows are supporting evidence, not replacements for the raw photo.

Rule: imported Excel rows should be visually treated as import/export views. They should not appear to outrank source photos or accepted events as evidence.

### Excel Export

Question answered: `Can I export now?`

This page shows export readiness and an Excel-like workbook preview generated from accepted state.

The preview should look close enough to the lab's familiar workbook formats that the user can recognize what will be exported. It is still an export/view surface, not a canonical editing surface.

Show by default:

- export readiness;
- ready row count;
- rows to create;
- rows to update;
- workbook/template tabs such as `Separation workbook`, `Animalsheet`, or configured export templates;
- Excel-like grid preview with familiar columns and row groupings;
- row-level export status chips such as `New`, `Update`, `No change`, and `Blocked`;
- lightweight source or evidence links per row;
- stale export warning if applicable;
- short blocker summary.

Blocker summary should not repeat detailed review information. Use a link such as `Open Focus Review`.

The export action should remain disabled while unresolved `Must Review` or required `Quick Check` items block export.

Rules:

- the grid is a preview of the file to be exported, not the primary place to edit canonical state;
- downloading a preview may be allowed while export is blocked if it is clearly labeled as a review-only preview;
- final export remains disabled until required review blockers are resolved;
- cell or row clicks may open a side drawer with source/evidence summary;
- blocked rows should be visible in the grid, but detailed resolution should link to `Focus Review`;
- evidence links should go to `Evidence Ledger`;
- export preview is generated from accepted mouse/event state, not directly from raw card rows;
- raw card rows remain evidence until reviewed or accepted.

## Optional Calendar Integration

Google Calendar or another external calendar may be used as a mirror for selected colony schedule tasks.

The app's database remains the source of truth. External calendar events are reminders and visibility aids, not canonical colony records.

Recommended flow:

1. Accepted colony event is recorded.
2. Configured rule derives a schedule task.
3. The task appears in `Colony Schedule`.
4. If enabled, the task syncs to an external calendar event.
5. Sync status and external event metadata are stored.

Calendar sync statuses:

- `not_synced`;
- `synced`;
- `sync_failed`;
- `changed_externally`;
- `deleted_externally`;
- `disabled`.

Rules:

- calendar event titles and descriptions should minimize payloads;
- do not send full OCR text, full cage card data, or unnecessary genotype details to external calendars;
- use a stable internal task identifier in external event metadata when supported, so repeated sync does not create duplicates;
- changes in the external calendar should not silently overwrite accepted colony state;
- external edits may update reminder timing or mark a sync conflict, but colony data changes should return to the app review/correction flow;
- Google Calendar integration should be optional and can follow the in-app schedule implementation.
- calendar sync UI should be compact. It should communicate sync state without making the external calendar look like the main workflow.

Example calendar event titles:

- `Weaning due: C-12 / 3 mice`;
- `Mating check: C-8`;
- `Genotype pending: MT319 litter`;
- `Review needed before Excel export`.

Relevant Google Calendar concepts:

- event creation;
- reminders;
- private extended properties for app metadata.

## Cross-Page Duplication Rules

Avoid repeating the same detail at the same depth on multiple pages.

Allowed repetition:

- status badges;
- small source chips;
- counts;
- links to the responsible page;
- one-line summaries.

Not allowed by default:

- full blocker detail outside `Focus Review`;
- full raw evidence outside `Evidence Ledger`;
- proposed event decisions outside `Focus Review`;
- export readiness widgets on non-export pages;
- review decision controls on accepted-state pages.

## Interaction Pattern

Use progressive disclosure:

1. Show the next required action.
2. Show the affected card or mouse.
3. Show only the problematic row by default.
4. Keep evidence collapsed.
5. Let the user expand evidence, OCR, note lines, proposed events, and review history on demand.

The interface should feel calm by default. Red and amber indicators should be reserved for items that truly require attention.

## UI Element Implementation Notes

### App Shell And Navigation

Purpose: keep the main workflow stable and predictable.

Implementation:

- use a persistent left navigation with the primary workflow order: `Focus Review`, `Colony State`, `Colony Schedule`, `Mouse Timeline`, `Evidence Ledger`, `Excel Export`;
- keep settings and diagnostics visually lower than daily lab work;
- preserve the selected entity context when navigating, such as selected mouse ID, card snapshot, or review item;
- use route parameters or query state for deep links, for example a blocked export row can open the matching `Focus Review` item.

Convenience and polish:

- show small count badges only where they imply action;
- avoid showing `Trace Only` as a daily workload badge;
- support keyboard shortcuts for next/previous review item after the basic workflow is stable;
- keep sidebar labels in lab language, not implementation language.

### Summary Cards And Status Chips

Purpose: give the user quick orientation without creating dashboard fatigue.

Implementation:

- summary cards should answer the page question, not repeat every global metric;
- use compact chips for `Must Review`, `Quick Check`, `Blocked`, `Linked`, `Pending`, `Superseded`, `Accepted`, `New`, `Update`, and `No change`;
- keep chip color semantics stable across pages.

Convenience and polish:

- make red mean blocking action is required;
- make amber mean short confirmation or pending attention;
- make green mean accepted, linked, or ready;
- avoid large numeric cards when a small badge or row label is enough.

### Source Photo Viewer

Purpose: make raw handwritten evidence inspectable without overwhelming the page.

Implementation:

- show the source photo prominently in `Focus Review`;
- provide zoom in, zoom out, rotate, fit-to-card, and open-fullscreen controls;
- support side-by-side comparison with parsed mouse rows when space allows;
- preserve photo metadata such as source filename, capture/import time, card date, and extraction time;
- allow ROI overlays later, but keep them optional and toggleable.

Convenience and polish:

- remember zoom and rotation per review session;
- use a loupe or split zoom preview for small handwriting;
- keep image loading skeletons stable so tables do not jump;
- warn if the source photo is too blurry, cropped, or missing the note area.

### Card-Level Review Group

Purpose: review one source card/photo as a coherent unit while allowing row-level decisions.

Implementation:

- represent each card as an expandable review group;
- show `Mouse rows` inside the card group with one row per parsed mouse or note-line mouse candidate;
- keep row actions separate from card actions;
- card-level actions should include `Apply confirmed rows only`, `Hold card`, and `Open source photo`;
- only confirmed row changes may be applied when unresolved rows remain.

Convenience and polish:

- highlight only the problematic row, not the whole card, unless the source card itself is unreliable;
- show a card progress indicator such as `2 confirmed, 1 unresolved`;
- explain suggested decisions as `why this matters` or `proposed resolution`, not as a duplicate of row labels;
- prevent accidental high-risk apply actions with a confirmation step that lists affected mouse IDs.

### Mouse Rows Table

Purpose: make multi-mouse cage cards clear and actionable.

Implementation:

- table columns should include mouse display ID, strain, sex, DOB, current status candidate, issue, and action;
- use inline row chips for `Duplicate active`, `Quick Check`, `Confirmed`, or `Needs correction`;
- keep internal record IDs hidden unless the user opens debug details;
- let row clicks open a focused detail drawer with raw/normalized field comparison.

Convenience and polish:

- keep row height compact but readable;
- pin the mouse ID and issue columns on wide tables if horizontal scrolling appears;
- use bounded selectors for normalized sex, card type, LMO, note-line interpretation, genotype status, and assigned strain;
- preserve before/after values whenever the user corrects a row.

### Collapsible Evidence Sections

Purpose: preserve traceability while keeping default screens calm.

Implementation:

- use accordion sections for `Evidence`, `Raw OCR`, `Note lines`, `Proposed events`, and `Review history`;
- show counts in the accordion header;
- lazy-load heavier evidence data only when expanded;
- keep expansion state local to the current review session.

Convenience and polish:

- include one-line previews in headers only when useful, such as `3 note lines`;
- allow `Open in Evidence Ledger` from each section;
- avoid expanding multiple dense evidence sections automatically after an action;
- use empty states that explain absence, such as `No proposed events from this card`.

### Detail Drawer

Purpose: let the user inspect detail without losing their place.

Implementation:

- use a right-side drawer for row details, schedule task details, export row details, and evidence summaries;
- include source links, raw value, normalized value, confidence, before/after, and proposed action when relevant;
- support direct navigation to the full page when the drawer is not enough.

Convenience and polish:

- keep the underlying list visible;
- make drawer close behavior predictable;
- avoid modals for routine inspection;
- use modals only for destructive or high-risk confirmation.

### Colony State Tables

Purpose: show accepted current state without becoming the review queue.

Implementation:

- show accepted active card snapshots and active mouse counts;
- use links to `Focus Review` for anomalies, not embedded review controls;
- provide filters for strain, status, and assigned scope;
- show source card chips as compact links only.

Convenience and polish:

- keep sample and production counts realistic;
- use saved filters for assigned strains or active-only views;
- offer search by mouse ID, card snapshot, strain, and DOB;
- show stale-state warnings when accepted state depends on unresolved review blockers.

### Colony Schedule Task Cards

Purpose: make time-based work visible and traceable.

Implementation:

- group schedule tasks by `Due now`, `Due soon`, and `Later`;
- each task should include due date, recorded source date when relevant, affected mouse IDs or card snapshot, source event, rule used, status, and evidence link;
- detail drawers should compare recorded date and due date;
- external calendar sync state should be secondary to the task content.

Convenience and polish:

- include quick filters for task type, assigned strain, and overdue status;
- let users mark a task done only when the corresponding accepted event exists or is created through review/correction flow;
- allow dismissing a task only with a reason;
- show `blocked_by_review` when a task depends on unresolved source data.

### Optional Calendar Sync UI

Purpose: mirror selected schedule tasks externally without making the external calendar canonical.

Implementation:

- show compact sync status such as `Calendar mirror: synced`;
- store sync status and external event metadata per task;
- provide retry for `sync_failed`;
- treat `changed_externally` and `deleted_externally` as sync conflicts, not silent colony-state changes.

Convenience and polish:

- let the user choose which task categories sync externally;
- minimize event payloads in titles and descriptions;
- avoid sending full OCR text, full cage card data, or unnecessary genotype details;
- provide a preview of the external calendar title before enabling sync.

### Mouse Timeline

Purpose: explain how a mouse reached its current accepted state.

Implementation:

- show accepted events by default;
- label the view `Accepted events only`;
- keep event rows scannable with date, event type, short summary, and evidence link;
- use `Open supporting evidence` for Evidence Ledger links.

Convenience and polish:

- support filtering by event type;
- allow compact and expanded timeline density;
- show proposed events only in a clearly separated area if the user explicitly opens them;
- link from each event to related card snapshot, mating, litter, or genotype record.

### Related Mice And Pedigree Panel

Purpose: show immediate biological relationships without overwhelming the timeline.

Implementation:

- start with sire, dam, siblings, offspring, and related mating records;
- show uncertain relationships with a distinct pending/review style;
- derive accepted relationships from accepted mating, litter, and parent-child events;
- keep the multi-generation graph as a later enhancement.

Convenience and polish:

- make each related mouse chip clickable;
- show sex, strain, and status where useful;
- avoid dense graph layouts in the default view;
- provide a clear `View family tree` path when a graph exists later.

### Evidence Ledger

Purpose: make source traceability searchable and auditable.

Implementation:

- split the page into related evidence and all evidence search;
- make source photos visually primary for card/photo-derived values;
- label Excel rows as `import view` or `export view`;
- support trace status filters: `Linked`, `Pending`, `Superseded`, `Rejected`, and `Exported`.

Convenience and polish:

- provide entity filters for mouse, card snapshot, review item, export row, and event;
- show why evidence is pending or superseded;
- allow opening source photo, OCR text, note line, or Excel row in a detail drawer;
- avoid making OCR or Excel rows look more authoritative than source photos and accepted events.

### Excel-Like Export Preview

Purpose: let the user recognize the exported workbook before generating it.

Implementation:

- use tabs for export templates such as `Separation workbook`, `Animalsheet`, and `Genotyping sheet`;
- render a spreadsheet-like grid with familiar columns and row groupings;
- show row status chips: `New`, `Update`, `No change`, and `Blocked`;
- link each row to evidence or review;
- keep final export disabled while required blockers remain.

Convenience and polish:

- allow `Download preview` only as a clearly labeled review-only preview when blocked;
- show `Preview only: canonical data cannot be edited here`;
- support column settings for hiding optional columns without changing the template;
- let blocked rows jump directly to the responsible `Focus Review` item;
- keep grid scrolling smooth and preserve column widths across tabs.

### Empty, Loading, And Error States

Purpose: reduce confusion when data is missing, still parsing, or blocked.

Implementation:

- show parsing states separately from review states;
- distinguish no data from hidden-by-filter;
- for partial failures, show what was saved and what still needs review;
- never silently discard source photos or review decisions.

Convenience and polish:

- use short, actionable empty states;
- keep retry buttons close to the failed operation;
- show stale export warnings before the user downloads;
- preserve user-entered corrections if a save fails.

### Accessibility And Ergonomics

Purpose: keep repeated review work comfortable.

Implementation:

- ensure badges do not rely on color alone;
- provide visible focus states;
- support keyboard navigation in review queues and grids;
- keep contrast high enough for small table text;
- avoid tiny click targets in row actions.

Convenience and polish:

- use consistent row action placement;
- avoid layout shifts when evidence loads;
- make destructive or high-risk actions reversible or explicitly confirmed;
- remember filters and sort choices per user where appropriate.

## Visual Design And State Cues

### Visual Priority System

Purpose: make urgency visible without making the whole product feel alarming.

Rules:

- use red only for blockers that require action before accepted state changes or final export;
- use amber for quick confirmation, pending sync, or low-risk attention;
- use green for accepted, linked, ready, or completed states;
- use gray for trace-only, superseded, disabled, or secondary information;
- do not use color alone to communicate state; pair color with text, icon, or shape.

Implementation:

- reserve the strongest border/background treatment for the currently active item;
- use small chips instead of large colored panels for most statuses;
- keep red badges numerically small and specific, such as `3 blockers`;
- avoid turning every uncertain OCR value into an alert.

### Page-Level Visual Hierarchy

Purpose: make each page answer one question at a glance.

Rules:

- page title should be paired with the page question, for example `Focus Review` and `What needs my decision today?`;
- first row should show only the summary needed for that page;
- primary action should be visually obvious but not oversized;
- secondary links should be quiet text or small outline buttons;
- evidence-heavy content should start collapsed except in `Evidence Ledger`.

Implementation:

- use consistent top spacing, heading size, and control placement across pages;
- avoid hero-scale type inside operational screens;
- avoid nested cards; use tables, panels, drawers, and accordions instead;
- maintain stable dimensions for sidebars, tab bars, icon buttons, chips, and table rows.

### Row And Card Highlighting

Purpose: show exactly where attention is needed.

Rules:

- if one mouse row is problematic, highlight that row, not the entire card;
- if the source photo itself is unreliable, highlight the card-level container;
- if an export row is blocked, show the blocked row and provide a link to the matching review item;
- if a schedule task is blocked by review, show the task as blocked but keep its underlying due date readable.

Implementation:

- use a subtle tinted row background plus left accent line for selected or blocked rows;
- keep warning chips close to the field or row they describe;
- use hover states to reveal row actions only when actions are secondary;
- keep primary row actions visible for `Must Review` rows.

### Motion And Transitions

Purpose: make state changes understandable without adding visual noise.

Rules:

- use short, restrained transitions for accordion expansion, drawer open/close, row apply, and status changes;
- avoid decorative animation and persistent motion;
- never animate source evidence in a way that makes handwriting harder to inspect.

Implementation:

- after `Confirm`, briefly show a row-level saved state and move the row to confirmed position only if it does not disorient the user;
- after `Apply confirmed rows only`, keep unresolved rows visible and show exactly what was applied;
- when a blocker is resolved, update connected badges and export readiness in place;
- use loading skeletons that match final table/card dimensions.

### Density And Spacing

Purpose: keep the app efficient without becoming cramped.

Rules:

- use compact tables for structured state and review rows;
- use more generous spacing around source photos and decision summaries;
- keep schedule cards readable at a glance;
- keep export grid dense enough to resemble a workbook.

Implementation:

- provide comfortable row heights for repeated review work;
- use line clamping for long filenames, OCR snippets, and note text;
- preserve column widths across filters and tabs;
- prevent badge and button text from wrapping awkwardly.

### Icons And Microcopy

Purpose: make routine actions recognizable.

Rules:

- use familiar icons for zoom, rotate, open, filter, settings, calendar sync, evidence link, warning, and export;
- label icon-only controls with tooltips;
- use lab workflow language: photos, cage cards, mouse IDs, mating, litter, genotype, review, Excel export;
- avoid implementation language such as internal IDs or parser state unless the user opens diagnostics.

Implementation:

- use `Open source photo`, not `Open artifact`;
- use `Open supporting evidence`, not `View full timeline in Evidence Ledger`;
- use `Needs quick confirmation`, not `Low risk`;
- use `Preview only`, not `Editable export`.

### Responsive Behavior

Purpose: keep critical workflows usable on narrower screens without flattening all detail.

Rules:

- desktop is the primary review surface;
- tablet/narrow layouts should preserve source photo plus active row context;
- phone layouts may focus on schedule/checklist views before full review workflows.

Implementation:

- collapse left navigation to icons on narrower widths;
- stack source photo above mouse rows when horizontal space is limited;
- convert multi-column schedule to grouped lists on narrow screens;
- keep Excel workbook preview horizontally scrollable rather than collapsing important columns away.

### Visual QA Checklist

Use this checklist before accepting implementation:

- source photo is large enough to inspect or one click from zoom;
- `Must Review` and `Quick Check` are visually distinct;
- `Trace Only` does not look like required work;
- unresolved row, card, task, and export blockers are visually traceable across pages;
- accepted-state pages do not look like review queues;
- external calendar sync appears secondary to in-app schedule;
- Excel preview looks like a workbook but not an editable database;
- evidence links are visible without expanding all raw evidence;
- empty, loading, and error states do not shift layout abruptly;
- color is never the only indicator of status.

## Implementation Notes

Before implementation, map each UI object to a data boundary:

| UI Object | Boundary |
| --- | --- |
| Source photo | raw source |
| OCR text | parsed or intermediate result |
| Parsed mouse row | parsed or intermediate result |
| Card snapshot | canonical structured state only after acceptance |
| Mouse current status | canonical structured state |
| Proposed event | review item / intermediate result |
| Accepted event | canonical structured state |
| Derived schedule task | parsed/intermediate result or review item until explicitly adopted as canonical |
| External calendar event | export or view / external mirror |
| Pedigree relationship | canonical structured state only when derived from accepted events |
| Inferred relationship | review item / intermediate result |
| Review decision | review item / audit evidence |
| Excel-like export grid | export or view |
| Export preview row status | export or view |
| Export manifest | export or view |
| Parser cache | cache |

Default to non-canonical when ambiguous.

## Acceptance Criteria

- A cage card with multiple mouse rows is represented as one card-level review group with row-level issues.
- `Focus Review` is the only page with detailed decision controls.
- `Colony State` shows accepted current state and links to review, not detailed review work.
- `Colony State` uses realistic operational summary numbers and avoids analytics-dashboard inflation.
- `Colony Schedule` shows separation, weaning, genotyping, mating check, and follow-up tasks derived from accepted events and configurable rules.
- Optional calendar sync mirrors selected schedule tasks without making the external calendar canonical.
- Optional calendar sync appears as secondary status, not the main schedule interface.
- `Mouse Timeline` shows accepted events by default.
- `Related Mice` or `Pedigree` starts with immediate accepted relationships: sire, dam, siblings, offspring, and related mating records.
- `Evidence Ledger` can show all evidence or evidence related to a selected mouse/card/review item.
- `Excel Export` shows readiness and an Excel-like workbook preview from accepted state, with only short blocker summaries.
- Excel-like preview rows include status chips and trace links without allowing direct canonical edits.
- Raw source evidence remains accessible from every important value without being expanded by default.
- Low-risk trace information does not appear as required work.
- Fixture/sample/cache diagnostics are hidden from normal lab workflow screens.
