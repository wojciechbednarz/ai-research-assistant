from dotenv import load_dotenv
import logging
from config import get_settings
from api import send_post_request
from httpx import AsyncClient
from agent.tools.definitions import TOOL_LIST
from langfuse import observe
from schemas import RespondResponse
from agent.prompts import (
    ANALYZE_LLM_SYSTEM_PROMPT,
    ANALYZE_LLM_USER_PROMPT,
    RESPOND_LLM_SYSTEM_PROMPT,
    RESPOND_LLM_USER_PROMPT,
)
from helpers import truncate_to_budget
from agent.decorators import llm_retry
from agent.llm_output_parser import (
    parse_with_fallbacks,
    regex_parser,
    json_parser,
)

load_dotenv()

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, client: AsyncClient):
        self.client = client

    @observe
    @llm_retry(max_retries=3)
    async def analyze_llm(
        self,
        prior_messages: list,
        retrieved_docs: list[dict],
        question: str,
        model: str = get_settings().OPENROUTER_LLM_DEFAULT_MODEL,
    ) -> tuple[list, dict]:
        """Send retrieved docs and question to the LLM for analysis.

        Returns (full_messages, message) — callers must use the returned list
        as the message history for subsequent calls, not the original prior_messages.
        """
        if not prior_messages:
            docs = [doc["document"] for doc in retrieved_docs]
            chunks_text = truncate_to_budget(docs, max_tokens=3000)
            messages = [
                {"role": "system", "content": ANALYZE_LLM_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": ANALYZE_LLM_USER_PROMPT.format(
                        chunks_text=chunks_text, question=question
                    ),
                },
            ]
        else:
            messages = prior_messages
        payload = {
            "model": model,
            "messages": messages,
            "tools": TOOL_LIST,
            "tool_choice": "auto",
            "temperature": get_settings().LLM_ANALYZE_TEMPERATURE,
            "max_tokens": get_settings().LLM_MAX_TOKENS,
        }
        response = await send_post_request(
            client=self.client, url=get_settings().CHAT_COMPLETIONS_URL, payload=payload
        )
        logger.debug(
            "analyze_llm raw: finish_reason=%s tool_calls=%s",
            response["choices"][0].get("finish_reason"),
            bool(response["choices"][0]["message"].get("tool_calls")),
        )
        message = response["choices"][0]["message"]
        return (messages + [message], message)

    def make_llm_parser(self):
        """Factory function to create an LLM parser that sends the raw output back to the LLM for parsing."""

        @llm_retry(max_retries=3)
        async def llm_parser(
            raw: str, model: str = get_settings().OPENROUTER_LLM_DEFAULT_MODEL
        ) -> dict:
            """Sends the raw LLM output back to the LLM for parsing, with instructions to respond only with a JSON object."""
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that extracts structured data from text. Respond ONLY with a JSON object.",
                },
                {
                    "role": "user",
                    "content": f"Extract a valid JSON object from this text and return only the JSON: {raw}",
                },
            ]
            payload = {
                "model": model,
                "messages": messages,
                "response_format": {"type": "json_object"},
            }
            response = await send_post_request(
                self.client, get_settings().CHAT_COMPLETIONS_URL, payload
            )
            content = response["choices"][0]["message"]["content"]
            return json_parser(content)

        return llm_parser

    @observe
    @llm_retry(max_retries=3)
    async def respond_llm(
        self,
        user_input: str,
        retrieved_docs: list[dict],
        analysis: str,
        model: str = get_settings().OPENROUTER_LLM_DEFAULT_MODEL,
    ) -> RespondResponse:
        """Sends the user input and retrieved documents to the LLM to generate a response."""
        docs = [doc["document"] for doc in retrieved_docs]
        chunks_text = truncate_to_budget(docs, max_tokens=3000)
        messages = [
            {"role": "system", "content": RESPOND_LLM_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": RESPOND_LLM_USER_PROMPT.format(
                    user_input=user_input, chunks_text=chunks_text, analysis=analysis
                ),
            },
        ]
        payload = {
            "model": model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": get_settings().LLM_RESPOND_TEMPERATURE,
            "max_tokens": get_settings().LLM_MAX_TOKENS,
        }
        response = await send_post_request(
            client=self.client, url=get_settings().CHAT_COMPLETIONS_URL, payload=payload
        )
        content = response["choices"][0]["message"]["content"]
        logger.debug("respond_llm raw content length: %d", len(content))
        return RespondResponse(
            **await parse_with_fallbacks(
                content, [json_parser, regex_parser, self.make_llm_parser()]
            )
        )
