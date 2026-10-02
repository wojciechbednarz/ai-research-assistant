import asyncio
import json
import logging
from dataclasses import dataclass
from typing import TypedDict

from chromadb.api import Collection
from httpx import AsyncClient
from langchain_core.runnables import RunnableConfig
from langfuse import observe
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt

from agent.agent import Agent
from agent.tools.handlers import summarize_text
from config import get_settings
from rag.retrieval import hybrid_search

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    question: str
    documents: list[dict]
    analysis: str
    answer: str
    messages: list
    tool_trace: list
    tool_iterations: int
    approved: str


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


def _parse_tool_call(message: dict) -> ToolCall | None:
    """Parse and validate a tool call from an LLM message. Returns None if malformed."""
    try:
        tc = message["tool_calls"][0]
        return ToolCall(
            id=tc["id"],
            name=tc["function"]["name"],
            args=json.loads(tc["function"]["arguments"]),
        )
    except (KeyError, json.JSONDecodeError):
        return None


def _tool_message(tool_call_id: str, content: str) -> dict:
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


class NodeHandler:
    """Holds all LangGraph node callables and the shared resources they need."""

    def __init__(self, client: AsyncClient, collection: Collection):
        self.client = client
        self.collection = collection
        self.agent = Agent(client)

    async def retrieve(self, state: AgentState) -> dict:
        last_message = state["messages"][-1] if state["messages"] else None
        tool_call = _parse_tool_call(last_message) if last_message else None
        if tool_call is None:
            return await self._plain_search(state)
        return await self._dispatch_tool(tool_call, state)

    async def _dispatch_tool(self, tool_call: ToolCall, state: AgentState) -> dict:
        handlers = {
            "search_documents": self._handle_search,
            "summarize_text": self._handle_summarize,
        }
        handler = handlers.get(tool_call.name, self._handle_search)
        return await handler(tool_call, state)

    async def _handle_search(self, tool_call: ToolCall, state: AgentState) -> dict:
        query = tool_call.args.get("query", state["question"])
        documents = await asyncio.to_thread(hybrid_search, self.collection, query)
        return {
            "documents": documents,
            "messages": state["messages"] + [_tool_message(tool_call.id, str(documents))],
            "tool_iterations": state.get("tool_iterations", 0) + 1,
        }

    async def _handle_summarize(self, tool_call: ToolCall, state: AgentState) -> dict:
        text = tool_call.args.get("text", state["question"])
        content = await summarize_text(text=text, max_tokens=500, client=self.client)
        return {
            "messages": state["messages"] + [_tool_message(tool_call.id, content)],
            "tool_iterations": state.get("tool_iterations", 0) + 1,
        }

    async def _plain_search(self, state: AgentState) -> dict:
        documents = await asyncio.to_thread(hybrid_search, self.collection, state["question"])
        return {"documents": documents}

    async def analyze(self, state: AgentState) -> dict:
        full_messages, message = await self.agent.analyze_llm(
            prior_messages=state["messages"],
            retrieved_docs=state["documents"],
            question=state["question"],
        )
        if message.get("tool_calls"):
            return {"messages": full_messages}
        return {"messages": full_messages, "analysis": message["content"]}

    async def respond(self, state: AgentState) -> dict:
        answer = await self.agent.respond_llm(
            state["question"], state["documents"], state["analysis"]
        )
        return {"answer": answer}

    async def approve(self, state: AgentState):
        logger.debug("APPROVE node entered, prior approved=%s", state.get("approved"))
        approved = interrupt("Do you approve this action?")
        logger.debug("APPROVE resumed with=%s", approved)
        return {"approved": approved}

    async def route_after_analyze(self, state: AgentState) -> str:
        """
        Decide whether to retrieve more docs or respond, based on presence of tool calls
        and iteration count.
        :state: The current state after the analyze node, including messages and tool
            call history.
        :returns: "retrieve" to loop back to retrieval, or "respond" to proceed to
            response generation.
        """
        last_message = state["messages"][-1]
        iterations = state.get("tool_iterations", 0)
        max_iter = get_settings().MAX_TOOL_ITERATIONS
        if last_message.get("tool_calls") and iterations < max_iter:
            return "retrieve"
        if iterations >= max_iter:
            logger.warning(
                "Max tool iterations (%d) reached for question: %s",
                max_iter,
                state["question"],
            )
        return "respond"

    async def route_after_approval(self, state: AgentState) -> str:
        return "respond" if state.get("approved") else "abort"


def build_graph(collection: Collection, client: AsyncClient) -> CompiledStateGraph:
    """Build and compile the agent graph once at startup."""
    node_handler = NodeHandler(client, collection)
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", node_handler.retrieve)
    graph.add_node("analyze", node_handler.analyze)
    graph.add_node("approve", node_handler.approve)
    graph.add_node("respond", node_handler.respond)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "analyze")
    graph.add_conditional_edges(
        "analyze",
        node_handler.route_after_analyze,
        {"retrieve": "retrieve", "respond": "approve"},
    )
    graph.add_conditional_edges(
        "approve",
        node_handler.route_after_approval,
        {"respond": "respond", "abort": END},
    )
    graph.add_edge("respond", END)
    checkpointer = InMemorySaver()

    return graph.compile(checkpointer=checkpointer)


@observe(capture_input=False)
async def run_graph(question: str, compiled_graph: CompiledStateGraph) -> dict:
    config: RunnableConfig = {"configurable": {"thread_id": 1}}
    state = await compiled_graph.aget_state(config)
    logger.debug(
        "Graph state: next=%s checkpoint=%s",
        state.next,
        state.config.get("configurable", {}).get("checkpoint_id"),
    )
    return await compiled_graph.ainvoke(
        input={
            "question": question,
            "messages": [],
            "tool_trace": [],
            "tool_iterations": 0,
        },
        config=config,
    )
