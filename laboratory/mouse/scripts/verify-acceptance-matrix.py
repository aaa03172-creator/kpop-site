from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "mvp_acceptance_matrix_ko.md"
LOCAL_VERIFY_PATH = ROOT / "scripts" / "verify-local-app.py"
INDEX_PATH = ROOT / "static" / "index.html"
MAIN_PATH = ROOT / "app" / "main.py"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    matrix = MATRIX_PATH.read_text(encoding="utf-8")
    local_verify = LOCAL_VERIFY_PATH.read_text(encoding="utf-8")
    index_html = INDEX_PATH.read_text(encoding="utf-8")
    main_py = MAIN_PATH.read_text(encoding="utf-8")

    for number in range(1, 21):
        acceptance_id = f"A{number:02d}"
        assert_true(acceptance_id in matrix, f"Acceptance matrix is missing {acceptance_id}.")

    evidence_checks = {
        "A01": ["Photo image endpoint should return the preserved raw upload bytes"],
        "A03": ["created_mouse_candidates", "Manual photo transcription should stay parsed/intermediate"],
        "A04": ["/api/card-snapshots", "card_snapshot_id"],
        "A06": ["Review Note Evidence", "review_note_summary", "image_url"],
        "A07": ["note_label_decision", "count_note"],
        "A08": ["parsed_label", "correction_log"],
        "A11": ["apply-preview", "Canonical candidate apply preview should not write mouse state"],
        "A13": ["canonical_candidate_voided", "Re-voiding a voided canonical candidate should be blocked"],
        "A17": ["blocked_review_items", "review_blockers"],
        "A18": ["Ready CSV export should succeed", "Ready separation XLSX export should succeed"],
    }
    combined = "\n".join([matrix, local_verify, index_html, main_py])
    for acceptance_id, tokens in evidence_checks.items():
        for token in tokens:
            assert_true(token in combined, f"{acceptance_id} evidence token missing: {token}")

    assert_true("Go / No-Go" in matrix, "Acceptance matrix should include a go/no-go summary.")
    assert_true("G01" in matrix and "G05" in matrix, "Acceptance matrix should include explicit remaining gaps.")
    print("Acceptance matrix verification passed.")


if __name__ == "__main__":
    main()
