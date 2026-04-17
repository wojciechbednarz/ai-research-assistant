from config import settings
from api import send_post_request
from httpx import AsyncClient


class Agent:
    def __init__(self, client: AsyncClient):
        self.client = client

    async def analyze_llm(self, user_input: str, retrieved_docs: list[dict]) -> str:
        """Sends the user input and retrieved documents to the LLM for analysis."""
        chunks_text = "\n\n---\n\n".join(doc["document"] for doc in retrieved_docs)
        messages = [
            {
                "role": "system",
                "content": "You are an assistant that helps analyze documents.",
            },
            {
                "role": "user",
                "content": f"User question: {user_input}\n\nRelevant context:\n{chunks_text}\n\nAnalyze the context and extract key insights relevant to the question.",
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
