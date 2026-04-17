search_documents = {
    "type": "function",
    "function": {
        "name": "search_documents",
        "description": "Retrieve relevant document chunks from the knowledge base",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}


summarize_text = {
    "type": "function",
    "function": {
        "name": "summarize_text",
        "description": "Summarize the given text",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
}

TOOL_LIST = [search_documents, summarize_text]
