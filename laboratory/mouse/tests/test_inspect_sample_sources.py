from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "inspect_sample_sources.py"


def test_inspect_workbook_outputs_compact_rows(tmp_path: Path) -> None:
    workbook_path = tmp_path / "source.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "animal sheet"
    sheet.append(["Cage No.", "Strain", "Sex", "I.D"])
    sheet.append(["C-014", "ApoM Tg/Tg", "M", "MT321"])
    workbook.save(workbook_path)

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--workbook", str(workbook_path), "--max-rows", "2"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "FILE\tsource.xlsx" in result.stdout
    assert "SHEET\tanimal sheet" in result.stdout
    assert "ROW\tC-014\tApoM Tg/Tg\tM\tMT321" in result.stdout


def test_inspect_photo_folder_lists_matching_files(tmp_path: Path) -> None:
    photo_path = tmp_path / "card-a.jpg"
    photo_path.write_bytes(b"not a real jpeg")
    ignored_path = tmp_path / "card-b.png"
    ignored_path.write_bytes(b"not inspected")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--photo-folder", str(tmp_path), "--photo-pattern", "*.jpg"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert f"PHOTO_FOLDER\t{tmp_path}" in result.stdout
    assert "PHOTO\tcard-a.jpg" in result.stdout
    assert "card-b.png" not in result.stdout
