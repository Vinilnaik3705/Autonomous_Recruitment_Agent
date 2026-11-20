"""Unit tests that do not require a model download or external services."""

import pytest

from backend.services.resume_ingestion import extract_resume_text


def test_empty_file_rejected():
    with pytest.raises(ValueError, match="empty"):
        extract_resume_text(b"", "resume.pdf")


def test_unsupported_file_rejected():
    with pytest.raises(ValueError, match="Only PDF and DOCX"):
        extract_resume_text(b"data", "resume.txt")


def test_docx_text_extraction():
    from io import BytesIO
    from docx import Document

    document = Document()
    document.add_paragraph("Ada Lovelace")
    document.add_paragraph("Python and SQL")
    buffer = BytesIO()
    document.save(buffer)
    assert extract_resume_text(buffer.getvalue(), "resume.DOCX") == "Ada Lovelace\nPython and SQL"
