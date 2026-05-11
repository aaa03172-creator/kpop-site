from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def tesseract_provider_status() -> dict[str, object]:
    executable = shutil.which("tesseract")
    if not executable:
        return {
            "provider": "tesseract_cli",
            "available": False,
            "external_inference_used": False,
            "mode": "unavailable",
            "skip_reason": "tesseract executable is not available on PATH.",
        }
    return {
        "provider": "tesseract_cli",
        "available": True,
        "external_inference_used": False,
        "mode": "local_ocr",
        "executable": executable,
    }


def extract_text_with_tesseract(
    image_path: Path,
    *,
    lang: str = "eng",
    psm: int = 6,
    timeout_seconds: int = 30,
) -> dict[str, object]:
    status = tesseract_provider_status()
    if not status["available"]:
        return {
            "provider": "tesseract_cli",
            "available": False,
            "external_inference_used": False,
            "mode": "unavailable",
            "status": "skipped",
            "text": "",
            "skip_reason": str(status["skip_reason"]),
        }

    command = [
        str(status["executable"]),
        str(image_path),
        "stdout",
        "-l",
        lang,
        "--psm",
        str(psm),
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return {
        "provider": "tesseract_cli",
        "available": True,
        "external_inference_used": False,
        "mode": "local_ocr",
        "status": "ok" if completed.returncode == 0 else "failed",
        "text": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "returncode": completed.returncode,
    }
