import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request, HTTPException, Query
from rag.ingestion import ChromaDB

from agent.graph import build_graph, run_graph
from pathlib import Path
from helpers import get_all_files_from_dir
import logging
from rich.logging import RichHandler
from contextlib import asynccontextmanager
from httpx import AsyncClient
from schemas import MCPTool, RespondResponse
from config import get_settings
import json
from cachetools import TTLCache

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.DEBUG, handlers=[RichHandler()])
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    s = get_settings()
    app.state.chroma_db = ChromaDB(collection_name="ai-research-assistant")
    app.state.http_client = AsyncClient(timeout=s.HTTP_TIMEOUT)
    app.state.response_cache = TTLCache(maxsize=s.CACHE_MAX_SIZE, ttl=s.CACHE_TTL)
    app.state.compiled_graph = build_graph(
        app.state.chroma_db.collection, app.state.http_client
    )
    app.state.cache_lock = asyncio.Lock()
    cmd = (sys.executable, "-m", "mcp_server")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=Path(__file__).parent,
    )
    init = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}) + "\n"
    notif = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(init.encode())
    process.stdin.write(notif.encode())
    await process.stdin.drain()
    raw = await process.stdout.readline()
    try:
        init_response = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"MCP subprocess init returned invalid JSON: {raw!r}") from e
    if "error" in init_response:
        raise RuntimeError(f"MCP subprocess init failed: {init_response['error']}")
    if init_response.get("id") != 1 or "result" not in init_response:
        raise RuntimeError(f"Unexpected MCP init response: {init_response}")
    logger.debug(
        "MCP subprocess initialised: %s", init_response["result"].get("serverInfo")
    )

    app.state.mcp_process = process
    app.state.mcp_lock = asyncio.Lock()

    yield

    process.terminate()
    await process.wait()
    await app.state.http_client.aclose()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to the AI Research Assistant!"}


@app.get("/health")
async def health():
    """Healthcheck endpoint"""
    return {"message": "App is running"}


@app.post("/ingest")
async def ingest_all_documents(request: Request) -> dict:
    """Endpoint to trigger research process"""

    chroma_db = request.app.state.chroma_db
    collection = chroma_db.collection
    logger.debug("Collection ready: %s", collection.name)

    docs_raw_dir = Path(__file__).parent / "raw"
    all_markdown_files = get_all_files_from_dir(docs_raw_dir)
    await asyncio.to_thread(chroma_db.load_and_ingest, all_markdown_files, collection)
    return {"message": "Ingestion complete"}


@app.post("/get_collection_count")
async def get_collection_count(request: Request) -> int:
    """Endpoint to get the number of documents in the collection"""
    chroma_db = request.app.state.chroma_db
    collection = chroma_db.collection
    return await asyncio.to_thread(chroma_db.count_collection, collection.name)


@app.get("/research")
async def research(
    request: Request, query: str = Query(..., min_length=1, max_length=500)
) -> RespondResponse:
    """Main research function that queries the vector database."""
    cache = request.app.state.response_cache
    cached = cache.get(query)
    if cached:
        return cached
    query_result = await run_graph(query, request.app.state.compiled_graph)
    answer = query_result["answer"]
    async with request.app.state.cache_lock:
        cache[query] = answer
    return answer


@app.post("/mcp_server")
async def mcp_server(tool: MCPTool, request: Request) -> dict:
    """
    Endpoint to call MCP tools. Expects a JSON body with the following structure:
    :tool: MCPTool - a Pydantic model with 'name' and 'arguments' fields representing the tool to call and its arguments.
    :returns: dict - the result of the tool call, or an error message if the call fails.
    """
    try:
        process = request.app.state.mcp_process
        lock = request.app.state.mcp_lock

        tool_call_msg = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": tool.name, "arguments": tool.arguments},
                }
            )
            + "\n"
        )
        async with lock:
            process.stdin.write(tool_call_msg.encode())
            await process.stdin.drain()
            line = await process.stdout.readline()
        logger.debug(f"MCP raw response: {line!r}")
        return json.loads(line).get("result", {})
    except json.JSONDecodeError as err:
        logger.error(f"JSON decode error: {err}")
        raise HTTPException(status_code=502, detail="Incorrect request body") from err
    except Exception as err:
        logger.exception("Error running MCP server")
        raise HTTPException(status_code=500, detail="Error running MCP server") from err
