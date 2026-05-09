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
- `Mouse Timeline` shows accepted events by default.
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

Use for records that need quick confirmation but should not look like serious errors:

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

- `Apply accepted rows`;
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
- cell or row clicks may open a side drawer with source/evidence summary;
- blocked rows should be visible in the grid, but detailed resolution should link to `Focus Review`;
- evidence links should go to `Evidence Ledger`;
- export preview is generated from accepted mouse/event state, not directly from raw card rows;
- raw card rows remain evidence until reviewed or accepted.

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
- `Mouse Timeline` shows accepted events by default.
- `Evidence Ledger` can show all evidence or evidence related to a selected mouse/card/review item.
- `Excel Export` shows readiness and an Excel-like workbook preview from accepted state, with only short blocker summaries.
- Excel-like preview rows include status chips and trace links without allowing direct canonical edits.
- Raw source evidence remains accessible from every important value without being expanded by default.
- Low-risk trace information does not appear as required work.
- Fixture/sample/cache diagnostics are hidden from normal lab workflow screens.
