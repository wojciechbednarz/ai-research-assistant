from chromadb.api import Collection
from chromadb import QueryResult
from display import print_header, print_info
import json


def search(collection: Collection, question: str, n_results: int = 3) -> QueryResult:
    """Queries the ChromaDB collection and prints results."""
    print_header(f"Searching for: {question}")
    query_result = collection.query(query_texts=[question], n_results=n_results)
    return [
        {"id": id_, "document": doc, "distance": dist}
        for id_, doc, dist in zip(
            query_result["ids"][0],
            query_result["documents"][0],
            query_result["distances"][0],
        )
    ]
