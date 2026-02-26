"""Semantic matching module: find the most relevant passage using embeddings."""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


_MODEL_NAME = "all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Lazy-load the sentence transformer model on first use."""
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def find_best_passage(citing_paragraph: str, paper_text: str | None) -> str | None:
    """Find the passage in paper_text most similar to the citing paragraph.

    Args:
        citing_paragraph: The paragraph containing the citation.
        paper_text: Full text of the retrieved paper, or None.

    Returns:
        The most semantically similar text chunk, or None if no text available.
    """
    if not paper_text or not paper_text.strip():
        return None

    chunks = _chunk_text(paper_text)
    if not chunks:
        return None

    try:
        model = _get_model()
        query_embedding = model.encode([citing_paragraph])
        chunk_embeddings = model.encode(chunks)

        similarities = cosine_similarity(
            np.array(query_embedding).reshape(1, -1),
            np.array(chunk_embeddings),
        )[0]

        best_idx = int(np.argmax(similarities))
        return chunks[best_idx]
    except Exception:
        return None


def _chunk_text(
    text: str, chunk_size: int = 700, overlap: int = 150
) -> list[str]:
    """Split text into overlapping chunks.

    Args:
        text: Full paper text.
        chunk_size: Target chunk size in characters.
        overlap: Overlap between consecutive chunks in characters.

    Returns:
        List of text chunks. Single-element list if text is shorter
        than chunk_size.
    """
    text = text.strip()
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks
