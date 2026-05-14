from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "prepare-copied-pilot-run.py"
EXAMPLE_MANIFEST = ROOT / "config" / "real_photo_validation_cases.example.json"
READINESS_MANIFEST = ROOT / "config" / "copied_photo_pilot_readiness_manifest.example.json"


def test_copied_pilot_harness_writes_sanitized_repeatable_run_log(tmp_path: Path) -> None:
    output_log = tmp_path / "copied-pilot-log.md"

    result = subprocess.run(
        [
            "python",
            str(HARNESS),
            "--manifest",
            str(EXAMPLE_MANIFEST),
            "--run-label",
            "example copied pilot",
            "--output-log",
            str(output_log),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "passed"
    assert summary["boundary"] == "review item / pilot run log"
    assert summary["canonical"] is False
    assert summary["manifest_case_count"] == 4
    assert summary["sanitized_log_path"] == str(output_log)
    assert "source_photo_path" not in result.stdout
    assert "static/assets/cage-card-evidence-art.png" not in result.stdout

    log = output_log.read_text(encoding="utf-8")
    assert "Layer classification: review item / pilot run log." in log
    assert "private manifest verified; path intentionally omitted" in log
    assert "AI / local OCR / manual extraction decision" in log
    assert "scripts/backup-local-pilot.ps1" in log
    assert "scripts/restore-local-pilot.ps1" in log
    assert "Other / Unknown" in log
    assert "Sanitized Metrics To Publish" in log
    assert "Failure Taxonomy" in log
    assert "Reviewer Workload Criteria" in log
    assert "Accuracy Evaluation Criteria" in log
    assert "Go / No-Go Criteria" in log
    assert "privacy_leak" in log
    assert "Mouse IDs and note-line continuity" in log
    assert "20-30 copied photos" in log
    assert "in-app Browser control surface does not provide file upload support" in log
    assert "source_photo_path" not in log
    assert "static/assets/cage-card-evidence-art.png" not in log


def test_operator_docs_and_ui_explain_other_unknown_and_browser_upload_limits() -> None:
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    walkthrough = (ROOT / "docs" / "manual_pilot_walkthrough_2026-05-13.md").read_text(encoding="utf-8")
    template = (ROOT / "docs" / "pilot_run_log_template_2026-05-13.md").read_text(encoding="utf-8")
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    assert '<option value="unknown">Other / Unknown</option>' in html
    assert "Other / Unknown" in walkthrough
    assert "in-app Browser control surface does not provide file upload support" in walkthrough
    assert "Other / Unknown" in template
    assert "Browser/upload surface" in template
    assert package["scripts"]["pilot:copied-runbook"] == "python scripts/prepare-copied-pilot-run.py"


def test_copied_pilot_harness_writes_go_no_go_and_backup_restore_evidence_without_private_paths(tmp_path: Path) -> None:
    output_log = tmp_path / "copied-photo-readiness-log.md"

    result = subprocess.run(
        [
            "python",
            str(HARNESS),
            "--manifest",
            str(READINESS_MANIFEST),
            "--run-label",
            "20 photo readiness example",
            "--output-log",
            str(output_log),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "passed"
    assert summary["readiness"]["status"] == "go"
    assert summary["readiness"]["checks"]["photo_count"]["actual"] == 20
    assert "source_photo_path" not in result.stdout
    assert "static/assets/cage-card-evidence-art.png" not in result.stdout

    log = output_log.read_text(encoding="utf-8")
    assert "## Go/No-Go Readiness" in log
    assert "| Go/no-go | go |" in log
    assert "| backup_restore_evidence | passed |" in log
    assert "before-20-photo-readiness-example" in log
    assert "restore-probe-20-photo-readiness-example" in log
    assert "source_photo_path" not in log
    assert "static/assets/cage-card-evidence-art.png" not in log
