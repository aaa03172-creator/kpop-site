from __future__ import annotations

import io
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from app import db
from app.main import ROOT, detect_card_bbox, generate_roi_preview


def blue_card_bytes() -> bytes:
    image = Image.new("RGB", (640, 420), "#f8f8f8")
    draw = ImageDraw.Draw(image)
    draw.rectangle((110, 80, 560, 350), fill="#36aee2")
    draw.rectangle((135, 110, 535, 330), fill="#eefaff")
    draw.text((150, 120), "ApoM Tg/Tg", fill="#111111")
    draw.text((150, 175), "Sex F 2", fill="#111111")
    draw.text((150, 230), "MT401 R", fill="#111111")
    output = io.BytesIO()
    image.save(output, "JPEG", quality=92)
    return output.getvalue()


def test_detect_card_bbox_prefers_colored_card_component() -> None:
    image = Image.open(io.BytesIO(blue_card_bytes())).convert("RGB")

    bbox = detect_card_bbox(image)

    assert bbox["template_hint"] == "blue_structured_card"
    assert bbox["source"].startswith("color_card_connected_component")
    assert bbox["w"] < image.width
    assert bbox["h"] < image.height


def test_roi_preview_is_cache_artifact_and_preserves_raw_photo(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    photo_id = "roi_tdd_photo"
    photo_dir = ROOT / "data" / "photos" / "test_roi_preview"
    roi_dir = ROOT / "data" / "roi" / photo_id
    raw_bytes = blue_card_bytes()
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        photo_dir.mkdir(parents=True, exist_ok=True)
        photo_path = photo_dir / "card.jpg"
        photo_path.write_bytes(raw_bytes)
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO photo_log
                    (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    photo_id,
                    "card.jpg",
                    str(photo_path.relative_to(ROOT)),
                    "2026-05-04T00:00:00Z",
                    "review_pending",
                    "cage_card_photo",
                ),
            )

        preview = generate_roi_preview(photo_id, "blue_structured_card")

        assert photo_path.read_bytes() == raw_bytes
        assert preview["source_layer"] == "raw source photo"
        assert preview["artifact_layer"] == "cache"
        assert preview["derived_layer"] == "parsed or intermediate result"
        assert preview["review_note"]
        assert preview["crops"]
        assert all(crop["artifact_layer"] == "cache" for crop in preview["crops"])
    finally:
        db.DB_PATH = old_db_path
        shutil.rmtree(photo_dir, ignore_errors=True)
        shutil.rmtree(roi_dir, ignore_errors=True)
