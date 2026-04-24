from config import get_settings
import httpx
import logging
from langfuse import observe, get_client

langfuse = get_client()

logger = logging.getLogger(__name__)


@observe(as_type="generation")
async def send_post_request(client: httpx.AsyncClient, url: str, payload: dict) -> dict:
    """Helper function to send POST requests."""
    logger.debug("Sending POST request to %s model=%s", url, payload.get("model"))
    try:
        response = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {get_settings().OPEN_ROUTER_API_KEY}"},
        )
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage", {})
        langfuse.update_current_generation(
            model=payload.get("model"),
            usage_details={
                "input": usage.get("prompt_tokens"),
                "output": usage.get("completion_tokens"),
                "total": usage.get("total_tokens"),
            },
        )
        return data
    except httpx.HTTPError:
        logger.exception("HTTP error occurred calling %s", url)
        raise
