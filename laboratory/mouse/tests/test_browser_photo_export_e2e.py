import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_package_exposes_browser_photo_to_export_e2e_script() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    assert package["scripts"]["test:browser-photo-export-e2e"] == (
        "node scripts/verify-browser-photo-export-e2e.js"
    )
    assert "npm run test:browser-photo-export-e2e" in package["scripts"]["verify"]
    assert (ROOT / "scripts" / "verify-browser-photo-export-e2e.js").exists()
