from config import settings
from api import send_post_request
from httpx import AsyncClient
from agent.tools.definitions import TOOL_LIST


class Agent:
    def __init__(self, client: AsyncClient):
        self.client = client

    async def analyze_llm(self, messages: list, retrieved_docs: list[dict], question: str) -> dict:
        """Sends the user input and retrieved documents to the LLM for analysis."""
        if not messages:  # first call — build initial messages
            chunks_text = "\n\n---\n\n".join(doc["document"] for doc in retrieved_docs)
            messages = [
                {
                    "role": "system",
                    "content": "You are a research assistant. You MUST call search_documents if the provided context does not contain a clear answer to the question. Do not guess or say you don't know — search first. If context is too long, call summarize_text.",
                },
                {
                    "role": "user",
                    "content": f"Analyze these documents and answer if confident, or call a tool if you need more:\n\n{chunks_text}\n\nUser question: {question}",
                },
            ]
        payload = {
            "model": settings.OPEN_ROUTER_DEFAULT_MODEL,
            "messages": messages,
            "tools": TOOL_LIST,
            "tool_choice": "auto",
        }
        response = await send_post_request(
            client=self.client, url=settings.CHAT_COMPLETIONS_URL, payload=payload
        )
        message =  response["choices"][0]["message"]
        return (messages + [message], message)

    async def respond_llm(
        self, user_input: str, retrieved_docs: list[dict], analysis: str
    ) -> str:
        """Sends the user input and retrieved documents to the LLM to generate a response."""
        chunks_text = "\n\n---\n\n".join(doc["document"] for doc in retrieved_docs)
        messages = [
            {
                "role": "system",
                "content": "You are an assistant that helps answer questions based on provided documents.",
            },
            {
                "role": "user",
                "content": f"User question: {user_input}\n\nRelevant context:\n{chunks_text}\n\n Analysis: {analysis}\n\nBased on the context and analysis, provide a concise and accurate answer to the user's question.",
            },
        ]
        payload = {
            "model": settings.OPEN_ROUTER_DEFAULT_MODEL,
            "messages": messages,
        }
        response = await send_post_request(
            client=self.client, url=settings.CHAT_COMPLETIONS_URL, payload=payload
        )
        return response["choices"][0]["message"]["content"]
