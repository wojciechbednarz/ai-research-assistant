from langgraph.graph import StateGraph, END, START
from typing import TypedDict, Callable
from rag.retrieval import search
from chromadb.api import Collection
from httpx import AsyncClient
from agent.agent import Agent
import json


class AgentState(TypedDict):
    question: str
    documents: list[dict]
    analysis: str
    answer: str
    messages: list
    tool_trace: list


class NodeHandler:
    def __init__(self, client: AsyncClient):
        self.client = client
        self.agent = Agent(client)

    async def analyze(self, state: AgentState) -> dict:
        full_messages, message = await self.agent.analyze_llm(state["messages"], state["documents"], state["question"])
        if message.get("tool_calls"):
            return {"messages": full_messages}
        return {"messages": full_messages, "analysis": message["content"]}

    async def respond(self, state: AgentState) -> dict:
        answer = await self.agent.respond_llm(
            state["question"], state["documents"], state["analysis"]
        )
        return {"answer": answer}

    async def route_after_analyze(self, state: AgentState) -> str:
        """Determines the next node after analysis based on the content of the analysis."""
        last_message = state["messages"][-1]
        if last_message.get("tool_calls"):
            return "retrieve"
        return "respond"


def make_retrieve_node(collection: Collection) -> Callable:
    def retrieve(state: AgentState) -> dict:
        last_message = state["messages"][-1] if state["messages"] else None
        if last_message and last_message.get("tool_calls"):
            args = json.loads(last_message["tool_calls"][0]["function"]["arguments"])
            query = args.get("query", state["question"])
            documents = search(collection, query)
            tool_message = {"role": "tool", "tool_call_id": last_message["tool_calls"][0]["id"], "content": str(documents)}
            return {"documents": documents, "messages": state["messages"] + [tool_message]}
        else:
            documents = search(collection, state["question"])
            return {"documents": documents}
    return retrieve


async def run_graph(question: str, collection: Collection, client: AsyncClient) -> None:
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", make_retrieve_node(collection))
    node_handler = NodeHandler(client)
    graph.add_node("analyze", node_handler.analyze)
    graph.add_node("respond", node_handler.respond)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "analyze")
    graph.add_conditional_edges(
        "analyze",
        node_handler.route_after_analyze,
        {"retrieve": "retrieve", "respond": "respond"},
    )
    graph.add_edge("respond", END)
    return await graph.compile().ainvoke(
        {"question": question, "messages": [], "tool_trace": []}
    )
