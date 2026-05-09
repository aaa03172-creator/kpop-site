from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_TRUE_EXPECTATIONS = [
    "must_route_to_review",
    "must_preserve_traceability",
    "must_not_write_canonical",
]

ALLOWED_BOUNDARIES = {
    "raw source",
    "parsed or intermediate result",
    "canonical structured state",
    "review item",
    "review item / test fixture",
    "export or view",
    "cache",
}


def load_probe(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(
            f"{path} must use JSON-compatible YAML for this dependency-free PoC: {error}"
        ) from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one probe object.")
    return value


def evaluate_probe(probe: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    failures: list[str] = []
    probe_id = str(probe.get("probe_id") or (path.stem if path else "unknown"))
    expected = probe.get("expected")

    if probe.get("canonical") is not False:
        failures.append("canonical must be false for evaluation probes")
    if probe.get("boundary") != "review item / test fixture":
        failures.append("boundary must be 'review item / test fixture'")
    if not isinstance(expected, dict):
        failures.append("expected must be an object")
        expected = {}

    boundary = expected.get("boundary")
    if boundary not in ALLOWED_BOUNDARIES:
        failures.append("expected.boundary must be a known project data boundary")
    for key in REQUIRED_TRUE_EXPECTATIONS:
        if expected.get(key) is not True:
            failures.append(f"expected.{key} must be true")
    if expected.get("external_inference_policy") not in {"local_only", "local_or_approved_only"}:
        failures.append("expected.external_inference_policy must be local_only or local_or_approved_only")

    return {
        "probe_id": probe_id,
        "taxonomy": probe.get("taxonomy", ""),
        "path": str(path) if path else "",
        "status": "fail" if failures else "pass",
        "failures": failures,
    }


def evaluate_probe_file(path: Path) -> dict[str, Any]:
    return evaluate_probe(load_probe(path), path)


def discover_probe_files(probes_dir: Path) -> list[Path]:
    return sorted([*probes_dir.glob("*.yaml"), *probes_dir.glob("*.yml"), *probes_dir.glob("*.json")])


def build_report(probes_dir: Path) -> dict[str, Any]:
    results = [evaluate_probe_file(path) for path in discover_probe_files(probes_dir)]
    passed = sum(1 for result in results if result["status"] == "pass")
    failed = sum(1 for result in results if result["status"] == "fail")
    return {
        "boundary": "review item / test fixture",
        "canonical": False,
        "harness": "cage_card_skill_gym",
        "summary": {"passed": passed, "failed": failed, "total": len(results)},
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run MouseDB Ctx2Skill-lite cage-card probe checks.")
    parser.add_argument("--probes", default=str(Path(__file__).with_name("probes")), help="Probe directory.")
    args = parser.parse_args(argv)

    report = build_report(Path(args.probes))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
