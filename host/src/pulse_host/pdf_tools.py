from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Literal

import fitz
import pytesseract
from PIL import Image
from pypdf import PdfReader


@dataclass
class PdfExtractResult:
    source: str
    output: str
    pages_total: int
    pages_used: int
    chars: int
    method: str


OCRMode = Literal["off", "auto", "force"]


def extract_pdf_text(
    pdf_path: str,
    out_path: str | None = None,
    max_pages: int | None = None,
    ocr_mode: OCRMode = "auto",
    ocr_lang: str = "eng",
    ocr_dpi: int = 300,
) -> PdfExtractResult:
    src = Path(pdf_path)
    if not src.exists():
        raise FileNotFoundError(f"PDF not found: {src}")

    dst = Path(out_path) if out_path else src.with_suffix(".txt")

    if ocr_mode not in ("off", "auto", "force"):
        raise ValueError("ocr_mode must be one of: off, auto, force")

    if ocr_dpi < 100:
        raise ValueError("ocr_dpi must be >= 100")

    if ocr_mode == "force":
        _ensure_tesseract_available()
        text, pages_total, pages_used = _extract_with_ocr(src, max_pages, ocr_lang, ocr_dpi)
        method = "ocr"
    else:
        text, pages_total, pages_used = _extract_with_pypdf(src, max_pages)
        method = "pypdf"

        if not text.strip():
            text, pages_total, pages_used = _extract_with_pymupdf(src, max_pages)
            method = "pymupdf"

        if ocr_mode == "auto" and _looks_like_scanned_doc(text, pages_used):
            _ensure_tesseract_available()
            text, pages_total, pages_used = _extract_with_ocr(src, max_pages, ocr_lang, ocr_dpi)
            method = "ocr(auto)"

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")

    return PdfExtractResult(
        source=str(src),
        output=str(dst),
        pages_total=pages_total,
        pages_used=pages_used,
        chars=len(text),
        method=method,
    )


def _extract_with_pypdf(pdf_path: Path, max_pages: int | None) -> tuple[str, int, int]:
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    used = total if max_pages is None else min(max_pages, total)

    chunks: list[str] = []
    for i in range(used):
        page_text = reader.pages[i].extract_text() or ""
        chunks.append(f"\n\n===== PAGE {i + 1} =====\n{page_text}")

    return "".join(chunks), total, used


def _extract_with_pymupdf(pdf_path: Path, max_pages: int | None) -> tuple[str, int, int]:
    doc = fitz.open(str(pdf_path))
    total = doc.page_count
    used = total if max_pages is None else min(max_pages, total)

    chunks: list[str] = []
    for i in range(used):
        page = doc.load_page(i)
        page_text = page.get_text("text") or ""
        chunks.append(f"\n\n===== PAGE {i + 1} =====\n{page_text}")

    doc.close()
    return "".join(chunks), total, used


def _extract_with_ocr(
    pdf_path: Path,
    max_pages: int | None,
    lang: str,
    dpi: int,
) -> tuple[str, int, int]:
    doc = fitz.open(str(pdf_path))
    total = doc.page_count
    used = total if max_pages is None else min(max_pages, total)

    scale = float(dpi) / 72.0
    matrix = fitz.Matrix(scale, scale)

    chunks: list[str] = []
    for i in range(used):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        page_text = pytesseract.image_to_string(image, lang=lang) or ""
        chunks.append(f"\n\n===== PAGE {i + 1} =====\n{page_text}")

    doc.close()
    return "".join(chunks), total, used


def _ensure_tesseract_available() -> None:
    if shutil.which("tesseract"):
        return
    raise RuntimeError(
        "Tesseract executable not found. Install Tesseract OCR and add it to PATH."
    )


def _looks_like_scanned_doc(text: str, pages_used: int) -> bool:
    if pages_used <= 0:
        return True
    min_chars = pages_used * 80
    return len(text.strip()) < min_chars
