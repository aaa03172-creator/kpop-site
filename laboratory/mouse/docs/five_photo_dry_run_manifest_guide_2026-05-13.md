# Five-Photo Dry Run Manifest Guide - 2026-05-13

Layer classification: review item / local pilot guide.

Canonical: false.

Use this guide to create a private 5-photo dry run manifest outside Git. The manifest is a local `review item / test fixture` used to check whether the workflow routes real copied cage-card photos safely. It is not canonical colony state.

## Who Does What

The operator chooses copied photos and reads the card evidence. Codex can help format the private manifest, run the verifier, interpret errors, and summarize a sanitized run log.

Do not commit:

- copied real cage-card photos
- private manifest files
- private local photo paths
- raw OCR/AI payloads from real photos
- generated pilot workbooks
- backup folders

## Suggested 5-Photo Mix

| Case | Card type | Expected review level | Export blocking? | Why include it |
| --- | --- | --- | --- | --- |
| `pilot_photo_001` | `separated` | `quick_check` | `false` | Clear separated card with mouse IDs/note lines. |
| `pilot_photo_002` | `separated` | `must_review` | `true` | Ambiguous DOB, count mismatch, unclear ear label, or low confidence. |
| `pilot_photo_003` | `mating` | `must_review` | `true` | Sire/dam or litter note should be reviewed before animal sheet export. |
| `pilot_photo_004` | `unclear` | `must_review` | `true` | Blurry, cropped, shadowed, or hard-to-read card. |
| `pilot_photo_005` | `other` (`Other / Unknown` in the UI) | `trace_only` | `false` | Unexpected or unsupported format should not force canonical interpretation. |

## Private Folder Layout

Create a folder outside the repository, for example:

```text
C:\MouseDB-private-pilot\2026-05-13-dry-run\
  photos\
    pilot_photo_001.jpg
    pilot_photo_002.jpg
    pilot_photo_003.jpg
    pilot_photo_004.jpg
    pilot_photo_005.jpg
  real_photo_pilot_manifest.json
```

The folder above is an example. Use any local private path that is not inside this Git checkout.

## Private Manifest Template

Copy this JSON into the private manifest file and edit only the values that come from copied source-photo evidence.

```json
{
  "layer": "review item / test fixture",
  "canonical": false,
  "source_policy": "Local-only real-photo dry run labels. Do not commit private photos, private source paths, OCR payloads, or pilot exports.",
  "recommended_card_types": ["separated", "mating", "unclear", "other"],
  "cases": [
    {
      "case_id": "pilot_photo_001",
      "source_photo_path": "C:/MouseDB-private-pilot/2026-05-13-dry-run/photos/pilot_photo_001.jpg",
      "source_photo_filename": "pilot_photo_001.jpg",
      "card_type": "separated",
      "traceability_label": "5-photo dry run / photo 001",
      "expected_review_level": "quick_check",
      "expected_export_blocking": false,
      "expected_fields": {
        "raw_strain_text": "copy visible strain text here",
        "mouse_ids_or_note_lines": ["copy raw note line here"],
        "sex_count": "copy visible sex/count here",
        "dob": "copy visible DOB text here",
        "mating_or_litter_note": "",
        "expected_review_blockers": []
      }
    },
    {
      "case_id": "pilot_photo_002",
      "source_photo_path": "C:/MouseDB-private-pilot/2026-05-13-dry-run/photos/pilot_photo_002.jpg",
      "source_photo_filename": "pilot_photo_002.jpg",
      "card_type": "separated",
      "traceability_label": "5-photo dry run / photo 002",
      "expected_review_level": "must_review",
      "expected_export_blocking": true,
      "expected_fields": {
        "raw_strain_text": "copy visible strain text here or unclear",
        "mouse_ids_or_note_lines": ["copy raw note line here"],
        "sex_count": "copy visible sex/count here or unclear",
        "dob": "copy raw DOB text here or unclear",
        "mating_or_litter_note": "",
        "expected_review_blockers": ["ambiguous_date"]
      }
    },
    {
      "case_id": "pilot_photo_003",
      "source_photo_path": "C:/MouseDB-private-pilot/2026-05-13-dry-run/photos/pilot_photo_003.jpg",
      "source_photo_filename": "pilot_photo_003.jpg",
      "card_type": "mating",
      "traceability_label": "5-photo dry run / photo 003",
      "expected_review_level": "must_review",
      "expected_export_blocking": true,
      "expected_fields": {
        "raw_strain_text": "copy visible strain text here",
        "mouse_ids_or_note_lines": ["copy sire/dam or parent note here"],
        "sex_count": "parents",
        "dob": "copy visible DOB or unclear",
        "mating_or_litter_note": "copy litter or mating note here",
        "expected_review_blockers": ["mating_litter_note_review"]
      }
    },
    {
      "case_id": "pilot_photo_004",
      "source_photo_path": "C:/MouseDB-private-pilot/2026-05-13-dry-run/photos/pilot_photo_004.jpg",
      "source_photo_filename": "pilot_photo_004.jpg",
      "card_type": "unclear",
      "traceability_label": "5-photo dry run / photo 004",
      "expected_review_level": "must_review",
      "expected_export_blocking": true,
      "expected_fields": {
        "raw_strain_text": "unclear",
        "mouse_ids_or_note_lines": ["copy any readable raw note text here"],
        "sex_count": "unclear",
        "dob": "unclear",
        "mating_or_litter_note": "not visible",
        "expected_review_blockers": ["low_confidence", "manual_transcription_required"]
      }
    },
    {
      "case_id": "pilot_photo_005",
      "source_photo_path": "C:/MouseDB-private-pilot/2026-05-13-dry-run/photos/pilot_photo_005.jpg",
      "source_photo_filename": "pilot_photo_005.jpg",
      "card_type": "other",
      "traceability_label": "5-photo dry run / photo 005",
      "expected_review_level": "trace_only",
      "expected_export_blocking": false,
      "expected_fields": {
        "raw_strain_text": "not a supported cage-card format",
        "mouse_ids_or_note_lines": [],
        "sex_count": "not applicable",
        "dob": "",
        "mating_or_litter_note": "",
        "expected_review_blockers": []
      }
    }
  ]
}
```

## How To Fill Values

- Use raw visible text. If a value is unclear, write `unclear`.
- Do not normalize ambiguous dates unless the human reviewer is confident.
- Preserve note lines as written, including struck-through or odd notation if visible.
- Use `expected_review_blockers` to describe why a case should stop export before review.
- Keep `expected_export_blocking=true` for any case that must not appear in final export until reviewed.

Common blocker labels:

- `low_confidence`
- `manual_transcription_required`
- `ambiguous_date`
- `count_mismatch`
- `unclear_ear_label`
- `duplicate_active_mouse`
- `outside_assigned_strain_scope`
- `mating_litter_note_review`
- `unsupported_card_format`

## Verify The Private Manifest

Run:

```powershell
python scripts/verify-real-photo-pilot.py --manifest "C:\MouseDB-private-pilot\2026-05-13-dry-run\real_photo_pilot_manifest.json"
```

Expected:

- `status` is `passed`
- `case_count` is `5`
- `failed` is `0`
- `card_type_counts` includes separated, mating, unclear, and other
- `export_blocking_counts.blocking` is at least `3`

If verification fails:

- `source_photo_path is required`: add the local copied photo path.
- `source_photo_path does not exist`: fix the path or copied filename.
- `traceability_label is required`: add a non-sensitive label.
- `expected_review_level must be one of`: use `must_review`, `quick_check`, or `trace_only`.
- `expected_export_blocking boolean is required`: use `true` or `false`, not text.

## After Manifest Verification

1. Start the app with `start.bat`.
2. Follow `docs/manual_pilot_walkthrough_2026-05-13.md`.
3. Prepare a repeatable sanitized run log shell:

```powershell
python scripts/prepare-copied-pilot-run.py --manifest "C:\MouseDB-private-pilot\2026-05-13-dry-run\real_photo_pilot_manifest.json" --run-label 5-photo-copied-dry-run --output-log docs/pilot_runs/YYYY-MM-DD-5-photo-copied-dry-run.md
```

4. Fill the generated log with operator counts, review outcomes, XLSX download results, and backup/restore findings.
5. Do not copy private photo paths or raw real-photo OCR payloads into the committed run log.

Browser note:

- The Codex in-app Browser control surface does not provide file upload support for this private copied-photo pilot. Use the normal local browser UI or standalone Playwright when the run must upload private copied photos and download XLSX files.
