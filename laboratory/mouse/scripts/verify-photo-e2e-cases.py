import argparse
from contextlib import closing
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import db  # noqa: E402
from app.main import list_review_items, review_attention_level, review_check_targets  # noqa: E402

MANIFEST_PATH = ROOT / "config" / "photo_e2e_validation_cases.json"
REQUIRED_TABLES = {"photo_log", "parse_result", "card_note_item_log", "review_queue"}


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_json_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    value = json.loads(raw)
    return value if isinstance(value, dict) else {}


def missing_fixture_tables(db_path: Path | None = None) -> list[str]:
    selected_db_path = db_path or db.DB_PATH
    if not selected_db_path.exists():
        return sorted(REQUIRED_TABLES)
    with closing(sqlite3.connect(selected_db_path)) as conn:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()
    existing = {str(row[0]) for row in rows}
    return sorted(REQUIRED_TABLES - existing)


def latest_parse(conn: sqlite3.Connection, photo_id: str, source_name: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT pr.parse_id, pr.photo_id, pr.source_name, pr.raw_payload, pr.parsed_at,
               pr.status, pr.confidence, pr.needs_review,
               pl.original_filename, pl.stored_path, pl.status AS photo_status
        FROM parse_result pr
        JOIN photo_log pl ON pl.photo_id = pr.photo_id
        WHERE pr.photo_id = ? AND pr.source_name = ?
        ORDER BY pr.parsed_at DESC
        LIMIT 1
        """,
        (photo_id, source_name),
    ).fetchone()


def stored_photo_path(stored_path: str) -> Path:
    path = Path(stored_path)
    if path.is_absolute():
        return path
    return ROOT / path


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def field_value(payload: dict[str, Any], field: str) -> Any:
    aliases = {
        "rawStrain": ["rawStrain", "raw_strain"],
        "mouseCount": ["mouseCount", "mouse_count"],
        "sexRaw": ["sexRaw", "sex_raw"],
        "dobRaw": ["dobRaw", "dob_raw"],
        "lmoRaw": ["lmoRaw", "lmo_raw"],
        "uncertainFields": ["uncertainFields", "uncertain_fields"],
    }
    for key in aliases.get(field, [field]):
        if key in payload:
            return payload[key]
    return None


def contains_all(actual: Any, needles: list[str]) -> tuple[bool, str]:
    text = as_text(actual)
    missing = [needle for needle in needles if needle not in text]
    if missing:
        return False, f"missing {missing!r} in {text!r}"
    return True, ""


def check_parse(case: dict[str, Any], row: sqlite3.Row, payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected = case.get("expected_parse", {})
    if expected.get("status") and row["status"] != expected["status"]:
        failures.append(f"parse status expected {expected['status']!r}, got {row['status']!r}")
    if "min_confidence" in expected and float(row["confidence"]) < float(expected["min_confidence"]):
        failures.append(
            f"confidence expected >= {expected['min_confidence']}, got {row['confidence']}"
        )
    if "max_confidence" in expected and float(row["confidence"]) > float(expected["max_confidence"]):
        failures.append(
            f"confidence expected <= {expected['max_confidence']}, got {row['confidence']}"
        )
    for field, needles in expected.get("field_contains", {}).items():
        ok, reason = contains_all(field_value(payload, field), list(needles))
        if not ok:
            failures.append(f"{field}: {reason}")
    uncertain = field_value(payload, "uncertainFields")
    uncertain_set = set(uncertain if isinstance(uncertain, list) else [])
    for field in expected.get("uncertain_fields_include", []):
        if field not in uncertain_set:
            failures.append(f"uncertainFields missing {field!r}: {sorted(uncertain_set)!r}")
    return failures


def check_photo(case: dict[str, Any], row: sqlite3.Row) -> list[str]:
    failures: list[str] = []
    if row["original_filename"] != case["photo_filename"]:
        failures.append(
            f"photo filename expected {case['photo_filename']!r}, got {row['original_filename']!r}"
        )
    path = stored_photo_path(row["stored_path"])
    if not path.exists():
        failures.append(f"stored photo missing: {path}")
        return failures
    min_bytes = int(case.get("min_photo_bytes", 0))
    size = path.stat().st_size
    if size < min_bytes:
        failures.append(f"stored photo too small: expected >= {min_bytes} bytes, got {size}")
    return failures


def check_note_items(
    conn: sqlite3.Connection,
    case: dict[str, Any],
    parse_id: str,
) -> list[str]:
    failures: list[str] = []
    rows = conn.execute(
        """
        SELECT raw_line_text, parsed_ear_label_code, parsed_ear_label_review_status
        FROM card_note_item_log
        WHERE parse_id = ?
        ORDER BY line_number
        """,
        (parse_id,),
    ).fetchall()
    by_raw = {row["raw_line_text"]: row for row in rows}
    for expected in case.get("expected_note_items", []):
        raw_line = expected["raw_line_text"]
        row = by_raw.get(raw_line)
        if row is None:
            failures.append(f"note item missing raw line {raw_line!r}")
            continue
        for key in ("parsed_ear_label_code", "parsed_ear_label_review_status"):
            if key in expected and row[key] != expected[key]:
                failures.append(
                    f"note {raw_line!r} {key} expected {expected[key]!r}, got {row[key]!r}"
                )
    return failures


def open_review_index(db_path: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    by_parse: dict[str, list[dict[str, Any]]] = {}
    if db_path is not None and db_path != db.DB_PATH:
        with closing(sqlite3.connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT review.review_id, review.parse_id, review.severity, review.issue,
                       review.current_value, review.suggested_value, review.review_reason,
                       review.status, review.created_at, review.resolved_at,
                       review.resolution_note, parse.raw_payload, parse.source_name,
                       parse.photo_id, parse.confidence
                FROM review_queue review
                LEFT JOIN parse_result parse ON parse.parse_id = review.parse_id
                """
            ).fetchall()
        for row in rows:
            item = dict(row)
            parse_payload = parse_json_object(item.pop("raw_payload", "{}"))
            item.update(review_attention_level(item, parse_payload))
            item["review_check_targets"] = review_check_targets(item, parse_payload)
            if item.get("status") != "open":
                continue
            by_parse.setdefault(item.get("parse_id", ""), []).append(item)
        return by_parse

    for item in list_review_items():
        if item.get("status") != "open":
            continue
        by_parse.setdefault(item.get("parse_id", ""), []).append(item)
    return by_parse


def check_open_review(
    case: dict[str, Any],
    parse_id: str,
    reviews_by_parse: dict[str, list[dict[str, Any]]],
) -> list[str]:
    failures: list[str] = []
    expected = case.get("expected_open_review")
    if not expected:
        return failures
    reviews = reviews_by_parse.get(parse_id, [])
    if not reviews:
        return [f"open review missing for parse {parse_id}"]
    attention_levels = {str(review.get("attention_level")) for review in reviews}
    for level in expected.get("attention_levels_include", []):
        if level not in attention_levels:
            failures.append(f"open review attention missing {level!r}: {sorted(attention_levels)!r}")
    targets = {
        target
        for review in reviews
        for target in (review.get("review_check_targets") or [])
    }
    for target in expected.get("targets_include", []):
        if target not in targets:
            failures.append(f"open review target missing {target!r}: {sorted(targets)!r}")
    return failures


def verify(manifest: dict[str, Any], db_path: Path | None = None) -> tuple[list[dict[str, Any]], int]:
    selector = manifest.get("latest_parse_selector", {})
    source_name = selector.get("source_name", "ai_photo_extraction")
    reviews_by_parse = open_review_index(db_path)
    results: list[dict[str, Any]] = []
    fail_count = 0
    with closing(sqlite3.connect(db_path or db.DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        for case in manifest.get("cases", []):
            failures: list[str] = []
            row = latest_parse(conn, case["photo_id"], source_name)
            if row is None:
                failures.append(f"latest parse missing for photo {case['photo_id']}")
                results.append(
                    {
                        "case_id": case["case_id"],
                        "status": "FAIL",
                        "photo_id": case["photo_id"],
                        "parse_id": None,
                        "failures": failures,
                    }
                )
                fail_count += 1
                continue
            payload = parse_json_object(row["raw_payload"])
            failures.extend(check_photo(case, row))
            failures.extend(check_parse(case, row, payload))
            failures.extend(check_note_items(conn, case, row["parse_id"]))
            failures.extend(check_open_review(case, row["parse_id"], reviews_by_parse))
            status = "PASS" if not failures else "FAIL"
            if failures:
                fail_count += 1
            results.append(
                {
                    "case_id": case["case_id"],
                    "status": status,
                    "photo_id": case["photo_id"],
                    "parse_id": row["parse_id"],
                    "confidence": row["confidence"],
                    "failures": failures,
                }
            )
    return results, fail_count


def confidence_calibration_summary(manifest: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    confidences = [
        float(result["confidence"])
        for result in results
        if result.get("confidence") is not None
    ]
    cases_by_id = {
        case.get("case_id"): case
        for case in manifest.get("cases", [])
        if case.get("case_id")
    }
    guard_cases = [
        result["case_id"]
        for result in results
        if "max_confidence" in cases_by_id.get(result.get("case_id"), {}).get("expected_parse", {})
    ]
    coverage = coverage_summary(manifest)
    if not confidences:
        return {
            "case_count": 0,
            "min_confidence": None,
            "max_confidence": None,
            "average_confidence": None,
            "bands": {
                "0_20_must_review": 0,
                "21_59_review": 0,
                "60_100_clearer": 0,
            },
            "low_confidence_guard_cases": guard_cases,
            "coverage": coverage,
        }
    return {
        "case_count": len(confidences),
        "min_confidence": min(confidences),
        "max_confidence": max(confidences),
        "average_confidence": round(sum(confidences) / len(confidences), 2),
        "bands": {
            "0_20_must_review": len([value for value in confidences if value <= 20]),
            "21_59_review": len([value for value in confidences if 20 < value < 60]),
            "60_100_clearer": len([value for value in confidences if value >= 60]),
        },
        "low_confidence_guard_cases": guard_cases,
        "coverage": coverage,
    }


def coverage_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    recommended_tags = [
        str(tag)
        for tag in manifest.get("recommended_coverage_tags", [])
        if str(tag).strip()
    ]
    case_tags = {}
    covered_tags: list[str] = []
    for case in manifest.get("cases", []):
        case_id = str(case.get("case_id") or "")
        tags = [
            str(tag)
            for tag in case.get("coverage_tags", [])
            if str(tag).strip()
        ]
        if case_id:
            case_tags[case_id] = tags
        for tag in tags:
            if tag not in covered_tags:
                covered_tags.append(tag)
    return {
        "recommended_tags": recommended_tags,
        "covered_tags": covered_tags,
        "missing_tags": [tag for tag in recommended_tags if tag not in covered_tags],
        "case_tags": case_tags,
    }


def build_summary(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    results: list[dict[str, Any]],
    fail_count: int,
) -> dict[str, Any]:
    return {
        "manifest": str(manifest_path.resolve()),
        "case_count": len(results),
        "passed": len([result for result in results if result["status"] == "PASS"]),
        "failed": fail_count,
        "skipped": 0,
        "boundary": manifest.get("boundary", "review item / test fixture"),
        "source_policy": manifest.get("source_policy", ""),
        "confidence_calibration": confidence_calibration_summary(manifest, results),
        "results": results,
    }


def build_missing_fixture_summary(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    missing_tables: list[str],
    require_fixtures: bool = False,
) -> dict[str, Any]:
    case_count = len(manifest.get("cases", []))
    summary = {
        "manifest": str(manifest_path.resolve()),
        "case_count": case_count,
        "passed": 0,
        "failed": case_count if require_fixtures else 0,
        "skipped": 0 if require_fixtures else case_count,
        "missing_tables": missing_tables,
        "skip_reason": "" if require_fixtures else (
            "Local photo E2E fixture database is unavailable. "
            f"Missing table(s): {', '.join(missing_tables)}."
        ),
        "failure_reason": (
            "Local photo E2E fixtures are required for this accuracy gate. "
            f"Missing table(s): {', '.join(missing_tables)}."
        ) if require_fixtures else "",
        "status": "failed" if require_fixtures else "skipped",
        "boundary": manifest.get("boundary", "review item / test fixture"),
        "source_policy": manifest.get("source_policy", ""),
    }
    return summary


def results_are_missing_fixture_parses(results: list[dict[str, Any]]) -> bool:
    if not results:
        return False
    return all(
        result.get("parse_id") is None
        and len(result.get("failures", [])) == 1
        and str(result["failures"][0]).startswith("latest parse missing for photo ")
        for result in results
    )


def build_missing_parse_fixture_summary(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    results: list[dict[str, Any]],
    require_fixtures: bool = False,
) -> dict[str, Any]:
    summary = build_missing_fixture_summary(
        manifest=manifest,
        manifest_path=manifest_path,
        missing_tables=[],
        require_fixtures=require_fixtures,
    )
    missing_photo_ids = [
        str(result.get("photo_id") or "")
        for result in results
        if result.get("photo_id")
    ]
    reason = (
        "Local photo E2E fixture database has the required schema but none of "
        "the expected photo parse rows."
    )
    summary["missing_photo_ids"] = missing_photo_ids
    summary["skip_reason"] = "" if require_fixtures else reason
    summary["failure_reason"] = f"{reason} Fixture rows are required for this accuracy gate." if require_fixtures else ""
    return summary


def missing_fixture_exit_code(summary: dict[str, Any]) -> int:
    return 1 if summary.get("status") == "failed" else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify real-photo cage-card extraction regression cases."
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), help="Validation manifest path.")
    parser.add_argument(
        "--db",
        "--db-path",
        dest="db",
        default=str(db.DB_PATH),
        help="Fixture SQLite database path.",
    )
    parser.add_argument(
        "--require-fixtures",
        action="store_true",
        help="Fail instead of skipping when the local photo E2E fixture database is unavailable.",
    )
    args = parser.parse_args()

    manifest = load_manifest(Path(args.manifest))
    db_path = Path(args.db)
    missing_tables = missing_fixture_tables(db_path)
    if missing_tables:
        summary = build_missing_fixture_summary(
            manifest=manifest,
            manifest_path=Path(args.manifest),
            missing_tables=missing_tables,
            require_fixtures=args.require_fixtures,
        )
        if args.json:
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        elif args.require_fixtures:
            print(
                "Photo E2E validation failed: local fixture database is required "
                f"(missing table(s): {', '.join(missing_tables)})."
            )
        else:
            print(
                "Photo E2E validation skipped: local fixture database is unavailable "
                f"(missing table(s): {', '.join(missing_tables)})."
            )
        return missing_fixture_exit_code(summary)
    results, fail_count = verify(manifest, db_path)
    if fail_count and results_are_missing_fixture_parses(results):
        summary = build_missing_parse_fixture_summary(
            manifest=manifest,
            manifest_path=Path(args.manifest),
            results=results,
            require_fixtures=args.require_fixtures,
        )
        if args.json:
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        elif args.require_fixtures:
            print(
                "Photo E2E validation failed: local fixture parse rows are required "
                f"(missing photo id(s): {', '.join(summary['missing_photo_ids'])})."
            )
        else:
            print(
                "Photo E2E validation skipped: local fixture parse rows are unavailable "
                f"(missing photo id(s): {', '.join(summary['missing_photo_ids'])})."
            )
        return missing_fixture_exit_code(summary)
    summary = build_summary(
        manifest=manifest,
        manifest_path=Path(args.manifest),
        results=results,
        fail_count=fail_count,
    )
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(
            f"Photo E2E validation: {summary['passed']}/{summary['case_count']} passed, "
            f"{summary['failed']} failed"
        )
        for result in results:
            print(
                f"- {result['status']} {result['case_id']} "
                f"photo={result['photo_id']} parse={result['parse_id']}"
            )
            for failure in result["failures"]:
                print(f"  - {failure}")
    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
