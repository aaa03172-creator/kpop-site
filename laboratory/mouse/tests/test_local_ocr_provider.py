from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "local_ocr_provider.py"


def load_provider_module():
    spec = importlib.util.spec_from_file_location("local_ocr_provider", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tesseract_provider_reports_unavailable_without_external_fallback(
    monkeypatch,
) -> None:
    provider = load_provider_module()
    monkeypatch.setattr(provider.shutil, "which", lambda _name: None)

    status = provider.tesseract_provider_status()

    assert status == {
        "provider": "tesseract_cli",
        "available": False,
        "external_inference_used": False,
        "mode": "unavailable",
        "skip_reason": "tesseract executable is not available on PATH.",
    }


def test_tesseract_provider_reports_available_path(monkeypatch) -> None:
    provider = load_provider_module()
    monkeypatch.setattr(provider.shutil, "which", lambda _name: "C:/tools/tesseract.exe")

    status = provider.tesseract_provider_status()

    assert status == {
        "provider": "tesseract_cli",
        "available": True,
        "external_inference_used": False,
        "mode": "local_ocr",
        "executable": "C:/tools/tesseract.exe",
    }
