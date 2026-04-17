from fastapi import FastAPI, Request
from rag.ingestion import ChromaDB

from agent.graph import run_graph
from pathlib import Path
from helpers import get_all_files_from_dir
import logging
from rich.logging import RichHandler
from contextlib import asynccontextmanager
from httpx import AsyncClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.DEBUG, handlers=[RichHandler()])
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    app.state.chroma_db = ChromaDB(collection_name="ai-research-assistant")
    app.state.http_client = AsyncClient(timeout=60)
    yield
    await app.state.http_client.aclose()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to the AI Research Assistant!"}


@app.get("/health")
async def health():
    """Healthcheck endpoint"""
    return {"App is running"}


@app.post("/ingest")
async def ingest_all_documents(request: Request) -> None:
    """Endpoint to trigger research process"""

    chroma_db = request.app.state.chroma_db
    collection = chroma_db.collection
    logger.debug("Collection ready: %s", collection.name)

    docs_raw_dir = Path(__file__).parent / "raw"
    all_markdown_files = get_all_files_from_dir(docs_raw_dir)
    chroma_db.load_and_ingest(all_markdown_files, collection)
    return {"message": "Ingestion complete"}


@app.post("/get_collection_count")
async def get_collection_count(request: Request) -> int:
    """Endpoint to get the number of documents in the collection"""
    chroma_db = request.app.state.chroma_db
    collection = chroma_db.collection
    return chroma_db.count_collection(collection.name)


@app.get("/research")
async def research(request: Request, query: str) -> dict:
    """Main research function that queries the vector database."""
    chroma_db = request.app.state.chroma_db
    async_client = request.app.state.http_client
    collection = chroma_db.collection
    query_result = await run_graph(query, collection, async_client)
    return {"answer": query_result["answer"]}
