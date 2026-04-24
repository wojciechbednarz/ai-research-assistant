"""
End-to-end smoke tests for the AI Research Assistant.

Tests the full pipeline: document ingestion → ChromaDB vector store → LLM-powered query.

Prerequisite: Docker running. pytest tests/test_smoke.py -v
"""

import pytest

pytestmark = pytest.mark.integration

TIMEOUT = 120  # LLM calls via OpenRouter can be slow


def test_ingest_returns_success_message(client) -> None:
    """POST /ingest completes successfully and returns a confirmation message."""
    resp = client.post("/ingest")
    assert resp.status_code == 200
    assert resp.json().get("message") == "Ingestion complete"


def test_collection_contains_documents_after_ingest(client) -> None:
    """ChromaDB collection is non-empty after ingestion."""
    resp = client.post("/get_collection_count")
    assert resp.status_code == 200
    count = resp.json()
    assert isinstance(count, int), f"Expected int count, got {type(count)}"
    assert count > 0, (
        f"Expected at least one chunk in ChromaDB after ingestion, got {count}"
    )


def test_research_response_has_valid_schema(client) -> None:
    """GET /research returns a response with answer, sources, and confidence fields."""
    resp = client.get("/research", params={"query": "What is function calling?"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("answer"), str) and data["answer"], (
        "answer must be a non-empty string"
    )
    assert isinstance(data.get("sources"), list), "sources must be a list"
    assert data.get("confidence") in {"high", "medium", "low"}, (
        f"confidence must be high/medium/low, got: {data.get('confidence')!r}"
    )


def test_research_answer_contains_relevant_terms(client) -> None:
    """Answer for a topic covered in raw docs references expected domain concepts."""
    resp = client.get(
        "/research", params={"query": "Co to jest function calling w LLM?"}
    )
    assert resp.status_code == 200
    answer_lower = resp.json()["answer"].lower()
    domain_terms = {"function", "tool", "narzędzi", "llm", "model", "calling", "agent"}
    assert any(term in answer_lower for term in domain_terms), (
        f"Answer references none of the expected terms {domain_terms}.\n"
        f"Answer (first 300 chars): {answer_lower[:300]}"
    )


def test_research_caching_returns_identical_response(client, app) -> None:
    """Cache is populated after the first call and the second call hits it."""
    query = "What are AI agents?"
    r1 = client.get("/research", params={"query": query})
    assert r1.status_code == 200
    # The cache entry must exist after the first call
    assert app.state.response_cache.get(query) is not None, (
        "Cache was not populated after the first /research call."
    )
    r2 = client.get("/research", params={"query": query})
    assert r2.status_code == 200
    assert r1.json() == r2.json(), (
        "Second (cached) response differs from the first — cache appears broken."
    )
