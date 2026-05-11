from __future__ import annotations

import shutil


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
