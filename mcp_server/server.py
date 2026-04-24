from typing import Any, Callable
from .protocol import make_result, make_error, ERROR_METHOD_NOT_FOUND
from .transport import run_server
from rag.retrieval import hybrid_search
from rag.ingestion import ChromaDB
from functools import lru_cache
import json

ToolEntry = dict[str, Any]

search_documents = {
    "schema": {
        "name": "search_documents",
        "title": "Search Documents",
        "description": "Search for documents based on a query",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
    },
    "handler": None,  # type: ignore[assignment]
}


get_metadata = {
    "schema": {
        "name": "get_metadata",
        "title": "Get Metadata",
        "description": "Retrieve metadata information",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to retrieve metadata from",
                }
            },
            "required": ["text"],
        },
    },
    "handler": None,  # type: ignore[assignment]
}


TOOLS: dict[str, dict[str, Any]] = {
    "search_documents": search_documents,
    "get_metadata": get_metadata,
}


def dispatch(request) -> dict:
    method = request.get("method")
    id = request.get("id")

    if method == "initialize":
        return make_result(
            id,
            {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "ai-research-assistant", "version": "1.0.0"},
                "capabilities": {
                    "tools": {},
                },
            },
        )

    elif method == "notifications/initialized":
        return {}

    elif method == "tools/list":
        return make_result(id, {"tools": [t["schema"] for t in TOOLS.values()]})

    elif method == "tools/call":
        name = request["params"]["name"]
        args = request["params"].get("arguments", {})
        if name not in TOOLS:
            return make_error(id, ERROR_METHOD_NOT_FOUND, "Method not found")
        result = TOOLS[name]["handler"](args)
        return make_result(id, {"content": [{"type": "text", "text": result}]})

    else:
        return make_error(id, ERROR_METHOD_NOT_FOUND, "Method not found")


def main() -> None:
    @lru_cache(maxsize=1)
    def get_collection():
        return ChromaDB(collection_name="ai-research-assistant").collection

    TOOLS["search_documents"]["handler"] = lambda args: json.dumps(
        [
            {"id": r["id"], "document": r["document"][:300]}
            for r in hybrid_search(get_collection(), args["query"])
        ],
        ensure_ascii=False,
    )
    TOOLS["get_metadata"]["handler"] = lambda args: json.dumps(
        {"collection": "ai-research-assistant", "count": get_collection().count()},
        ensure_ascii=False,
    )
    run_server(dispatch)


if __name__ == "__main__":
    main()
