import json
import re
import logging
import inspect
from typing import Callable, Iterator

logger = logging.getLogger(__name__)


class ParseFailedError(Exception):
    """Custom exception to indicate that parsing failed for all provided parsers."""

    pass


def parser_pipeline(
    parsers: list[Callable[[str], dict]],
) -> Iterator[Callable[[str], dict]]:
    """Create a parser pipeline that applies multiple parsers in sequence."""
    logger.debug(f"Attempting to parse LLM output with {len(parsers)} parsers.")
    for parser in parsers:
        yield parser


async def parse_with_fallbacks(
    raw: str, parsers: list[Callable[[str], dict]], **kwargs
) -> dict:
    """Attempt to parse LLM output using a list of parsers, falling back to the next parser on failure."""
    logger.debug("Starting parsing with fallbacks.")
    for parser in parser_pipeline(parsers):
        try:
            if inspect.iscoroutinefunction(parser):
                return await parser(raw, **kwargs)
            else:
                return parser(raw, **kwargs)
        except ParseFailedError as exc:
            logger.debug(
                f"Parser {parser.__name__} failed with error: {exc}. Trying next parser."
            )
            continue
    logger.error(f"All {len(parsers)} parsers failed to parse the input: {raw}")
    raise ParseFailedError(f"All {len(parsers)} parsers failed to parse the input.")


def json_parser(raw: str) -> dict:
    """Parses a JSON string into a dictionary. Raises ParseFailedError if parsing fails."""
    try:
        return json.loads(raw)
    except json.decoder.JSONDecodeError as exc:
        logger.error(f"Error during decoding data {raw}. Error: {exc}")
        raise ParseFailedError(f"JSON parsing failed for input: {raw}") from exc


def regex_parser(raw: str) -> dict:
    """"""
    logger.debug(f"Attempting regex parsing for input: {raw}")
    pattern = r'"(\w+)":\s*"?([^",}]+)"?'
    search = re.search(pattern, raw)
    if search:
        key = search.group(1)
        value = search.group(2)
        return {"key": key, "value": value}
    else:
        logger.error(f"Regex parsing failed for input: {raw}")
        raise ParseFailedError(f"Regex parsing failed for input: {raw}")
