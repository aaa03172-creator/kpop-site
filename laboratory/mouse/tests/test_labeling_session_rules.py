from __future__ import annotations

from app import db
from app.labeling_rules import (
    apply_ear_sequence,
    interpret_crossed_out_status,
    match_samples_to_mice,
)


def test_labeling_rule_schema_seeds_default_apom_rule(tmp_path):
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            rule = conn.execute(
                """
                SELECT display_name, numbering_order, mouse_number_scope,
                       ear_sequence_scope, crossed_out_handling, sample_mapping,
                       genotyping_target
                FROM labeling_rule_set
                WHERE rule_set_id = ?
                """,
                ("label_rule_apom_tgtg_20260506",),
            ).fetchone()
            sequence = conn.execute(
                """
                SELECT ear_label_code
                FROM labeling_rule_ear_sequence
                WHERE rule_set_id = ?
                ORDER BY sequence_index
                """,
                ("label_rule_apom_tgtg_20260506",),
            ).fetchall()

        assert dict(rule) == {
            "display_name": "ApoM Tg/Tg 2026-05-06",
            "numbering_order": "male_first",
            "mouse_number_scope": "continues_across_cages_within_same_id",
            "ear_sequence_scope": "resets_per_cage",
            "crossed_out_handling": "dead",
            "sample_mapping": "sample_id_equals_mouse_display_id",
            "genotyping_target": "ApoM-tg",
        }
        assert [row["ear_label_code"] for row in sequence[:6]] == [
            "R_PRIME",
            "L_PRIME",
            "R_PRIME_L_PRIME",
            "R_CIRCLE",
            "L_CIRCLE",
            "R_CIRCLE_L_CIRCLE",
        ]
    finally:
        db.DB_PATH = old_db_path


def test_ear_sequence_resets_for_each_cage_group():
    sequence = ["R_PRIME", "L_PRIME", "R_PRIME_L_PRIME"]
    note_groups = [
        [{"mouse": "1"}, {"mouse": "2"}],
        [{"mouse": "3"}, {"mouse": "4"}],
    ]

    result = apply_ear_sequence(note_groups, sequence)

    assert result[0][0]["expected_ear_label_code"] == "R_PRIME"
    assert result[0][1]["expected_ear_label_code"] == "L_PRIME"
    assert result[1][0]["expected_ear_label_code"] == "R_PRIME"
    assert result[1][1]["expected_ear_label_code"] == "L_PRIME"


def test_ear_sequence_deep_copies_groups_and_skips_dead_notes():
    sequence = ["R_PRIME", "L_PRIME", "R_PRIME_L_PRIME"]
    note_groups = [
        [
            {"mouse": "1", "metadata": {"raw": "1 R'"}},
            {"mouse": "2", "interpreted_status": "dead", "metadata": {"raw": "2 crossed"}},
            {"mouse": "3", "metadata": {"raw": "3 L'"}},
        ]
    ]

    result = apply_ear_sequence(note_groups, sequence)

    assert result is not note_groups
    assert result[0] is not note_groups[0]
    assert result[0][0] is not note_groups[0][0]
    assert result[0][0]["metadata"] is not note_groups[0][0]["metadata"]
    assert result[0][0]["expected_ear_label_code"] == "R_PRIME"
    assert result[0][1]["expected_ear_label_code"] is None
    assert result[0][2]["expected_ear_label_code"] == "L_PRIME"
    assert "expected_ear_label_code" not in note_groups[0][0]


def test_crossed_out_mouse_line_interprets_as_dead_under_rule():
    assert interpret_crossed_out_status("double", "dead") == "dead"
    assert interpret_crossed_out_status("single", "dead") == "dead"
    assert interpret_crossed_out_status("none", "dead") == "active"


def test_crossed_out_status_requires_review_when_not_dead_or_none():
    assert interpret_crossed_out_status("single", "review") == "review"
    assert interpret_crossed_out_status("double", "ignore") == "review"
    assert interpret_crossed_out_status("smudged", "dead") == "review"


def test_sample_id_matches_mouse_display_id():
    mice = [{"mouse_id": "mouse_24", "display_id": "24"}]
    samples = [{"sample_id": "24", "target_name": "ApoM-tg"}]

    [match] = match_samples_to_mice(samples, mice)

    assert match["match_status"] == "matched"
    assert match["mouse_id"] == "mouse_24"


def test_duplicate_sample_match_requires_review():
    mice = [
        {"mouse_id": "mouse_a", "display_id": "24"},
        {"mouse_id": "mouse_b", "display_id": "24"},
    ]
    samples = [{"sample_id": "24", "target_name": "ApoM-tg"}]

    [match] = match_samples_to_mice(samples, mice)

    assert match["match_status"] == "duplicate_mouse_match"
    assert match["mouse_id"] is None


def test_blank_sample_id_stays_unmatched():
    mice = [
        {"mouse_id": "mouse_blank", "display_id": ""},
        {"mouse_id": "mouse_missing"},
    ]
    samples = [{"sample_id": ""}, {}]

    matches = match_samples_to_mice(samples, mice)

    assert [match["match_status"] for match in matches] == ["unmatched", "unmatched"]
    assert [match["mouse_id"] for match in matches] == [None, None]
