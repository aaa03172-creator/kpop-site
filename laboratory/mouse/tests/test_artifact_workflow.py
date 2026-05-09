from __future__ import annotations

import json
from pathlib import Path

from app import main as app_main


def test_persist_proposed_changeset_artifact_keeps_preview_non_canonical(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(app_main, "ARTIFACT_ROOT", tmp_path / "mousedb_artifacts")
    preview = {
        "candidate_id": "candidate_001",
        "review_id": "review_001",
        "parse_id": "parse_001",
        "legacy_row_id": "legacy_001",
        "proposed_mice": [
            {
                "mouse_id": "mouse_MT318_parse_001",
                "display_id": "MT318",
                "source_note_item_id": "note_001",
                "source_photo_id": "photo_001",
                "card_snapshot_id": "card_001",
                "will_create_mouse": True,
                "will_create_event": True,
            }
        ],
        "duplicate_risks": [],
        "blocked": False,
        "blockers": [],
    }

    result = app_main.persist_proposed_changeset_artifact(
        preview,
        created_at="2026-05-09T12:00:00Z",
    )

    artifact_path = Path(result["artifact_path"])
    assert artifact_path.exists()
    assert artifact_path.parent == tmp_path / "mousedb_artifacts" / "proposed_changesets"

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["artifact_type"] == "proposed_changeset"
    assert artifact["source_layer"] == "export or view"
    assert artifact["status"] == "draft"
    assert artifact["canonical_candidate_id"] == "candidate_001"
    assert artifact["source_refs"]["photo_ids"] == ["photo_001"]
    assert artifact["source_refs"]["note_item_ids"] == ["note_001"]
    assert artifact["source_refs"]["card_snapshot_ids"] == ["card_001"]
    assert artifact["proposed_writes"][0]["target_layer"] == "canonical structured state"
    assert artifact["proposed_writes"][0]["target_table"] == "mouse_master"
    assert artifact["proposed_writes"][0]["operation"] == "insert"
    assert artifact["proposed_writes"][0]["evidence_refs"] == ["note_001", "photo_001", "card_001"]
    assert artifact["blockers"] == []


def test_persist_validation_report_artifact_blocks_missing_trace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(app_main, "ARTIFACT_ROOT", tmp_path / "mousedb_artifacts")
    preview = {
        "candidate_id": "candidate_missing_trace",
        "candidate_status": "draft",
        "review_id": "review_002",
        "parse_id": "parse_002",
        "proposed_mice": [
            {
                "mouse_id": "mouse_MT319_parse_002",
                "display_id": "MT319",
                "source_note_item_id": "",
                "source_photo_id": "photo_002",
            }
        ],
        "duplicate_risks": [],
        "blockers": [],
    }

    report = app_main.build_canonical_apply_validation_report(
        preview,
        created_at="2026-05-09T12:05:00Z",
    )
    result = app_main.persist_validation_report_artifact(report)

    artifact_path = Path(result["artifact_path"])
    assert artifact_path.exists()
    assert artifact_path.parent == tmp_path / "mousedb_artifacts" / "validation_reports"

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["artifact_type"] == "validation_report"
    assert artifact["source_layer"] == "export or view"
    assert artifact["scope"] == "canonical_apply"
    assert artifact["status"] == "blocked"
    assert artifact["canonical_candidate_id"] == "candidate_missing_trace"
    assert artifact["source_refs"]["photo_ids"] == ["photo_002"]
    assert artifact["source_refs"]["parse_ids"] == ["parse_002"]
    assert any(
        check["check_key"] == "missing_source_trace" and check["status"] == "blocked"
        for check in artifact["checks"]
    )
