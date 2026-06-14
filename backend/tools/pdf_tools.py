from __future__ import annotations

import io

import pdfplumber
from pypdf import PdfReader


def extract_text(pdf_bytes: bytes) -> str:
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        text = ""
    if len(text.strip()) >= 500:
        return text
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return text


def ocr_fallback(pdf_bytes: bytes) -> str:
    """Run OCR for scanned PDFs when optional system dependencies are available.

    The project can run without OCR dependencies in lightweight demo environments; when
    `pdf2image`/`pytesseract` or the required native binaries are unavailable, this
    returns an empty string and the caller records a partial extraction.
    """
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
    except Exception:
        return ""

    try:
        pages = convert_from_bytes(pdf_bytes, dpi=220, fmt="png")
        return "\n".join(pytesseract.image_to_string(page) for page in pages)
    except Exception:
        return ""
