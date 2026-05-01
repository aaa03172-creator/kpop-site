# Mouse Colony Project Agent Guidelines

## Product Principles
- Preserve handwritten cage card photos and related source records as raw evidence.
- Treat Excel files as import/export views, not the only source of truth.
- Keep raw extracted values separate from normalized values.
- Use mouse IDs and note-line evidence as primary continuity anchors.
- Treat cage/card records as snapshots; durable history should be represented as events.
- Do not hard-code strain names, genotype categories, protocols, or date rules.

## Data Boundaries
Before adding or changing a table, file, artifact, or response shape, classify it as one of:

- raw source
- parsed or intermediate result
- canonical structured state
- review item
- export or view
- cache

If the layer is ambiguous, default to non-canonical until the PRD or another adopted project document explicitly defines it as canonical.

## Review Rules
- Do not silently overwrite high-risk data.
- Preserve before and after values for user corrections and inferred state changes.
- Send low-confidence, conflicting, or biologically unlikely records to review.
- Always keep traceability back to a source photo, note item, or imported Excel row.
- Check failure paths for partial writes, orphan records, duplicate records, and stale exports.
- If documentation and implementation differ, call out the mismatch explicitly.

## OCR And Inference Rules
- Store original photos even when image quality is poor.
- Attach confidence scores to parsed fields.
- Keep uncertain OCR values reviewable instead of pretending they are clean.
- Before using any external OCR, LLM, or inference service, minimize payloads and avoid sending unnecessary full records.
- When uncertain whether a payload is safe to send externally, treat it as local-only until the user approves otherwise.

## Implementation Guidance
- Prefer configurable strain, genotype, and rule masters over hard-coded logic.
- Keep internal IDs hidden from the user unless needed for debugging.
- Use user-facing language that matches the lab workflow: photos, cage cards, mouse IDs, mating, litter, genotype, review, and Excel export.
- Add abstractions only when they clarify the domain model or reduce meaningful duplication.
- Keep changes scoped to the current PRD and adopted project documents.

## Git And Worktree Hygiene
- Before development changes, check the current branch and worktree status.
- Do not develop directly on `main` or another shared default branch when a task-specific branch is appropriate.
- For new implementation work, create or switch to a `codex/<task-name>` branch automatically unless the user requests a specific branch.
- If already on a relevant `codex/` branch, continue there instead of creating unnecessary branch sprawl.
- Stage only files that belong to the current task. Do not use broad `git add .` when unrelated files are present.
- Leave unrelated user files and untracked local artifacts untouched.
- Keep generated folders and verification artifacts such as `node_modules/`, screenshots, logs, and temporary files out of commits unless explicitly adopted as source.
- Before commit or push, run the relevant verification command and confirm there are no unintended unstaged changes.

## UI And Workflow Guidance
- Do not replace the lab's handwritten cage-card workflow in the initial product direction.
- Prioritize upload, review, correction, and Excel export flows over broad dashboard decoration.
- Make uncertain states visible and actionable rather than burying them in logs.
- Avoid UX patterns that pressure the user to accept inferred biological or colony-state data without review.
