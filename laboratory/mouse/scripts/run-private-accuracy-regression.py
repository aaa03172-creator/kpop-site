from __future__ import annotations

import argparse
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPORTER_PATH = ROOT / "scripts" / "export-review-scoring-audit-input.py"
REPORTER_PATH = ROOT / "scripts" / "report-private-accuracy.py"
BOUNDARY = "review item / private accuracy regression runner"
COMPARISON_BOUNDARY = "review item / private accuracy regression comparison"
KEY_METRICS = [
    "decision",
    "case_count",
    "matched_case_count",
    "missing_result_case_count",
    "extra_result_case_count",
    "failure_taxonomy_counts",
    "workflow_metrics",
    "workload",
    "hybrid_note_line_evaluator_metrics",
    "field_family_scores",
    "hard_gates",
    "result_validation_failures",
]


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sanitized_suffix(value: str) -> str:
    suffix = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return suffix or "private-accuracy-regression"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def private_filename(path: Path | str | None) -> str:
    return Path(path).name if path else ""


def field_outcome_integrity(results_path: Path | str) -> dict[str, Any]:
    payload = json.loads(Path(results_path).read_text(encoding="utf-8"))
    missing_scope = []
    empty_scoped = []
    invalid_scoring_status = []
    scored_scope_missing_scored_cases = []
    cases = payload.get("cases") if isinstance(payload.get("cases"), list) else []
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id") or "")
        audit = case.get("review_resolution_scoring_audit")
        if not isinstance(audit, dict):
            audit = {}
        scope = str(audit.get("note_line_scoring_scope") or "").strip()
        fields = case.get("field_scores") if isinstance(case.get("field_scores"), dict) else {}
        labels = case.get("failure_labels") if isinstance(case.get("failure_labels"), list) else []
        has_scoring = bool(fields) or bool(labels)
        if has_scoring and not scope:
            missing_scope.append(case_id)
        if scope and not has_scoring:
            empty_scoped.append(case_id)
        if case.get("scoring_status") != "review_resolution_audit_exported":
            invalid_scoring_status.append(case_id)
        scored_cases = []
        evaluator = case.get("hybrid_note_line_evaluator")
        if isinstance(evaluator, dict) and isinstance(evaluator.get("scored_cases"), list):
            scored_cases = evaluator["scored_cases"]
        if scope == "scored_note_line" and not scored_cases:
            scored_scope_missing_scored_cases.append(case_id)
    return {
        "case_count": len(cases),
        "missing_scope": missing_scope,
        "empty_scoped": empty_scoped,
        "invalid_scoring_status": invalid_scoring_status,
        "scored_scope_missing_scored_cases": scored_scope_missing_scored_cases,
    }


def field_outcome_integrity_status(integrity: dict[str, Any]) -> str:
    return (
        "passed"
        if (
            not integrity.get("missing_scope")
            and not integrity.get("empty_scoped")
            and not integrity.get("invalid_scoring_status")
            and not integrity.get("scored_scope_missing_scored_cases")
        )
        else "failed"
    )


def regression_gate_status(
    *,
    report_status: str,
    integrity: dict[str, Any],
    comparison: dict[str, Any],
) -> dict[str, Any]:
    integrity_status = field_outcome_integrity_status(integrity)
    comparison_match = comparison.get("all_key_metrics_match") if comparison else True
    status = (
        "passed"
        if report_status == "passed" and integrity_status == "passed" and comparison_match is True
        else "failed"
    )
    return {
        "status": status,
        "report_status": report_status,
        "field_outcome_integrity_status": integrity_status,
        "comparison_all_key_metrics_match": comparison_match,
    }


def baseline_promotion_status(
    *,
    gate: dict[str, Any],
    decision: str,
    matched_case_count: int,
    unmatched_audit_count: int,
    missing_result_case_count: int,
    extra_result_case_count: int,
    result_validation_failures: int,
    comparison: dict[str, Any],
    report_hard_gate_failures: list[str],
    results_path: Path | str,
    baseline_results_path: Path | str | None,
) -> dict[str, Any]:
    blocked_reasons = []
    if gate.get("status") != "passed":
        blocked_reasons.append("regression_gate_failed")
    if decision != "go":
        blocked_reasons.append("decision_not_go")
    if matched_case_count <= 0:
        blocked_reasons.append("no_matched_cases")
    if unmatched_audit_count:
        blocked_reasons.append("unmatched_audit")
    if missing_result_case_count or extra_result_case_count:
        blocked_reasons.append("result_case_mismatch")
    if result_validation_failures:
        blocked_reasons.append("result_validation_failures")
    if not baseline_results_path:
        blocked_reasons.append("baseline_results_required")
    if comparison and comparison.get("all_key_metrics_match") is not True:
        blocked_reasons.append("baseline_comparison_mismatch")
    for gate_name in report_hard_gate_failures:
        blocked_reasons.append(f"{gate_name}_failed")
    eligible = not blocked_reasons
    return {
        "eligible": eligible,
        "status": "ready_for_operator_promotion" if eligible else "blocked",
        "recommended_action": (
            "operator_may_promote_current_results_to_baseline_after_review"
            if eligible
            else "do_not_promote_baseline"
        ),
        "candidate_results_filename": private_filename(results_path),
        "current_baseline_filename": private_filename(baseline_results_path),
        "blocked_reasons": blocked_reasons,
    }


def history_record(
    *,
    safe_suffix: str,
    summary: dict[str, Any],
    results_path: Path | str,
    report_path: Path | str,
    comparison_path: Path | str,
    baseline_results_path: Path | str | None,
) -> dict[str, Any]:
    comparison = summary.get("comparison") if isinstance(summary.get("comparison"), dict) else {}
    return {
        "run_id": safe_suffix,
        "recorded_at": utc_timestamp(),
        "boundary": BOUNDARY,
        "canonical": False,
        "run_label": summary.get("run_label"),
        "status": summary.get("status"),
        "decision": summary.get("decision"),
        "matched_case_count": summary.get("matched_case_count"),
        "unmatched_audit_count": summary.get("unmatched_audit_count"),
        "missing_result_case_count": summary.get("missing_result_case_count"),
        "extra_result_case_count": summary.get("extra_result_case_count"),
        "result_validation_failures": summary.get("result_validation_failures"),
        "report_hard_gate_failures": summary.get("report_hard_gate_failures"),
        "field_outcome_integrity": summary.get("field_outcome_integrity"),
        "regression_gate": summary.get("regression_gate"),
        "comparison": {
            "all_key_metrics_match": comparison.get("all_key_metrics_match") if comparison else None,
            "matches": comparison.get("matches") if comparison else {},
        },
        "baseline_promotion": summary.get("baseline_promotion"),
        "artifacts": {
            "results_filename": private_filename(results_path),
            "report_filename": private_filename(report_path),
            "comparison_filename": private_filename(comparison_path) if baseline_results_path else "",
        },
    }


UNSAFE_HISTORY_MARKERS = (
    "SECRET_",
    "source_photo_path",
    "raw_payload",
    "rawText",
    "C:\\",
    "C:/",
    "\\Users\\",
    "/Users/",
    "카카오",
)

UNSAFE_HISTORY_KEYS = {
    "private_path",
    "raw_payload",
    "rawText",
    "source_photo_path",
    "source_photo_filename",
    "reviewer_note",
    "review_note",
}

HISTORY_FIELD_OUTCOME_KEYS = {
    "case_count",
    "missing_scope",
    "empty_scoped",
    "invalid_scoring_status",
    "scored_scope_missing_scored_cases",
}


def is_unsafe_history_text(value: str) -> bool:
    return any(marker in value for marker in UNSAFE_HISTORY_MARKERS)


def safe_history_count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def safe_history_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def safe_history_reason(value: Any) -> str | None:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9_]+", value):
        return None
    return None if is_unsafe_history_text(value) else value


def safe_history_label(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    if is_unsafe_history_text(value) or not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        return None
    return value[:200]


def safe_history_timestamp(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    if is_unsafe_history_text(value) or not re.fullmatch(r"[0-9TZ:.-]+", value):
        return None
    return value


def safe_history_reason_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [reason for item in value if (reason := safe_history_reason(item))]


def safe_history_filename(value: Any, suffixes: tuple[str, ...]) -> str | None:
    if not isinstance(value, str):
        return None
    if is_unsafe_history_text(value) or "/" in value or "\\" in value or ":" in value:
        return None
    if value == "":
        return "" if "" in suffixes else None
    allowed_suffixes = tuple(suffix for suffix in suffixes if suffix)
    if not allowed_suffixes or not value.endswith(allowed_suffixes):
        return None
    return value


def sanitize_field_outcome_integrity(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    sanitized = {}
    if (case_count := safe_history_count(value.get("case_count"))) is not None:
        sanitized["case_count"] = case_count
    for key in HISTORY_FIELD_OUTCOME_KEYS - {"case_count"}:
        sanitized[key] = safe_history_reason_list(value.get(key))
    return sanitized


def sanitize_regression_gate(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    sanitized = {}
    for key in {"status", "report_status", "field_outcome_integrity_status"}:
        if status := safe_history_reason(value.get(key)):
            sanitized[key] = status
    if (comparison_match := safe_history_bool(value.get("comparison_all_key_metrics_match"))) is not None:
        sanitized["comparison_all_key_metrics_match"] = comparison_match
    return sanitized


def sanitize_comparison(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    sanitized = {}
    if (all_match := safe_history_bool(value.get("all_key_metrics_match"))) is not None:
        sanitized["all_key_metrics_match"] = all_match
    matches = value.get("matches")
    if isinstance(matches, dict):
        sanitized["matches"] = {
            metric: matched
            for key, matched in matches.items()
            if (metric := safe_history_reason(key)) and isinstance(matched, bool)
        }
    else:
        sanitized["matches"] = {}
    return sanitized


def sanitize_baseline_promotion(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    sanitized = {}
    if (eligible := safe_history_bool(value.get("eligible"))) is not None:
        sanitized["eligible"] = eligible
    for key in {"status", "recommended_action"}:
        if status := safe_history_reason(value.get(key)):
            sanitized[key] = status
    for key in {"candidate_results_filename", "current_baseline_filename"}:
        if filename := safe_history_filename(value.get(key), (".json", "")):
            sanitized[key] = filename
    sanitized["blocked_reasons"] = safe_history_reason_list(value.get("blocked_reasons"))
    return sanitized


def sanitize_history_artifacts(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    suffixes = {
        "results_filename": (".json",),
        "report_filename": (".md",),
        "comparison_filename": (".json", ""),
    }
    sanitized = {}
    for key, allowed_suffixes in suffixes.items():
        if filename := safe_history_filename(value.get(key), allowed_suffixes):
            sanitized[key] = filename
    return sanitized


def sanitize_history_run(run: Any) -> dict[str, Any] | None:
    if not isinstance(run, dict) or not run.get("run_id"):
        return None
    run_id = safe_history_label(run.get("run_id"))
    if not run_id:
        return None
    sanitized: dict[str, Any] = {"run_id": run_id}
    if recorded_at := safe_history_timestamp(run.get("recorded_at")):
        sanitized["recorded_at"] = recorded_at
    boundary = run.get("boundary")
    if boundary in {BOUNDARY, "review item / private accuracy regression history"}:
        sanitized["boundary"] = boundary
    if (canonical := safe_history_bool(run.get("canonical"))) is not None:
        sanitized["canonical"] = canonical
    if run_label := safe_history_label(run.get("run_label")):
        sanitized["run_label"] = run_label
    for key in {"status", "decision"}:
        if value := safe_history_reason(run.get(key)):
            sanitized[key] = value
    for key in {
        "matched_case_count",
        "unmatched_audit_count",
        "missing_result_case_count",
        "extra_result_case_count",
        "result_validation_failures",
    }:
        if (count := safe_history_count(run.get(key))) is not None:
            sanitized[key] = count
    sanitized["report_hard_gate_failures"] = safe_history_reason_list(run.get("report_hard_gate_failures"))
    nested_specs = {
        "field_outcome_integrity": sanitize_field_outcome_integrity,
        "regression_gate": sanitize_regression_gate,
        "comparison": sanitize_comparison,
        "baseline_promotion": sanitize_baseline_promotion,
        "artifacts": sanitize_history_artifacts,
    }
    for key, sanitizer in nested_specs.items():
        if key in run:
            sanitized[key] = sanitizer(run[key])
    encoded = json.dumps(sanitized, ensure_ascii=False)
    if any(marker in encoded for marker in UNSAFE_HISTORY_MARKERS):
        return None
    return sanitized


def update_history_index(
    *,
    history_path: Path | str,
    record: dict[str, Any],
    baseline_results_path: Path | str | None,
) -> None:
    path = Path(history_path)
    if path.exists():
        try:
            history = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            history = {}
    else:
        history = {}
    existing_runs = history.get("runs") if isinstance(history.get("runs"), list) else []
    runs = []
    for existing_run in existing_runs:
        sanitized_run = sanitize_history_run(existing_run)
        if sanitized_run and sanitized_run.get("run_id") != record.get("run_id"):
            runs.append(sanitized_run)
    runs.append(record)
    history = {
        "layer": "review item / private accuracy regression history",
        "canonical": False,
        "source_policy": (
            "Local-only sanitized run history. Raw photos, private paths, raw OCR/AI text, "
            "and full private result payloads are omitted."
        ),
        "updated_at": record["recorded_at"],
        "latest_run_label": record["run_id"],
        "run_count": len(runs),
        "baseline": {
            "current_filename": private_filename(baseline_results_path),
            "promotion_policy": (
                "Promote only after operator review when the regression gate passes, decision is go, "
                "field outcome integrity passes, and all baseline comparison metrics match."
            ),
        },
        "runs": runs,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def compare_reports(
    *,
    manifest_path: Path | str,
    baseline_results_path: Path | str,
    new_results_path: Path | str,
    comparison_path: Path | str,
) -> dict[str, Any]:
    reporter = load_module(REPORTER_PATH, "report_private_accuracy_for_regression_compare")
    old_report = reporter.build_report(manifest_path=manifest_path, results_path=baseline_results_path)
    new_report = reporter.build_report(manifest_path=manifest_path, results_path=new_results_path)
    comparison = {
        "boundary": COMPARISON_BOUNDARY,
        "canonical": False,
        "matches": {},
        "old": {},
        "new": {},
    }
    for key in KEY_METRICS:
        old_value = old_report.get(key)
        new_value = new_report.get(key)
        matched = old_value == new_value
        comparison["matches"][key] = matched
        if not matched:
            comparison["old"][key] = old_value
            comparison["new"][key] = new_value
    comparison["all_key_metrics_match"] = all(comparison["matches"].values())
    output = Path(comparison_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")
    return comparison


def run_private_accuracy_regression(
    *,
    db_path: Path | str,
    manifest_path: Path | str,
    run_dir: Path | str,
    run_label: str,
    suffix: str,
    baseline_results_path: Path | str | None = None,
    history_index_path: Path | str | None = None,
) -> dict[str, Any]:
    safe_suffix = sanitized_suffix(suffix)
    output_dir = Path(run_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / f"review-scoring-audit-export-input-{safe_suffix}.json"
    report_path = output_dir / f"sanitized-private-accuracy-{safe_suffix}.md"
    comparison_path = output_dir / f"field-outcomes-regression-comparison-{safe_suffix}.json"

    exporter = load_module(EXPORTER_PATH, "export_review_scoring_audit_input_for_regression")
    reporter = load_module(REPORTER_PATH, "report_private_accuracy_for_regression")
    export_summary = exporter.export_review_scoring_audit_input(
        db_path=db_path,
        manifest_path=manifest_path,
        output_path=results_path,
        run_label=run_label,
    )
    report = reporter.build_report(manifest_path=manifest_path, results_path=results_path)
    report_path.write_text(
        reporter.build_markdown_report(run_label=run_label, summary=report),
        encoding="utf-8",
    )
    integrity = field_outcome_integrity(results_path)
    comparison = {}
    if baseline_results_path:
        comparison = compare_reports(
            manifest_path=manifest_path,
            baseline_results_path=baseline_results_path,
            new_results_path=results_path,
            comparison_path=comparison_path,
        )
    gate = regression_gate_status(
        report_status=str(report.get("status") or ""),
        integrity=integrity,
        comparison=comparison,
    )
    hard_gates = report.get("hard_gates") if isinstance(report.get("hard_gates"), dict) else {}
    hard_gate_failures = [
        str(name)
        for name, gate_summary in hard_gates.items()
        if isinstance(gate_summary, dict) and gate_summary.get("status") != "passed"
    ]
    summary = {
        "status": gate["status"],
        "decision": report.get("decision"),
        "boundary": BOUNDARY,
        "canonical": False,
        "run_label": export_summary.get("run_label"),
        "matched_case_count": export_summary.get("matched_case_count"),
        "unmatched_audit_count": export_summary.get("unmatched_audit_count"),
        "missing_result_case_count": report.get("missing_result_case_count"),
        "extra_result_case_count": report.get("extra_result_case_count"),
        "result_validation_failures": report.get("result_validation_failures"),
        "report_hard_gate_failures": hard_gate_failures,
        "field_outcome_integrity": integrity,
        "comparison": comparison,
        "regression_gate": gate,
        "output_path": "private output path omitted",
        "report_path": "private output path omitted",
        "comparison_path": "private output path omitted" if baseline_results_path else "",
        "history_index_path": "private output path omitted" if history_index_path else "",
        "history_update_status": "not_requested",
    }
    summary["baseline_promotion"] = baseline_promotion_status(
        gate=gate,
        decision=str(summary.get("decision") or ""),
        matched_case_count=int(summary.get("matched_case_count") or 0),
        unmatched_audit_count=int(summary.get("unmatched_audit_count") or 0),
        missing_result_case_count=int(summary.get("missing_result_case_count") or 0),
        extra_result_case_count=int(summary.get("extra_result_case_count") or 0),
        result_validation_failures=int(summary.get("result_validation_failures") or 0),
        comparison=comparison,
        report_hard_gate_failures=hard_gate_failures,
        results_path=results_path,
        baseline_results_path=baseline_results_path,
    )
    if history_index_path:
        record = history_record(
            safe_suffix=safe_suffix,
            summary=summary,
            results_path=results_path,
            report_path=report_path,
            comparison_path=comparison_path,
            baseline_results_path=baseline_results_path,
        )
        update_history_index(
            history_path=history_index_path,
            record=record,
            baseline_results_path=baseline_results_path,
        )
        summary["history_update_status"] = "updated"
    return summary


def redacted_error(exc: Exception, private_values: list[str]) -> str:
    error = str(exc)
    for value in private_values:
        if value:
            error = error.replace(value, "<private path>")
    return error


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a private field-outcome accuracy regression from review resolution audit metadata."
    )
    parser.add_argument("--db-path", required=True, help="Local SQLite database path.")
    parser.add_argument("--manifest", required=True, help="Private real-photo manifest path.")
    parser.add_argument("--run-dir", required=True, help="Private output directory.")
    parser.add_argument("--run-label", default="private-accuracy-regression", help="Sanitized run label.")
    parser.add_argument("--suffix", default="private-accuracy-regression", help="Output filename suffix.")
    parser.add_argument("--baseline-results", default="", help="Optional previous sanitized results JSON for key metric comparison.")
    parser.add_argument("--history-index", default="", help="Optional private local run history JSON path.")
    parser.add_argument("--json", action="store_true", help="Print sanitized JSON summary.")
    args = parser.parse_args()

    private_values = [args.db_path, args.manifest, args.run_dir, args.baseline_results, args.history_index]
    try:
        summary = run_private_accuracy_regression(
            db_path=Path(args.db_path),
            manifest_path=Path(args.manifest),
            run_dir=Path(args.run_dir),
            run_label=args.run_label,
            suffix=args.suffix,
            baseline_results_path=Path(args.baseline_results) if args.baseline_results else None,
            history_index_path=Path(args.history_index) if args.history_index else None,
        )
    except Exception as exc:
        summary = {
            "status": "failed",
            "boundary": BOUNDARY,
            "canonical": False,
            "error": redacted_error(exc, private_values),
            "output_path": "private output path omitted",
        }
        if args.json:
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            print(f"status: {summary['status']}")
            print(f"error: {summary['error']}")
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"status: {summary['status']}")
        print(f"decision: {summary['decision']}")
        print(f"matched_case_count: {summary['matched_case_count']}")
        print(f"unmatched_audit_count: {summary['unmatched_audit_count']}")
    return 0 if summary.get("status") == "passed" and summary.get("decision") in {"go", "narrow_rerun"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
