import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_package_exposes_browser_photo_to_export_e2e_script() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    assert package["scripts"]["test:browser-photo-export-e2e"] == (
        "node scripts/verify-browser-photo-export-e2e.js"
    )
    assert "npm run test:browser-photo-export-e2e" in package["scripts"]["verify"]
    assert (ROOT / "scripts" / "verify-browser-photo-export-e2e.js").exists()


def test_browser_photo_export_e2e_uses_approved_ai_extraction_path() -> None:
    result = subprocess.run(
        ["node", "scripts/verify-browser-photo-export-e2e.js"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "passed"
    assert summary["extraction_method"] == "ai_photo_extraction"
    assert summary["external_approval"]["approved_external_inference"] is True
    assert summary["external_approval"]["approval_scope"] == "single_photo_ai_transcription_draft"
    assert summary["external_approval"]["payload_review"] == {
        "full_colony_records_sent": False,
        "excel_rows_sent": False,
        "raw_source_photo_sent": False,
        "derived_roi_crops_sent": True,
        "assigned_strain_scope_sent": True,
    }
