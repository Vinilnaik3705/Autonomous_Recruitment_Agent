"""Small, testable text-extraction boundary for the new screening pipeline.

No database writes or LLM calls occur here. OCR is an explicit fallback.
"""

from io import BytesIO


def extract_resume_text(data: bytes, filename: str, *, ocr_fallback: bool = False) -> str:
    if not data:
        raise ValueError("Resume file is empty")
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension == "pdf":
        import pdfplumber
        with pdfplumber.open(BytesIO(data)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages).strip()
        if text:
            return text
        if not ocr_fallback:
            raise ValueError("Scanned PDF has no selectable text; enable OCR fallback")
        return _ocr_pdf(data)
    if extension == "docx":
        from docx import Document
        document = Document(BytesIO(data))
        text = "\n".join(p.text for p in document.paragraphs if p.text.strip())
        if not text.strip():
            raise ValueError("DOCX contains no extractable paragraph text")
        return text
    raise ValueError("Only PDF and DOCX resumes are supported")


def _ocr_pdf(data: bytes) -> str:
    # OCR needs a PDF-to-image renderer. This implementation deliberately
    # fails explicitly until the approved OCR runtime is installed.
    raise RuntimeError("OCR fallback is not configured; scanned PDFs cannot be processed yet")
