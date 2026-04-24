import pytest
from pathlib import Path
from helpers import (
    chunk_text,
    estimate_tokens,
    truncate_to_budget,
    parse_message,
    get_markdown_content,
)


def test_chunk_text_basic():
    text = "a" * 2000
    chunks = chunk_text(text, chunk_size=800, overlap=150)
    assert all(len(c) <= 800 for c in chunks)
    assert len(chunks) > 1


def test_chunk_text_overlap():
    # Use distinct chars so comparison is meaningful
    text = "".join(chr(ord("a") + i % 26) for i in range(2000))
    chunks = chunk_text(text, chunk_size=800, overlap=150)
    for i in range(len(chunks) - 1):
        # Only check pairs where the next chunk is at least as long as the overlap
        if len(chunks[i + 1]) >= 150:
            assert chunks[i][-150:] == chunks[i + 1][:150]


def test_chunk_text_overlap_guard():
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("some text", chunk_size=100, overlap=100)


def test_chunk_text_empty():
    assert chunk_text("") == []


def test_chunk_text_short():
    text = "hello world"
    chunks = chunk_text(text, chunk_size=800, overlap=150)
    assert chunks == [text]


def test_estimate_tokens():
    assert isinstance(estimate_tokens("Hello, world!"), int)
    assert estimate_tokens("Hello, world!") > 0
    # longer text has more tokens
    assert estimate_tokens("word " * 100) > estimate_tokens("word")


def test_truncate_to_budget_fits():
    docs = ["hi there"] * 3
    result = truncate_to_budget(docs, max_tokens=10000)
    assert result.count("hi there") == 3


def test_truncate_to_budget_truncates():
    # ~50 tokens each; 10 docs total; budget forces early cutoff
    chunk = "The quick brown fox jumps over the lazy dog. " * 5
    docs = [chunk] * 10
    result = truncate_to_budget(docs, max_tokens=60)
    assert result.count(chunk) < 10


def test_parse_message_valid():
    msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    parsed = parse_message(msg)
    assert parsed["method"] == "tools/list"
    assert parsed["id"] == 1


def test_parse_message_missing_method():
    with pytest.raises(ValueError, match="method"):
        parse_message({"jsonrpc": "2.0", "id": 1})


def test_parse_message_wrong_version():
    with pytest.raises(ValueError, match="2.0"):
        parse_message({"jsonrpc": "1.0", "id": 1, "method": "ping"})


def test_get_markdown_content(tmp_path: Path):
    f = tmp_path / "doc.md"
    f.write_text("---\ntitle: Test\n---\nActual content here\n")
    assert get_markdown_content(f) == "Actual content here"


def test_get_markdown_content_no_delimiters(tmp_path: Path):
    f = tmp_path / "plain.md"
    f.write_text("plain content")
    assert get_markdown_content(f) == "plain content"
