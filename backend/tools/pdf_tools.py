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
    return ""
