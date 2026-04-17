from langgraph.graph import StateGraph, END, START
from typing import TypedDict, Callable
from rag.retrieval import search
from chromadb.api import Collection
from httpx import AsyncClient
from agent.agent import Agent


class AgentState(TypedDict):
    question: str
    documents: list[dict]
    analysis: str
    answer: str


class NodeHandler:
    def __init__(self, client: AsyncClient):
        self.client = client
        self.agent = Agent(client)

    async def analyze(self, state: AgentState) -> dict:
        analysis = await self.agent.analyze_llm(state["question"], state["documents"])
        return {"analysis": analysis}

    async def respond(self, state: AgentState) -> dict:
        answer = await self.agent.respond_llm(
            state["question"], state["documents"], state["analysis"]
        )
        return {"answer": answer}


def make_retrieve_node(collection: Collection) -> Callable:
    def retrieve(state: AgentState) -> dict:
        documents = search(collection, state["question"])
        print(
            f"DEBUG - Retrieved documents for question '{state['question']}': {documents}"
        )
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
    graph.add_edge("analyze", "respond")
    graph.add_edge("respond", END)
    return await graph.compile().ainvoke({"question": question})
