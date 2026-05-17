from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "prepare-real-photo-hybrid-evaluator-run.py"


def load_pack_module():
    spec = importlib.util.spec_from_file_location("prepare_real_photo_hybrid_evaluator_run", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_photo_hybrid_pack_writes_private_manifest_and_scoring_template(
    tmp_path: Path,
) -> None:
    packer = load_pack_module()
    source_dir = tmp_path / "private-source"
    source_dir.mkdir()
    (source_dir / "card-a.jpg").write_bytes(b"private photo a")
    (source_dir / "card-b.PNG").write_bytes(b"private photo b")
    (source_dir / "ignore.txt").write_text("not a photo", encoding="utf-8")
    output_dir = tmp_path / "private-output"

    summary = packer.build_run_pack(
        source_dir=source_dir,
        output_dir=output_dir,
        run_label="apom-real-photo",
    )

    assert summary["boundary"] == "review item / private real-photo evaluator run pack"
    assert summary["canonical"] is False
    assert summary["photo_count"] == 2
    assert summary["manifest_filename"] == "real-photo-hybrid-manifest.json"
    assert summary["results_template_filename"] == "real-photo-hybrid-scoring-template.json"
    encoded_summary = json.dumps(summary, ensure_ascii=False)
    assert str(source_dir) not in encoded_summary

    manifest = json.loads((output_dir / summary["manifest_filename"]).read_text(encoding="utf-8"))
    assert manifest["layer"] == "review item / test fixture"
    assert manifest["canonical"] is False
    assert len(manifest["cases"]) == 2
    assert manifest["cases"][0]["case_id"] == "apom_real_photo_001"
    assert manifest["cases"][0]["source_photo_filename"] == "card-a.jpg"
    assert Path(manifest["cases"][0]["source_photo_path"]).exists()
    assert manifest["cases"][0]["expected_review_level"] == "must_review"
    assert manifest["cases"][0]["expected_fields"]["expected_review_blockers"] == [
        "manual_real_photo_review_required",
        "hybrid_evaluator_scoring_pending",
    ]

    results = json.loads((output_dir / summary["results_template_filename"]).read_text(encoding="utf-8"))
    assert results["layer"] == "review item / private accuracy scoring input"
    assert results["canonical"] is False
    assert results["workflow_metrics"]["photos_uploaded"] == 2
    assert results["cases"][0]["hybrid_note_line_evaluator"]["boundary"] == (
        "review item / private accuracy scoring input"
    )
    assert results["cases"][0]["hybrid_note_line_evaluator"]["scored_cases"] == []
    assert results["cases"][0]["scoring_status"] == "operator_fill_required"
    assert results["cases"][0]["field_scores"]["mouse_ids_or_note_lines"]["status"] == "missed"
    assert results["cases"][0]["field_scores"]["mouse_ids_or_note_lines"]["reviewed_before_apply"] is False

    readme = (output_dir / "README.md").read_text(encoding="utf-8")
    assert "Local-only" in readme
    assert str(source_dir) not in readme


def test_real_photo_hybrid_pack_cli_redacts_private_source_dir(tmp_path: Path) -> None:
    source_dir = tmp_path / "private-source"
    source_dir.mkdir()
    (source_dir / "card-a.jpg").write_bytes(b"private photo a")
    output_dir = tmp_path / "private-output"

    result = subprocess.run(
        [
            "python",
            str(SCRIPT_PATH),
            "--source-dir",
            str(source_dir),
            "--output-dir",
            str(output_dir),
            "--run-label",
            "apom-cli",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["photo_count"] == 1
    assert summary["source_dir"] == "private source directory omitted"
    assert str(source_dir) not in result.stdout


def test_package_exposes_real_photo_hybrid_pack_command() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    assert (
        package["scripts"]["pilot:real-photo-hybrid-pack"]
        == "python scripts/prepare-real-photo-hybrid-evaluator-run.py"
    )
