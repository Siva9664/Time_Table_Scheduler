"""
ocr_engine.py — OCR subsystem
Fallback text extraction using Tesseract OCR (pytesseract)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger


def _ocr_with_tesseract(path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image

        ext = path.suffix.lower()
        if ext == ".pdf":
            try:
                from pdf2image import convert_from_path

                images = convert_from_path(
                    str(path), dpi=200, first_page=1, last_page=6
                )
                texts = [pytesseract.image_to_string(img, lang="eng") for img in images]
                return "\n".join(texts)
            except Exception as exc:
                logger.warning(f"pdf2image failed: {exc}")
                return ""
        else:
            img = Image.open(str(path))
            return pytesseract.image_to_string(img, lang="eng")
    except ImportError:
        logger.warning("pytesseract not installed. OCR unavailable.")
        return ""
    except Exception as exc:
        logger.warning(f"Tesseract OCR failed: {exc}")
        return ""


def run_ocr(path: Path) -> str:
    """
    Run OCR on an image or scanned document using Tesseract.
    """
    logger.info(f"Running OCR on: {path.name}")
    text = _ocr_with_tesseract(path)
    if text.strip():
        logger.info(f"Tesseract extracted {len(text)} chars from {path.name}")
    else:
        logger.warning(f"OCR produced no output for {path.name}")
    return text
