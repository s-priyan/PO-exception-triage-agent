"""RAG retrieval over the merch SOP corpus for Agent 2.

Markdown docs are split by header (to keep section numbers for citations) and then
recursively chunked. Chunks are embedded with Harrier and indexed in a persistent
ChromaDB collection. ``search_sops`` is the retrieval tool Agent 2 calls.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_core.tools import tool

from .embeddings import HarrierEmbeddings, QUERY_INSTRUCTION, prewarm_embeddings

FILES_DIR = Path(__file__).resolve().parents[1] / "files"
CHROMA_DIR = Path(__file__).resolve().parents[1] / ".chroma"
COLLECTION_NAME = "merch_sops"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
TOP_K = 5

_HEADERS_TO_SPLIT_ON = [("#", "h1"), ("##", "h2"), ("###", "h3")]
_SECTION_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)")

_vector_store = None  # Chroma singleton, populated on first use.


def _section_from_metadata(metadata: dict) -> str:
    """Derive the SOP section number (e.g. "4" or "2.1") from header metadata."""
    for key in ("h3", "h2"):
        header = metadata.get(key)
        if header:
            match = _SECTION_RE.match(header)
            if match:
                return match.group(1)
    return ""  # Front matter or the document title carry no section number.


def load_and_chunk() -> List[Document]:
    """Load every SOP markdown file and split it into citation-tagged chunks."""
    # Imported lazily so the package stays importable without the heavy stack.
    from langchain_text_splitters import (
        MarkdownHeaderTextSplitter,
        RecursiveCharacterTextSplitter,
    )

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=_HEADERS_TO_SPLIT_ON, strip_headers=False
    )
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )

    chunks: List[Document] = []
    for path in sorted(FILES_DIR.glob("*.md")):
        sections = header_splitter.split_text(path.read_text(encoding="utf-8"))
        for section in sections:
            section.metadata["source"] = path.name
            section.metadata["section"] = _section_from_metadata(section.metadata)
        chunks.extend(char_splitter.split_documents(sections))
    return chunks


def get_vector_store():
    """Return the Chroma store, building and persisting the index on first use."""
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    # Imported lazily so the package stays importable without the heavy stack.
    from langchain_chroma import Chroma

    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=HarrierEmbeddings(query_instruction=QUERY_INSTRUCTION),
        persist_directory=str(CHROMA_DIR),
        collection_metadata={"hnsw:space": "cosine"},
    )
    if not store.get(limit=1)["ids"]:
        store.add_documents(load_and_chunk())
    _vector_store = store
    return _vector_store


def prewarm() -> None:
    """Load the embedding model and build/load the SOP index ahead of time."""
    prewarm_embeddings()
    get_vector_store()


@tool
def search_sops(query: str) -> List[dict]:
    """Retrieve merch SOP passages relevant to the query.

    Pass a synthesised query that carries the semantic context needed for
    retrieval. Returns a list of passages, each with a citation ("document.md
    \u00a7n"), source, section, relevance score and text. Ground every claim in
    these passages and cite them; do not assert policy that is not present here.
    """
    results = get_vector_store().similarity_search_with_relevance_scores(query, k=TOP_K)
    passages: List[dict] = []
    for document, score in results:
        source = document.metadata.get("source", "unknown")
        section = document.metadata.get("section", "")
        citation = f"{source} \u00a7{section}" if section else source
        passages.append(
            {
                "citation": citation,
                "source": source,
                "section": section,
                "score": round(float(score), 4),
                "text": document.page_content,
            }
        )
    return passages
