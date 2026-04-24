import pytest
from agent.llm_output_parser import (
    json_parser,
    regex_parser,
    parse_with_fallbacks,
    ParseFailedError,
)


def test_json_parser_valid():
    result = json_parser('{"answer": "yes", "confidence": "high"}')
    assert result == {"answer": "yes", "confidence": "high"}


def test_json_parser_invalid():
    with pytest.raises(ParseFailedError):
        json_parser("not valid json {{{")


def test_regex_parser_match():
    result = regex_parser('"confidence": "high"')
    assert result["value"] == "high"


def test_regex_parser_no_match():
    with pytest.raises(ParseFailedError):
        regex_parser("no key value pairs here at all")


async def test_parse_with_fallbacks_first_succeeds():
    result = await parse_with_fallbacks('{"key": "val"}', [json_parser])
    assert result == {"key": "val"}


async def test_parse_with_fallbacks_falls_to_second():
    result = await parse_with_fallbacks(
        '"confidence": "low"', [json_parser, regex_parser]
    )
    assert result["value"] == "low"


async def test_parse_with_fallbacks_all_fail():
    with pytest.raises(ParseFailedError):
        await parse_with_fallbacks(
            "totally unparseable blob", [json_parser, regex_parser]
        )
