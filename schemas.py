from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class MCPTool(BaseModel):
    name: str = Field(
        description="Name of the MCP tool to invoke (e.g. 'search_documents', 'summarize_text', 'get_metadata').",
        examples=["search_documents"],
    )
    arguments: dict = Field(
        description="Arguments dict matching the tool's inputSchema.",
        examples=[{"query": "Co to jest AI Devs 4?"}],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "search_documents",
                    "arguments": {"query": "Co to jest AI Devs 4?"},
                },
                {
                    "name": "summarize_text",
                    "arguments": {"text": "Long passage of text to summarize..."},
                },
                {
                    "name": "get_metadata",
                    "arguments": {"text": ""},
                },
            ]
        }
    )


class RespondResponse(BaseModel):
    answer: str
    sources: list[str]
    confidence: Literal["high", "medium", "low"]
