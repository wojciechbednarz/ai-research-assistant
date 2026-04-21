from .protocol import make_result, make_error, ERROR_METHOD_NOT_FOUND
from .transport import run_server
from rag.retrieval import search
from rag.ingestion import ChromaDB
import json

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
    "handler": None,
}

summarize_text = {
    "schema": {
        "name": "summarize_text",
        "title": "Summarize Text",
        "description": "Summarize the given text",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to summarize"}
            },
            "required": ["text"],
        },
    },
    "handler": None,
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
    "handler": None,
}


TOOLS = {
    "search_documents": search_documents,
    "summarize_text": summarize_text,
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
        return None

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
    db = ChromaDB(collection_name="ai-research-assistant")
    collection = db.collection

    TOOLS["search_documents"]["handler"] = lambda args: json.dumps(
      [{"id": r["id"], "document": r["document"][:300]} for r in search(collection, args["query"])],
      ensure_ascii=False)
    TOOLS["summarize_text"]["handler"] = lambda args: f"Summary of {args['text'][:100]}"
    TOOLS["get_metadata"]["handler"] = lambda args: json.dumps(                                                                                                                                                                             
      {"collection": "ai-research-assistant", "count": collection.count()},
      ensure_ascii=False)
    run_server(dispatch)


if __name__ == "__main__":
    main()
