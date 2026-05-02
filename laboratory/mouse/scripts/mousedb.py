from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "--data-dir":
        data_dir = Path(args[1])
        db_path = data_dir / "mousedb.sqlite"
        sys.argv = [sys.argv[0], "--db", str(db_path), *args[2:]]

    from mousedb.cli import app

    app()


if __name__ == "__main__":
    main()
