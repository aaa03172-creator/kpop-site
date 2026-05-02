from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(tmp_path: Path, *args: str) -> object:
    env = os.environ.copy()
    env["MOUSEDB_PATH"] = str(tmp_path / "mousedb.sqlite")
    result = subprocess.run(
        [sys.executable, "-m", "mousedb", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def run_cli_result(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["MOUSEDB_PATH"] = str(tmp_path / "mousedb.sqlite")
    return subprocess.run(
        [sys.executable, "-m", "mousedb", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_demo_workflow_json_contract(tmp_path: Path) -> None:
    reset = run_cli(tmp_path, "reset", "--yes", "--json")
    assert reset["reset"] is True

    seed = run_cli(tmp_path, "seed", "--json")
    assert seed["strain_id"] == "STR-0001"
    assert seed["allele_id"] == "AL-0001"

    strains = run_cli(tmp_path, "strain", "search", "PV-Cre", "--json")
    assert strains[0]["strain_id"] == "STR-0001"
    assert strains[0]["alive_mouse_count"] == 0

    mouse = run_cli(
        tmp_path,
        "mouse",
        "add",
        "--display-id",
        "M0231",
        "--strain",
        "STR-0001",
        "--sex",
        "male",
        "--dob",
        "2026-01-04",
        "--cage",
        "C-014",
        "--status",
        "available",
        "--use",
        "experimental",
        "--json",
    )
    assert mouse["mouse_id"] == "M-2026-0231"
    assert mouse["current_cage_id"] == "C-014"

    genotype = run_cli(
        tmp_path,
        "genotype",
        "record",
        "--mouse",
        "M-2026-0231",
        "--allele",
        "AL-0001",
        "--result",
        "positive",
        "--zygosity",
        "heterozygous",
        "--date",
        "2026-02-03",
        "--json",
    )
    assert genotype["genotype_result_id"] == "GT-2026-0001"

    moved = run_cli(
        tmp_path,
        "cage",
        "move-mouse",
        "--mouse",
        "M-2026-0231",
        "--to",
        "C-014",
        "--date",
        "2026-03-12",
        "--json",
    )
    assert moved["current_cage_id"] == "C-014"

    timeline = run_cli(tmp_path, "mouse", "timeline", "M-2026-0231", "--json")
    event_types = [event["event_type"] for event in timeline]
    assert "born" in event_types
    assert "genotyped" in event_types
    assert event_types.count("moved") >= 1
    assert all("source_type" in event for event in timeline)

    ready = run_cli(
        tmp_path,
        "experiment-ready",
        "--strain",
        "STR-0001",
        "--genotype",
        "AL-0001:positive",
        "--sex",
        "male",
        "--age-min-weeks",
        "8",
        "--json",
    )
    assert ready["count"] == 1
    assert ready["mice"][0]["eligibility"] == "candidate"

    summary = run_cli(tmp_path, "colony", "summary", "--json")
    assert summary["total_alive_mice"] == 1
    assert summary["active_strains"] == 1


def test_mating_litter_and_archive_commands(tmp_path: Path) -> None:
    run_cli(tmp_path, "reset", "--yes", "--json")
    run_cli(tmp_path, "seed", "--json")
    male = run_cli(
        tmp_path,
        "mouse",
        "add",
        "--display-id",
        "M0101",
        "--strain",
        "STR-0001",
        "--sex",
        "male",
        "--dob",
        "2026-01-01",
        "--status",
        "breeder",
        "--use",
        "breeder",
        "--json",
    )
    female = run_cli(
        tmp_path,
        "mouse",
        "add",
        "--display-id",
        "M0102",
        "--strain",
        "STR-0001",
        "--sex",
        "female",
        "--dob",
        "2026-01-01",
        "--status",
        "breeder",
        "--use",
        "breeder",
        "--json",
    )
    mating = run_cli(
        tmp_path,
        "mating",
        "create",
        "--male",
        male["mouse_id"],
        "--female",
        female["mouse_id"],
        "--goal",
        "PV-Cre",
        "--start-date",
        "2026-02-01",
        "--status",
        "active",
        "--json",
    )
    assert mating["mating_id"] == "MAT-2026-001"

    litter = run_cli(
        tmp_path,
        "litter",
        "create",
        "--mating",
        mating["mating_id"],
        "--birth-date",
        "2026-03-01",
        "--number-born",
        "2",
        "--json",
    )
    assert litter["litter_id"] == "LIT-2026-001"

    offspring = run_cli(tmp_path, "litter", "create-mice", litter["litter_id"], "--count", "2", "--strain", "STR-0001", "--json")
    assert len(offspring) == 2
    assert {mouse["current_status"] for mouse in offspring} == {"weaning_pending"}

    weaned = run_cli(tmp_path, "litter", "wean", litter["litter_id"], "--date", "2026-03-22", "--json")
    assert weaned["status"] == "weaned"
    assert weaned["number_weaned"] == 2
    assert weaned["weaned_mouse_count"] == 2

    weaned_mouse = run_cli(tmp_path, "mouse", "show", offspring[0]["mouse_id"], "--json")
    assert weaned_mouse["current_status"] == "alive"
    offspring_timeline = run_cli(tmp_path, "mouse", "timeline", offspring[0]["mouse_id"], "--json")
    assert "weaned" in [event["event_type"] for event in offspring_timeline]

    duplicate_wean = run_cli_result(tmp_path, "litter", "wean", litter["litter_id"], "--date", "2026-03-23", "--json")
    assert duplicate_wean.returncode != 0

    archived = run_cli(tmp_path, "strain", "archive", "STR-0001", "--json")
    assert archived["status"] == "archived"


def test_review_correction_source_cli_preserves_before_after(tmp_path: Path) -> None:
    run_cli(tmp_path, "reset", "--yes", "--json")
    run_cli(tmp_path, "seed", "--json")

    source = run_cli(
        tmp_path,
        "source",
        "add",
        "--type",
        "cage_card_photo",
        "--label",
        "Card A",
        "--raw-payload",
        "raw handwritten note",
        "--json",
    )
    assert source["source_record_id"].startswith("SRC-")

    review = run_cli(
        tmp_path,
        "review",
        "add",
        "--issue-type",
        "uncertain_ocr",
        "--severity",
        "high",
        "--entity-type",
        "strain",
        "--entity-id",
        "STR-0001",
        "--source",
        source["source_record_id"],
        "--raw-value",
        "PV-Cre?",
        "--current-value",
        "PV-Cre",
        "--suggested-value",
        "Pvalb-Cre",
        "--evidence",
        "note line 2",
        "--json",
    )
    assert review["status"] == "open"

    correction = run_cli(
        tmp_path,
        "correction",
        "apply",
        "--entity-type",
        "strain",
        "--entity-id",
        "STR-0001",
        "--field",
        "common_name",
        "--value",
        "Pvalb-Cre",
        "--reason",
        "reviewed source card",
        "--source",
        source["source_record_id"],
        "--review",
        review["review_item_id"],
        "--json",
    )
    assert correction["before_value"] == "PV-Cre"
    assert correction["after_value"] == "Pvalb-Cre"

    updated = run_cli(tmp_path, "strain", "show", "STR-0001", "--json")
    assert updated["common_name"] == "Pvalb-Cre"
    resolved = run_cli(tmp_path, "review", "list", "--status", "resolved", "--json")
    assert resolved[0]["review_item_id"] == review["review_item_id"]


def test_source_review_correction_loop(tmp_path: Path) -> None:
    run_cli(tmp_path, "reset", "--yes", "--json")
    run_cli(tmp_path, "seed", "--json")
    mouse = run_cli(
        tmp_path,
        "mouse",
        "add",
        "--display-id",
        "M0232",
        "--strain",
        "STR-0001",
        "--sex",
        "unknown",
        "--dob",
        "2026-01-04",
        "--status",
        "available",
        "--json",
    )

    source = run_cli(
        tmp_path,
        "source",
        "add",
        "--type",
        "manual_entry",
        "--label",
        "Correction note",
        "--raw-payload",
        "M0232 sex female",
        "--json",
    )
    assert source["source_record_id"].startswith("SRC-")
    assert source["checksum"]

    review = run_cli(
        tmp_path,
        "review",
        "add",
        "--issue-type",
        "sex_uncertain",
        "--severity",
        "medium",
        "--entity-type",
        "mouse",
        "--entity-id",
        mouse["mouse_id"],
        "--source",
        source["source_record_id"],
        "--raw-value",
        "unknown",
        "--suggested-value",
        "female",
        "--json",
    )
    assert review["review_item_id"].startswith("REV-")
    assert review["status"] == "open"

    correction = run_cli(
        tmp_path,
        "correction",
        "apply",
        "--entity-type",
        "mouse",
        "--entity-id",
        mouse["mouse_id"],
        "--field",
        "sex",
        "--value",
        "female",
        "--reason",
        "Reviewed cage card note",
        "--source",
        source["source_record_id"],
        "--review",
        review["review_item_id"],
        "--json",
    )
    assert correction["before_value"] == "unknown"
    assert correction["after_value"] == "female"

    updated_mouse = run_cli(tmp_path, "mouse", "show", mouse["mouse_id"], "--json")
    assert updated_mouse["sex"] == "female"

    reviews = run_cli(tmp_path, "review", "list", "--json")
    assert reviews[0]["status"] == "resolved"

    timeline = run_cli(tmp_path, "mouse", "timeline", mouse["mouse_id"], "--json")
    assert any(event["event_type"] == "correction_applied" for event in timeline)
