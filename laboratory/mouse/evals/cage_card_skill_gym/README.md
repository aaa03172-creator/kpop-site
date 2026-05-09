# Cage Card Skill Gym

Layer classification: review item / test fixture. Canonical: false.

This is a tiny Ctx2Skill-lite harness for MouseDB. It keeps only the useful part of Ctx2Skill: stable probes, binary checks, and cross-time replay pressure. It does not modify product runtime, database schema, API contracts, `AGENTS.md`, or any future project Skill.md.

The probes are deliberately about cage-card workflow safety, not paper reading:

- source photo and ROI grounding
- Excel import/export-view interpretation
- raw evidence versus normalized value separation
- note-line and event reconstruction
- limitation and uncertainty detection
- local reproducibility
- source photo, note item, workbook row, or export traceability
- unsupported or unknown logging

Run:

```powershell
python evals/cage_card_skill_gym/run_baseline.py --probes evals/cage_card_skill_gym/probes
```

Probe files use JSON-compatible YAML so the harness does not add a new dependency.
