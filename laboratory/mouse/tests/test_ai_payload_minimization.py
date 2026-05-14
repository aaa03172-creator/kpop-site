from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import db
from app import main as app_main
from app.main import ROOT, PhotoAiDraftCreate, ai_transcription_image_content, request_ai_transcription_draft


def test_static_ai_status_copy_requires_approval_and_local_only_policy() -> None:
    html = Path("static/index.html").read_text(encoding="utf-8")
    shell_start = html.index("function renderShellStatus")
    shell_end = html.index("function firstMouse", shell_start)
    shell_status = html[shell_start:shell_end]

    assert "function aiDraftStatusLabel" in html
    assert "function aiPayloadPolicyCopy" in html
    assert "function aiExternalApprovalMessage" in html
    assert "AI draft: approval required" in html
    assert "AI unavailable: local-only" in html
    assert "No external request is sent until you approve this action." in html
    assert "Payload minimized: selected source photo plus active assigned strain names only." in html
    assert "Drafts stay reviewable; operator approval is still required." in html
    assert "aiPayloadPolicyCopy(aiStatus)" in shell_status
    assert "aiDraftStatusLabel(aiStatus)" in shell_status
    assert "local + AI draft ready" not in shell_status


def test_health_ai_draft_status_keeps_approval_required_when_provider_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_main, "RUNTIME_OPENAI_API_KEY", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(app_main.app)

    unavailable = client.get("/api/health").json()["ai_draft"]

    assert unavailable["available"] is False
    assert unavailable["approval_required"] is True
    assert unavailable["key_source"] == "missing"

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    available = client.get("/api/health").json()["ai_draft"]

    assert available["available"] is True
    assert available["approval_required"] is True
    assert available["key_source"] == "environment"


def test_ai_image_content_does_not_send_unreadable_full_photo_fallback(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    photo_id = "corrupt_photo"
    photo_dir = ROOT / "data" / "photos" / "test_ai_payload_minimization"
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        photo_dir.mkdir(parents=True, exist_ok=True)
        photo_path = photo_dir / "corrupt-card.jpg"
        photo_path.write_bytes(b"not a readable image")
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO photo_log
                    (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    photo_id,
                    "corrupt-card.jpg",
                    str(photo_path.relative_to(ROOT)),
                    "2026-05-04T00:00:00Z",
                    "review_pending",
                    "cage_card_photo",
                ),
            )

        with pytest.raises(HTTPException) as error:
            ai_transcription_image_content(photo_id, photo_path, "image/jpeg", "low")

        assert error.value.status_code == 415
        assert "ROI crop generation is required" in str(error.value.detail)
    finally:
        db.DB_PATH = old_db_path
        shutil.rmtree(photo_dir, ignore_errors=True)


def test_external_ai_draft_response_records_approval_and_payload_review(monkeypatch: pytest.MonkeyPatch) -> None:
    posted_payloads: list[dict] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "output_text": """
                {
                  "card_type": "Separated",
                  "raw_strain": "ApoM Tg/Tg",
                  "matched_strain": "ApoM Tg/Tg",
                  "sex_raw": "F",
                  "id_raw": "MT",
                  "dob_raw": "",
                  "dob_normalized": "",
                  "mating_date_raw": "",
                  "mating_date_normalized": "",
                  "lmo_raw": "",
                  "mouse_count": "2 total",
                  "notes": [],
                  "raw_visible_text_lines": ["ApoM Tg/Tg", "Sex F 2"],
                  "symbol_confusions": [],
                  "confidence": 88,
                  "uncertain_fields": [],
                  "reviewer_note": ""
                }
                """
            }

    class FakeClient:
        def __init__(self, timeout: int):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def post(self, url: str, *, headers: dict, json: dict):
            posted_payloads.append(json)
            return FakeResponse()

    monkeypatch.setattr(app_main, "current_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(
        app_main,
        "photo_image_path",
        lambda photo_id: (
            {"original_filename": "approval-card.jpg"},
            Path("unused.jpg"),
            "image/jpeg",
        ),
    )
    monkeypatch.setattr(
        app_main,
        "ai_transcription_image_content",
        lambda photo_id, image_path, media_type, detail: {
            "mode": "roi_field_crops",
            "payload_minimization": "Only ROI crops and active assigned strain names/aliases were sent.",
            "extraction_regions": [{"label": "card", "target_fields": ["raw_visible_text_lines"]}],
            "roi_template_type": "blue_structured_card",
            "content": [{"type": "input_text", "text": "ROI crop payload"}],
        },
    )
    monkeypatch.setattr(
        app_main,
        "assigned_strain_scope_for_prompt",
        lambda: [{"display_name": "ApoM Tg/Tg", "aliases": ["ApoM"]}],
    )
    monkeypatch.setattr(app_main.httpx, "Client", FakeClient)

    result = request_ai_transcription_draft(
        "photo_approval_review",
        PhotoAiDraftCreate(approved_external_inference=True, detail="low"),
    )

    assert posted_payloads
    assert result["external_approval"] == {
        "approved_external_inference": True,
        "approval_scope": "single_photo_ai_transcription_draft",
        "payload_review": {
            "full_colony_records_sent": False,
            "excel_rows_sent": False,
            "raw_source_photo_sent": False,
            "derived_roi_crops_sent": True,
            "assigned_strain_scope_sent": True,
        },
    }
