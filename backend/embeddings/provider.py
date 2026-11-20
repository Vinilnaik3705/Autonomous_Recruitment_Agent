"""Lazy, replaceable embedding interface for 384-dimensional MiniLM vectors."""

from functools import lru_cache
from typing import Protocol

DIMENSIONS = 384
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingProvider(Protocol):
    def encode(self, text: str) -> list[float]: ...


class LocalMiniLM:
    def encode(self, text: str) -> list[float]:
        values = self._model().encode(text).tolist()
        if len(values) != DIMENSIONS:
            raise ValueError(f"Expected {DIMENSIONS} embedding values, got {len(values)}")
        return [float(value) for value in values]

    @staticmethod
    @lru_cache(maxsize=1)
    def _model():
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(MODEL_NAME)
