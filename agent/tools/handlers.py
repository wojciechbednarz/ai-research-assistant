from config import settings
from rag.retrieval import search
from chromadb.api import Collection
from api import send_post_request
from httpx import AsyncClient


async def search_documents(query: str, chroma_collection: Collection) -> list[dict]:
    """Searches the ChromaDB collection for relevant documents based on the query."""
    return search(chroma_collection, query)


async def summarize_text(text: str, max_tokens: int, client: AsyncClient) -> str:
    """Summarizes the given text using the LLM."""
    messages = [
        {
            "role": "system",
            "content": "You are an assistant that helps summarize text.",
        },
        {
            "role": "user",
            "content": f"Please summarize the following text in no more than {max_tokens} tokens:\n\n{text}",
        },
    ]
    payload = {
        "model": settings.OPEN_ROUTER_DEFAULT_MODEL,
        "messages": messages,
    }
    response = await send_post_request(
        client=client, url=settings.CHAT_COMPLETIONS_URL, payload=payload
    )
    return response["choices"][0]["message"]["content"]


HANDLERS = {
    "search_documents": search_documents,
    "summarize_text": summarize_text,
}


async def dispatch_handler(handler_name: str, **kwargs):
    """Dispatches the handler based on the handler name."""
    if handler_name not in HANDLERS:
        raise ValueError(f"Handler '{handler_name}' not found.")
    handler = HANDLERS[handler_name]
    return await handler(**kwargs)
