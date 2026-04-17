from __future__ import annotations

import argparse

from .pdf_tools import extract_pdf_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract text from PDF files")
    parser.add_argument("pdf", help="PDF file path")
    parser.add_argument("--out", default=None, help="Output text file path")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit page count")
    parser.add_argument(
        "--ocr-mode",
        choices=["off", "auto", "force"],
        default="auto",
        help="OCR mode: off=disable OCR, auto=OCR when text is too sparse, force=always OCR",
    )
    parser.add_argument(
        "--ocr-lang",
        default="eng",
        help="Tesseract language set, e.g. eng or chi_tra+eng",
    )
    parser.add_argument(
        "--ocr-dpi",
        type=int,
        default=300,
        help="Render DPI for OCR image generation (higher = slower but usually better)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    result = extract_pdf_text(
        pdf_path=args.pdf,
        out_path=args.out,
        max_pages=args.max_pages,
        ocr_mode=args.ocr_mode,
        ocr_lang=args.ocr_lang,
        ocr_dpi=args.ocr_dpi,
    )

    print(f"PDF: {result.source}")
    print(f"OUT: {result.output}")
    print(f"METHOD: {result.method}")
    print(f"PAGES: {result.pages_used}/{result.pages_total}")
    print(f"CHARS: {result.chars}")


if __name__ == "__main__":
    main()
