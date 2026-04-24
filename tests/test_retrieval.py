from unittest.mock import MagicMock
from rag.retrieval import hybrid_search, _tokenize


def _make_collection(
    docs: list[str], ids: list[str] = None, distances: list[float] = None
):
    if ids is None:
        ids = [f"doc{i}" for i in range(len(docs))]
    if distances is None:
        distances = [0.1 * (i + 1) for i in range(len(docs))]
    collection = MagicMock()
    collection.query.return_value = {
        "ids": [ids],
        "documents": [docs],
        "distances": [distances],
    }
    return collection


def test_hybrid_search_returns_list():
    collection = _make_collection(["doc about AI", "doc about ML"])
    results = hybrid_search(collection, "what is AI?", n_results=2)
    assert isinstance(results, list)
    assert len(results) == 2


def test_hybrid_search_result_has_document_key():
    collection = _make_collection(["doc about AI", "doc about ML"])
    results = hybrid_search(collection, "what is AI?", n_results=2)
    for r in results:
        assert "document" in r


def test_hybrid_search_empty_results():
    collection = _make_collection([])
    results = hybrid_search(collection, "anything", n_results=3)
    assert results == []


def test_tokenize_strips_punctuation():
    # "4" is a single char and gets dropped by the noise filter — that's expected
    assert _tokenize("AI_devs 4: Builders!") == ["ai", "devs", "builders"]


def test_tokenize_handles_concatenated():
    # "AIDEVS4" stays as one token — semantic search bridges the gap
    assert _tokenize("AIDEVS4?") == ["aidevs4"]


def test_tokenize_drops_single_chars():
    assert "a" not in _tokenize("a b hello")
