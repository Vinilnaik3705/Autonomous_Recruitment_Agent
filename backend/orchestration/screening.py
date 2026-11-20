"""Phase 2 screening graph. No automatic rejection or external side effects.

This graph processes a single resume and returns validated extraction and
a vector. Database writes and notifications belong to the Celery task.
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from backend.embeddings.provider import LocalMiniLM
from backend.services.resume_extraction import extract_resume_fields
from backend.services.resume_ingestion import extract_resume_text


class ScreeningState(TypedDict, total=False):
    filename: str
    file_bytes: bytes
    text: str
    fields: dict
    embedding: list[float]


def build_screening_graph(*, extractor=extract_resume_fields, embedder=None):
    encoder = embedder or LocalMiniLM()

    def parse(state: ScreeningState) -> dict:
        return {"text": extract_resume_text(state["file_bytes"], state["filename"])}

    def extract(state: ScreeningState) -> dict:
        return {"fields": extractor(state["text"]).model_dump(mode="json")}

    def embed(state: ScreeningState) -> dict:
        return {"embedding": encoder.encode(state["text"])}

    graph = StateGraph(ScreeningState)
    graph.add_node("parse", parse)
    graph.add_node("extract", extract)
    graph.add_node("embed", embed)
    graph.add_edge(START, "parse")
    graph.add_edge("parse", "extract")
    graph.add_edge("extract", "embed")
    graph.add_edge("embed", END)
    return graph.compile()
