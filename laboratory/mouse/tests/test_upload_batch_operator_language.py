from __future__ import annotations

from app.main import upload_batch_payload


def base_batch_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "upload_batch_id": "batch_operator_words",
        "batch_label": "Operator wording batch",
        "expected_photo_count": 5,
        "status": "open",
        "source_layer": "raw source",
        "note": "",
        "created_at": "2026-05-13T00:00:00Z",
        "updated_at": "2026-05-13T00:00:00Z",
        "photo_count": 5,
        "transcribed_photo_count": 5,
        "pending_transcription_count": 0,
        "total_review_count": 15,
        "open_review_count": 0,
        "comparison_review_count": 4,
        "open_comparison_review_count": 0,
        "comparison_needed_count": 1,
        "canonical_candidate_count": 1,
        "applied_candidate_count": 1,
        "first_photo_uploaded_at": "2026-05-13T00:00:00Z",
        "latest_photo_uploaded_at": "2026-05-13T00:01:00Z",
    }
    row.update(overrides)
    return row


def test_upload_batch_payload_uses_operator_language_for_comparison_needed_state() -> None:
    payload = upload_batch_payload(base_batch_row())

    assert payload["derived_status"] == "review_pending"
    assert payload["operator_status_label"] == "Needs comparison review setup"
    assert "1 transcribed photo" in payload["operator_status_detail"]
    assert "Create Batch Comparison Reviews" in payload["operator_next_action"]


def test_upload_batch_payload_explains_ready_for_mapping_state() -> None:
    payload = upload_batch_payload(
        base_batch_row(
            comparison_review_count=5,
            comparison_needed_count=0,
            canonical_candidate_count=0,
            applied_candidate_count=0,
        )
    )

    assert payload["derived_status"] == "ready_for_mapping"
    assert payload["operator_status_label"] == "Ready to map candidate"
    assert "comparison reviews are resolved" in payload["operator_status_detail"]
    assert "map source-backed evidence" in payload["operator_next_action"]
