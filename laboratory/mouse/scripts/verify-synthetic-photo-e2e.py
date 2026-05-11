from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_synthetic_cage_card_fixtures import generate  # noqa: E402


def remove_tree_with_retries(path: Path, attempts: int = 5) -> None:
    gc.collect()
    for attempt in range(attempts):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.2 * (attempt + 1))
            gc.collect()


def load_photo_verifier() -> Any:
    script_path = ROOT / "scripts" / "verify-photo-e2e-cases.py"
    spec = importlib.util.spec_from_file_location("verify_photo_e2e_cases", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load verifier script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(output_dir: Path) -> dict[str, Any]:
    generated = generate(output_dir)
    verifier = load_photo_verifier()
    manifest_path = Path(generated["manifest"])
    db_path = Path(generated["database"])
    manifest = verifier.load_manifest(manifest_path)
    missing_tables = verifier.missing_fixture_tables(db_path)
    if missing_tables:
        verification = verifier.build_missing_fixture_summary(
            manifest=manifest,
            manifest_path=manifest_path,
            missing_tables=missing_tables,
            require_fixtures=True,
        )
        exit_code = verifier.missing_fixture_exit_code(verification)
    else:
        results, fail_count = verifier.verify(manifest, db_path)
        verification = verifier.build_summary(
            manifest=manifest,
            manifest_path=manifest_path,
            results=results,
            fail_count=fail_count,
        )
        exit_code = 1 if fail_count else 0
    return {
        "boundary": "review item / test fixture",
        "canonical": False,
        "generated": generated,
        "verification": verification,
        "exit_code": exit_code,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and verify synthetic cage-card JPEG fixtures.")
    parser.add_argument("--output-dir", default="", help="Directory for generated disposable fixtures.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    temp_dir = None
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        temp_dir = Path(tempfile.mkdtemp(prefix="synthetic-cage-cards-"))
        output_dir = temp_dir
    try:
        summary = verify(output_dir)
        if args.json:
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            verification = summary["verification"]
            print(
                "Synthetic photo E2E validation: "
                f"{verification['passed']}/{verification['case_count']} passed, "
                f"{verification['failed']} failed"
            )
        return int(summary["exit_code"])
    finally:
        if temp_dir is not None and temp_dir.exists():
            remove_tree_with_retries(temp_dir)


if __name__ == "__main__":
    raise SystemExit(main())
