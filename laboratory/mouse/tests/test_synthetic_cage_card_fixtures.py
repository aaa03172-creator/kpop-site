from __future__ import annotations

import importlib.util
from contextlib import closing
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from PIL import Image


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_synthetic_cage_card_fixtures.py"
VERIFY_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify-synthetic-photo-e2e.py"
PACKAGE_PATH = Path(__file__).resolve().parents[1] / "package.json"


def load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_synthetic_cage_card_fixtures", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_synthetic_cage_card_fixtures_creates_images_manifest_and_db(tmp_path: Path) -> None:
    generator = load_generator_module()
    output_dir = tmp_path / "synthetic_cage_cards"

    summary = generator.generate(output_dir)

    manifest_path = output_dir / "synthetic_photo_e2e_validation_cases.json"
    db_path = output_dir / "synthetic_photo_e2e.sqlite"
    assert summary == {
        "boundary": "review item / test fixture",
        "canonical": False,
        "case_count": 5,
        "image_count": 5,
        "manifest": str(manifest_path),
        "database": str(db_path),
    }
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["boundary"] == "review item / test fixture"
    assert manifest["canonical"] is False
    assert "Do not send synthetic validation payloads to external services." in manifest["source_policy"]
    assert manifest["latest_parse_selector"]["source_name"] == "synthetic_photo_fixture"
    assert manifest["recommended_coverage_tags"] == [
        "clear",
        "low_confidence",
        "dense_notes",
        "cropped_or_blurry",
        "ear_label_ambiguity",
        "numeric_notes",
    ]
    assert len(manifest["cases"]) == 5
    assert {case["case_id"] for case in manifest["cases"]} == {
        "synthetic_clear_card",
        "synthetic_low_confidence_blurry_card",
        "synthetic_numeric_notes_card",
        "synthetic_digit_prime_confusion_card",
        "synthetic_dense_mating_notes_card",
    }
    for case in manifest["cases"]:
        image_path = output_dir / case["photo_filename"]
        assert image_path.exists()
        assert image_path.suffix.lower() == ".jpg"
        assert image_path.stat().st_size >= case["min_photo_bytes"]
        with Image.open(image_path) as image:
            assert image.format == "JPEG"
            assert image.size[0] >= 1000
            assert image.size[1] >= 700
        assert case["synthetic_source"] == {
            "boundary": "raw source / test fixture",
            "canonical": False,
            "rendering": "local_jpeg_photo_simulation",
        }

    with closing(sqlite3.connect(db_path)) as conn:
        photo_count = conn.execute("SELECT COUNT(*) FROM photo_log").fetchone()[0]
        parse_count = conn.execute("SELECT COUNT(*) FROM parse_result").fetchone()[0]
        note_count = conn.execute("SELECT COUNT(*) FROM card_note_item_log").fetchone()[0]
        review_count = conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0]
        raw_source_kinds = {
            row[0] for row in conn.execute("SELECT DISTINCT raw_source_kind FROM photo_log").fetchall()
        }
        source_layers = {
            row[0] for row in conn.execute("SELECT DISTINCT source_layer FROM photo_log").fetchall()
        }

    assert photo_count == 5
    assert parse_count == 5
    assert note_count >= 8
    assert review_count >= 4
    assert raw_source_kinds == {"synthetic_cage_card_photo"}
    assert source_layers == {"raw source"}


def test_verify_synthetic_photo_e2e_script_runs_generated_jpeg_cases(tmp_path: Path) -> None:
    output_dir = tmp_path / "synthetic_photo_e2e_run"

    completed = subprocess.run(
        [
            sys.executable,
            str(VERIFY_SCRIPT_PATH),
            "--output-dir",
            str(output_dir),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    assert summary["boundary"] == "review item / test fixture"
    assert summary["canonical"] is False
    assert summary["generated"]["image_count"] == 5
    assert summary["verification"]["passed"] == 5
    assert summary["verification"]["failed"] == 0
    assert summary["verification"]["confidence_calibration"]["coverage"]["missing_tags"] == []
    assert (output_dir / "synthetic_photo_e2e_validation_cases.json").exists()
    assert (output_dir / "synthetic_photo_e2e.sqlite").exists()


def test_verify_synthetic_photo_e2e_default_run_cleans_disposable_output() -> None:
    completed = subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT_PATH), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    generated_dir = Path(summary["generated"]["manifest"]).parent
    assert summary["verification"]["passed"] == 5
    assert not generated_dir.exists()


def test_package_exposes_synthetic_photo_e2e_script() -> None:
    package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))

    assert package["scripts"]["test:synthetic-photo-e2e"] == (
        "python scripts/verify-synthetic-photo-e2e.py --json"
    )
    assert "npm run test:synthetic-photo-e2e" in package["scripts"]["verify"]
