from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "parse_distribution_workbook.py"


def load_parser_module():
    spec = importlib.util.spec_from_file_location("parse_distribution_workbook", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_parse_distribution_workbook_keeps_source_cells_with_read_only_mode(tmp_path: Path) -> None:
    parser = load_parser_module()
    workbook_path = tmp_path / "distribution.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "distribution"
    ws.append(["Lab A", "Mating Type", "Cage Count", "Mating Cage Count"])
    ws.append(["Dr Kim", "maintenance", "12", "4"])
    ws.append(["", "expansion", "8", "2"])
    wb.save(workbook_path)

    payload = parser.parse_distribution_workbook(workbook_path)

    assert payload["layer"] == "parsed or intermediate result"
    assert payload["rows"][0]["responsible_person_raw"] == "Dr Kim"
    assert payload["rows"][0]["cage_count_value"] == 12
    assert payload["rows"][0]["source_cells"]["mating_type"] == "B2"
    assert payload["rows"][1]["responsible_person_raw"] == "Dr Kim"
    assert payload["rows"][1]["source_cells"]["mating_cage_count"] == "D3"
