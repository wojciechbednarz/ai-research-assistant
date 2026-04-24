import logging
import re
from chromadb import Collection
from rank_bm25 import BM25Okapi
from rag.ingestion import ChromaDB
from config import get_settings

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    """Split on any non-alphanumeric boundary, lowercase, drop single chars."""
    return [t for t in re.sub(r"[^\w]|_", " ", text.lower()).split() if len(t) > 1]


def search(collection: Collection, question: str, n_results: int = 3) -> list[dict]:
    logger.debug("Searching for: %s", question)
    query_result = collection.query(query_texts=[question], n_results=n_results)
    ids = query_result["ids"] or []
    documents = query_result["documents"] or []
    distances = query_result["distances"] or []
    if not ids:
        return []
    return [
        {"id": id_, "document": doc, "distance": dist}
        for id_, doc, dist in zip(ids[0], documents[0], distances[0])
    ]


def hybrid_search(
    collection: Collection,
    question: str,
    n_results: int = 3,
    alpha: float | None = None,
) -> list[dict]:
    """Hybrid BM25 + vector similarity search, re-ranked by combined score."""
    if alpha is None:
        alpha = get_settings().HYBRID_SEARCH_ALPHA
    vector_results = search(collection, question, n_results * 2)
    if not vector_results:
        return []
    corpus = [_tokenize(r["document"]) for r in vector_results]
    bm25 = BM25Okapi(corpus)
    bm25_scores = bm25.get_scores(_tokenize(question))

    for i, result in enumerate(vector_results):
        vector_score = 1 - result["distance"]
        bm25_score = bm25_scores[i] / (max(bm25_scores) + 1e-9)
        result["hybrid_score"] = alpha * vector_score + (1 - alpha) * bm25_score
    return sorted(vector_results, key=lambda r: r["hybrid_score"], reverse=True)[
        :n_results
    ]


if __name__ == "__main__":
    chromad_db = ChromaDB(collection_name="ai-research-assistant")
    hybrid_search(chromad_db.collection, "Co to jest AIDevs4?", n_results=3)
