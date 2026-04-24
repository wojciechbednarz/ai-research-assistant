from config import get_settings
import asyncio
from functools import wraps
from typing import Callable
import logging

logger = logging.getLogger(__name__)


def llm_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    fallback_model: str = get_settings().OPENROUTER_LLM_FALLBACK_MODEL,
) -> Callable:
    """A decorator to retry LLM calls with exponential backoff and fallback model support."""

    def func_decorator(func: Callable) -> Callable:
        """Inner decorator function."""

        @wraps(func)
        async def wrapper(*args, **kwargs) -> dict | str:
            """Wrapper function to handle retries and fallback model."""
            delay = initial_delay
            for retry in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    logger.exception("LLM call failed")
                    if retry < max_retries:
                        logger.info(f"Retrying in {delay} seconds.")
                        await asyncio.sleep(delay)
                        delay *= 2
                    else:
                        logger.warning(
                            "Exceeded maximum number of retries, trying fallback model..."
                        )
                        try:
                            return await func(
                                *args, **{**kwargs, "model": fallback_model}
                            )
                        except Exception:
                            logger.exception(f"Fallback model {fallback_model} failed.")
                            raise

        return wrapper

    return func_decorator
