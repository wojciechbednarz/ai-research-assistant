from config import settings
import httpx
from display import print_header, print_results


async def send_post_request(
    client: httpx.AsyncClient, url: str, payload: dict
) -> httpx.Response:
    """Helper function to send POST requests."""
    print_header(f"Sending POST request to {url} with payload: {payload}")
    try:
        response = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {settings.OPEN_ROUTER_API_KEY}"},
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        print_header(f"HTTP error occurred: {e}")
        raise
