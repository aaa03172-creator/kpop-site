from __future__ import annotations

import importlib.util
import subprocess
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


def test_extract_text_skips_when_tesseract_is_unavailable(monkeypatch, tmp_path: Path) -> None:
    provider = load_provider_module()
    image_path = tmp_path / "card.jpg"
    image_path.write_bytes(b"fake jpeg")
    monkeypatch.setattr(provider.shutil, "which", lambda _name: None)

    result = provider.extract_text_with_tesseract(image_path)

    assert result == {
        "provider": "tesseract_cli",
        "available": False,
        "external_inference_used": False,
        "mode": "unavailable",
        "status": "skipped",
        "text": "",
        "skip_reason": "tesseract executable is not available on PATH.",
    }


def test_extract_text_runs_tesseract_stdout_command(monkeypatch, tmp_path: Path) -> None:
    provider = load_provider_module()
    image_path = tmp_path / "card.jpg"
    image_path.write_bytes(b"fake jpeg")
    calls = []

    def fake_run(command, check, capture_output, text, timeout):
        calls.append(
            {
                "command": command,
                "check": check,
                "capture_output": capture_output,
                "text": text,
                "timeout": timeout,
            }
        )
        return subprocess.CompletedProcess(command, 0, stdout="Strain B6J\n101 R'\n", stderr="")

    monkeypatch.setattr(provider.shutil, "which", lambda _name: "C:/tools/tesseract.exe")
    monkeypatch.setattr(provider.subprocess, "run", fake_run)

    result = provider.extract_text_with_tesseract(image_path, lang="eng", psm=6, timeout_seconds=12)

    assert calls == [
        {
            "command": [
                "C:/tools/tesseract.exe",
                str(image_path),
                "stdout",
                "-l",
                "eng",
                "--psm",
                "6",
            ],
            "check": False,
            "capture_output": True,
            "text": True,
            "timeout": 12,
        }
    ]
    assert result == {
        "provider": "tesseract_cli",
        "available": True,
        "external_inference_used": False,
        "mode": "local_ocr",
        "status": "ok",
        "text": "Strain B6J\n101 R'",
        "stderr": "",
        "returncode": 0,
    }


def test_extract_text_reports_tesseract_failure(monkeypatch, tmp_path: Path) -> None:
    provider = load_provider_module()
    image_path = tmp_path / "card.jpg"
    image_path.write_bytes(b"fake jpeg")

    def fake_run(command, check, capture_output, text, timeout):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="cannot read image")

    monkeypatch.setattr(provider.shutil, "which", lambda _name: "C:/tools/tesseract.exe")
    monkeypatch.setattr(provider.subprocess, "run", fake_run)

    result = provider.extract_text_with_tesseract(image_path)

    assert result["status"] == "failed"
    assert result["external_inference_used"] is False
    assert result["text"] == ""
    assert result["stderr"] == "cannot read image"
    assert result["returncode"] == 1
