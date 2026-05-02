from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "parse_legacy_workbooks.py"


def load_parser_module():
    spec = importlib.util.spec_from_file_location("parse_legacy_workbooks", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_parse_animal_sheet_keeps_workbook_rows_reviewable(tmp_path: Path) -> None:
    parser = load_parser_module()
    workbook_path = tmp_path / "animal-sheet.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "animal sheet"
    ws.append(["Cage No.", "Strain", "Sex", "I.D", "Genotype", "DOB", "Mating Date", "Pubs"])
    ws.append(["C-014", "ApoM Tg/Tg", "\u2642", "319", "Tg/Tg", "2026-04-13", "", ""])
    ws.append(["", "", "", "", "", "", "2026-04-13", "10p"])
    wb.save(workbook_path)

    payload = parser.parse_workbook(workbook_path, kind="animal")

    assert payload["layer"] == "parsed or intermediate result"
    assert payload["source_layer"] == "export or view"
    assert payload["workbook_kind"] == "legacy_animal_sheet"
    assert payload["notes"]
    assert payload["rows"][0]["row_type"] == "parent_or_mouse_snapshot"
    assert payload["rows"][0]["sex_raw"] == "\u2642"
    assert payload["rows"][0]["sex_candidate"] == "male"
    assert payload["rows"][0]["cage_no_raw"] == "C-014"
    assert payload["rows"][0]["source_cells"]["display_id"] == "D2"
    assert payload["rows"][1]["row_type"] == "litter_or_offspring_snapshot"
    assert payload["rows"][1]["review_status"] == "candidate"


def test_parse_separation_sheet_keeps_counts_as_candidates(tmp_path: Path) -> None:
    parser = load_parser_module()
    workbook_path = tmp_path / "separation.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "separation"
    ws.append(["Strain", "Genotype", "Total", "DOB", "WT", "TG", "Sampling Point"])
    ws.append(["Npc1 fl/fl", "fl/fl", "\u2640 3p", "2026-04-01", "1", "2", "tail"])
    wb.save(workbook_path)

    payload = parser.parse_workbook(workbook_path, kind="separation")

    row = payload["rows"][0]
    assert payload["workbook_kind"] == "legacy_separation_status"
    assert row["row_type"] == "separation_summary_row"
    assert row["source_layer"] == "export or view"
    assert row["sex_candidate"] == "female"
    assert row["count_candidate"] == 3
    assert row["source_cells"]["total"] == "C2"
    assert row["review_status"] == "candidate"
