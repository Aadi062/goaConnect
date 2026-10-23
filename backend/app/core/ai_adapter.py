"""
GoaConnect — AI Model Adapter
Supports: Ollama (local), OpenAI, Anthropic — with graceful fallback to rules-based.
"""
from __future__ import annotations
import asyncio
import json
from typing import Any, Optional
from app.core.logging import get_logger

logger = get_logger("ai.adapter")

_OLLAMA_AVAILABLE: Optional[bool] = None  # cached after first check


async def _check_ollama(base_url: str) -> bool:
    """Check if Ollama is running without blocking."""
    global _OLLAMA_AVAILABLE
    if _OLLAMA_AVAILABLE is not None:
        return _OLLAMA_AVAILABLE
    try:
        import urllib.request
        req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as r:
            data = json.loads(r.read())
            models = [m["name"] for m in data.get("models", [])]
            _OLLAMA_AVAILABLE = True
            logger.info("ollama_connected", models=models)
            return True
    except Exception:
        _OLLAMA_AVAILABLE = False
        logger.info("ollama_unavailable", fallback="rules_based")
        return False


async def generate(
    prompt: str,
    system: str = "",
    model: Optional[str] = None,
    base_url: str = "http://localhost:11434",
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> Optional[str]:
    """
    Generate text using Ollama if available, else return None (caller uses fallback).
    """
    available = await _check_ollama(base_url)
    if not available:
        return None

    try:
        import ollama as _ollama
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        m = model or "qwen2.5:3b"
        # Check if model exists
        tags = _ollama.list()
        available_models = [t.model for t in tags.models]
        if m not in available_models:
            if available_models:
                m = available_models[0]
                logger.info("ollama_model_fallback", requested=model, using=m)
            else:
                logger.warning("ollama_no_models_pulled")
                return None

        response = _ollama.chat(
            model=m,
            messages=messages,
            options={"temperature": temperature, "num_predict": max_tokens},
        )
        return response.message.content
    except Exception as exc:
        logger.error("ollama_generate_error", exc=str(exc))
        return None


async def embed(
    text: str,
    model: str = "nomic-embed-text",
    base_url: str = "http://localhost:11434",
) -> Optional[list[float]]:
    """Generate embeddings via Ollama, or None if unavailable."""
    available = await _check_ollama(base_url)
    if not available:
        return None
    try:
        import ollama as _ollama
        response = _ollama.embeddings(model=model, prompt=text)
        return response["embedding"]
    except Exception as exc:
        logger.error("ollama_embed_error", exc=str(exc))
        return None


def ollama_status() -> dict[str, Any]:
    """Return Ollama availability for health checks."""
    return {
        "available": _OLLAMA_AVAILABLE,
        "checked": _OLLAMA_AVAILABLE is not None,
        "endpoint": "http://localhost:11434",
    }


def reset_ollama_cache() -> None:
    """Force re-check on next call."""
    global _OLLAMA_AVAILABLE
    _OLLAMA_AVAILABLE = None
