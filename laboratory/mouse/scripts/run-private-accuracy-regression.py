from __future__ import annotations

import argparse
import importlib.util
import json
import re
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


def field_outcome_integrity(results_path: Path | str) -> dict[str, Any]:
    payload = json.loads(Path(results_path).read_text(encoding="utf-8"))
    missing_scope = []
    empty_scoped = []
    invalid_scoring_status = []
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
    return {
        "case_count": len(cases),
        "missing_scope": missing_scope,
        "empty_scoped": empty_scoped,
        "invalid_scoring_status": invalid_scoring_status,
    }


def field_outcome_integrity_status(integrity: dict[str, Any]) -> str:
    return (
        "passed"
        if (
            not integrity.get("missing_scope")
            and not integrity.get("empty_scoped")
            and not integrity.get("invalid_scoring_status")
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

    return {
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
        "field_outcome_integrity": integrity,
        "comparison": comparison,
        "regression_gate": gate,
        "output_path": "private output path omitted",
        "report_path": "private output path omitted",
        "comparison_path": "private output path omitted" if baseline_results_path else "",
    }


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
    parser.add_argument("--json", action="store_true", help="Print sanitized JSON summary.")
    args = parser.parse_args()

    private_values = [args.db_path, args.manifest, args.run_dir, args.baseline_results]
    try:
        summary = run_private_accuracy_regression(
            db_path=Path(args.db_path),
            manifest_path=Path(args.manifest),
            run_dir=Path(args.run_dir),
            run_label=args.run_label,
            suffix=args.suffix,
            baseline_results_path=Path(args.baseline_results) if args.baseline_results else None,
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
