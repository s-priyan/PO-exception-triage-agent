"""Embeddings backed by microsoft/harrier-oss-v1-0.6b.

The model is loaded once into a module-level singleton (prewarm) and reused for
every call. Harrier is instruction-aware: queries carry an ``Instruct: ...\\nQuery:
...`` prompt, documents are embedded as-is. Vectors are L2-normalized so cosine
similarity is a dot product.
"""

from __future__ import annotations

from typing import List

from langchain_core.embeddings import Embeddings

HARRIER_MODEL_ID = "microsoft/harrier-oss-v1-0.6b"

QUERY_INSTRUCTION = (
    "Given a merchandising purchase-order exception, retrieve the SOP passages that "
    "state the governing policy, thresholds, sign-off authorities and actions."
)

_model = None  # SentenceTransformer singleton, populated on first use.


def _load_model():
    """Load and cache the SentenceTransformer model (downloads on first call)."""
    global _model
    if _model is None:
        # Imported lazily so the package stays importable without the heavy stack.
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(HARRIER_MODEL_ID, model_kwargs={"dtype": "auto"}, device="cpu")
    return _model


def prewarm_embeddings() -> None:
    """Load the embedding model once so later retrieval calls reuse it."""
    _load_model()


class HarrierEmbeddings(Embeddings):
    """LangChain embeddings adapter for the Harrier model.

    :param query_instruction: One-sentence task description prepended to queries.
    """

    def __init__(self, query_instruction: str) -> None:
        self._query_instruction = query_instruction

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed corpus passages without an instruction prompt."""
        vectors = _load_model().encode(list(texts), normalize_embeddings=True)
        return vectors.tolist()

    def embed_query(self, text: str) -> List[float]:
        """Embed a query with the instruction-aware prompt Harrier expects."""
        prompt = f"Instruct: {self._query_instruction}\nQuery: {text}"
        vector = _load_model().encode(prompt, normalize_embeddings=True)
        return vector.tolist()
