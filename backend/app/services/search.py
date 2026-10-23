"""
GoaConnect — Semantic Search Service
Uses pgvector when running on PostgreSQL + Ollama embeddings.
Falls back to SQLite keyword/LIKE search in development automatically.
"""
from __future__ import annotations

import re
from typing import Any, Optional
from app.core.logging import get_logger

logger = get_logger("search")

# Minimum similarity threshold for vector search
_VECTOR_THRESHOLD = 0.6


def _tokenise(text: str) -> list[str]:
    """Lower-case word tokens, stripped of punctuation."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _keyword_score(query_tokens: list[str], doc: str) -> float:
    """Simple TF-style overlap score — used in SQLite fallback."""
    doc_tokens = _tokenise(doc)
    if not doc_tokens:
        return 0.0
    hits = sum(1 for t in query_tokens if t in doc_tokens)
    return hits / max(len(query_tokens), 1)


async def semantic_search_places(
    query: str,
    places: list[dict[str, Any]],
    top_k: int = 5,
    ollama_base_url: str = "http://localhost:11434",
) -> list[dict[str, Any]]:
    """
    Rank `places` by relevance to `query`.

    Strategy:
    1. Try Ollama embeddings → cosine similarity (pgvector-style in Python).
    2. Fall back to keyword overlap scoring.

    `places` items must contain at least a `name` field.
    Returns a list of {place, score, method} dicts sorted by score descending.
    """
    if not places:
        return []

    query_tokens = _tokenise(query)

    # ---- Attempt vector similarity via Ollama --------------------------------
    try:
        from app.core import ai_adapter
        query_vec = await ai_adapter.embed(query, base_url=ollama_base_url)
        if query_vec:
            results = []
            for place in places:
                doc_text = " ".join(
                    str(v) for k, v in place.items()
                    if k in ("name", "description", "category", "district")
                )
                doc_vec = await ai_adapter.embed(doc_text, base_url=ollama_base_url)
                if doc_vec:
                    score = _cosine(query_vec, doc_vec)
                    if score >= _VECTOR_THRESHOLD:
                        results.append({"place": place, "score": round(score, 4), "method": "vector"})

            if results:
                results.sort(key=lambda x: x["score"], reverse=True)
                logger.info("vector_search", query=query[:60], results=len(results))
                return results[:top_k]
    except Exception as exc:
        logger.debug("vector_search_failed", reason=str(exc))

    # ---- Keyword fallback ---------------------------------------------------
    results = []
    for place in places:
        doc_text = " ".join(
            str(v) for k, v in place.items()
            if k in ("name", "description", "category", "district", "tags")
        )
        score = _keyword_score(query_tokens, doc_text)
        if score > 0:
            results.append({"place": place, "score": round(score, 4), "method": "keyword"})

    # If nothing matched, return all places with score 0 (non-filtered browse)
    if not results:
        results = [{"place": p, "score": 0.0, "method": "keyword"} for p in places]

    results.sort(key=lambda x: x["score"], reverse=True)
    logger.info("keyword_search", query=query[:60], results=len(results))
    return results[:top_k]


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def search_status() -> dict[str, Any]:
    """Return search backend status for health checks."""
    try:
        from app.core.ai_adapter import ollama_status
        ollama = ollama_status()
        vector_ready = ollama.get("available", False)
    except Exception:
        vector_ready = False
    return {
        "vector_search": vector_ready,
        "fallback": "keyword",
        "threshold": _VECTOR_THRESHOLD,
    }
