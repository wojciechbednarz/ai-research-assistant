from config import get_settings
from api import send_post_request
from httpx import AsyncClient
from agent.decorators import llm_retry


@llm_retry(max_retries=3)
async def summarize_text(
    text: str,
    max_tokens: int,
    client: AsyncClient,
    model: str = get_settings().OPENROUTER_LLM_DEFAULT_MODEL,
) -> str:
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
        "model": model,
        "messages": messages,
    }
    response = await send_post_request(
        client=client, url=get_settings().CHAT_COMPLETIONS_URL, payload=payload
    )
    return response["choices"][0]["message"]["content"]
