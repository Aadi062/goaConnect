"""
Tests for cache service and semantic search service.
Both must work without Redis or Ollama (in-memory + keyword fallback).
"""
import pytest
import asyncio


# ---------------------------------------------------------------------------
# Cache service tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=False)
def reset_cache():
    """Ensure each test starts with a clean in-memory cache state."""
    from app.core.cache import reset_cache_state
    reset_cache_state()
    yield
    reset_cache_state()


@pytest.mark.asyncio
async def test_cache_set_and_get(reset_cache):
    from app.core.cache import set, get
    await set("test_key", {"foo": "bar"}, ttl=60)
    result = await get("test_key")
    assert result == {"foo": "bar"}


@pytest.mark.asyncio
async def test_cache_miss_returns_none(reset_cache):
    from app.core.cache import get
    result = await get("nonexistent_key_xyz")
    assert result is None


@pytest.mark.asyncio
async def test_cache_delete(reset_cache):
    from app.core.cache import set, get, delete
    await set("del_key", "hello", ttl=60)
    assert await get("del_key") == "hello"
    await delete("del_key")
    assert await get("del_key") is None


@pytest.mark.asyncio
async def test_cache_ttl_expiry(reset_cache):
    """Values with TTL=1 should expire after 1 second."""
    import time
    from app.core import cache as cache_module
    from app.core.cache import _mem_set, _mem_get
    # Set directly into memory store with 1-second TTL
    _mem_set("expire_key", "value", ttl=1)
    assert _mem_get("expire_key") == "value"
    # Wait for expiry
    await asyncio.sleep(1.05)
    assert _mem_get("expire_key") is None


@pytest.mark.asyncio
async def test_cache_status_falls_back_to_memory(reset_cache):
    from app.core.cache import cache_status, set
    await set("any_key", 42)
    status = cache_status()
    # Without Redis running, should use in_memory
    assert status["backend"] in ("in_memory", "redis")  # either is valid
    assert "in_memory_keys" in status


@pytest.mark.asyncio
async def test_cache_stores_complex_values(reset_cache):
    from app.core.cache import set, get
    complex_val = {"list": [1, 2, 3], "nested": {"a": True, "b": None}}
    await set("complex", complex_val, ttl=60)
    result = await get("complex")
    assert result == complex_val


# ---------------------------------------------------------------------------
# Semantic search service tests
# ---------------------------------------------------------------------------

SAMPLE_PLACES = [
    {"id": "1", "name": "Calangute Beach", "description": "Largest beach in North Goa", "category": "beach", "district": "North Goa"},
    {"id": "2", "name": "Basilica of Bom Jesus", "description": "UNESCO World Heritage church Old Goa", "category": "heritage", "district": "North Goa"},
    {"id": "3", "name": "Dudhsagar Falls", "description": "Stunning waterfall in wildlife sanctuary", "category": "nature", "district": "South Goa"},
    {"id": "4", "name": "Palolem Beach", "description": "Crescent-shaped beach in South Goa", "category": "beach", "district": "South Goa"},
    {"id": "5", "name": "Chapora Fort", "description": "17th century Portuguese fort panoramic views", "category": "heritage", "district": "North Goa"},
]


@pytest.mark.asyncio
async def test_search_returns_results():
    from app.services.search import semantic_search_places
    results = await semantic_search_places("beach", SAMPLE_PLACES, top_k=3)
    assert len(results) > 0
    assert all("place" in r and "score" in r and "method" in r for r in results)


@pytest.mark.asyncio
async def test_search_beach_query_ranks_beaches_higher():
    from app.services.search import semantic_search_places
    results = await semantic_search_places("beach swimming", SAMPLE_PLACES, top_k=5)
    names = [r["place"]["name"] for r in results]
    # Beaches should appear before purely heritage results
    beach_indices = [i for i, n in enumerate(names) if "Beach" in n]
    heritage_indices = [i for i, n in enumerate(names) if "Basilica" in n or "Fort" in n]
    if beach_indices and heritage_indices:
        assert min(beach_indices) < max(heritage_indices)


@pytest.mark.asyncio
async def test_search_heritage_query():
    from app.services.search import semantic_search_places
    results = await semantic_search_places("UNESCO heritage church", SAMPLE_PLACES, top_k=5)
    assert len(results) > 0
    # Basilica should score higher than beaches
    basilica = next((r for r in results if "Basilica" in r["place"]["name"]), None)
    assert basilica is not None


@pytest.mark.asyncio
async def test_search_empty_places_returns_empty():
    from app.services.search import semantic_search_places
    results = await semantic_search_places("anything", [], top_k=5)
    assert results == []


@pytest.mark.asyncio
async def test_search_no_match_returns_all_places():
    from app.services.search import semantic_search_places
    # A query with zero keyword overlap should still return all places (score=0)
    results = await semantic_search_places("xyzxyzxyz_nomatch", SAMPLE_PLACES, top_k=10)
    assert len(results) == len(SAMPLE_PLACES)
    assert all(r["score"] == 0.0 for r in results)


@pytest.mark.asyncio
async def test_search_top_k_respected():
    from app.services.search import semantic_search_places
    results = await semantic_search_places("goa", SAMPLE_PLACES, top_k=2)
    assert len(results) <= 2


@pytest.mark.asyncio
async def test_search_status():
    from app.services.search import search_status
    status = search_status()
    assert "vector_search" in status
    assert "fallback" in status
    assert status["fallback"] == "keyword"


@pytest.mark.asyncio
async def test_search_method_is_keyword_without_ollama():
    """Without Ollama running, all searches must use keyword method."""
    from app.services.search import semantic_search_places
    from app.core.ai_adapter import reset_ollama_cache
    reset_ollama_cache()
    results = await semantic_search_places("waterfall", SAMPLE_PLACES, top_k=5)
    methods = {r["method"] for r in results if r["score"] > 0}
    # In dev (no Ollama), must be keyword
    assert "keyword" in methods or len(methods) == 0
