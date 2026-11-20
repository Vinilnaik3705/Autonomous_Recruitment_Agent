"""Offline graph test with fake extraction and embeddings."""

from io import BytesIO

from docx import Document

from backend.orchestration.screening import build_screening_graph
from backend.schemas.resume import ResumeFields


class FakeEncoder:
    def encode(self, text):
        assert "Python" in text
        return [0.1] * 384


def test_graph_extracts_and_embeds():
    doc = Document()
    doc.add_paragraph("Ada Lovelace")
    doc.add_paragraph("Python")
    buffer = BytesIO()
    doc.save(buffer)

    graph = build_screening_graph(
        extractor=lambda text: ResumeFields(name="Ada Lovelace", skills=["Python"]),
        embedder=FakeEncoder(),
    )
    result = graph.invoke({"filename": "resume.docx", "file_bytes": buffer.getvalue()})
    assert result["fields"]["name"] == "Ada Lovelace"
    assert len(result["embedding"]) == 384
