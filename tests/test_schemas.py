import pytest
from schemas import RespondResponse, MCPTool


@pytest.mark.parametrize("confidence", ["high", "medium", "low"])
def test_respond_response_valid_confidence(confidence):
    r = RespondResponse(answer="test answer", sources=["src1"], confidence=confidence)
    assert r.confidence == confidence


def test_respond_response_fields():
    r = RespondResponse(answer="answer", sources=["a", "b"], confidence="high")
    assert r.answer == "answer"
    assert r.sources == ["a", "b"]


def test_mcp_tool_valid():
    t = MCPTool(name="search_documents", arguments={"query": "what is AI?"})
    assert t.name == "search_documents"
    assert t.arguments["query"] == "what is AI?"
