# AI Research Assistant

A RAG-powered personal knowledge assistant that answers questions from your own documents using a LangGraph agent pipeline and ChromaDB vector store.

A portfolio project demonstrating production-grade LLM engineering patterns.

## What it does

Ingest your markdown notes into ChromaDB, then query them in natural language. The `/research` endpoint runs a 3-node LangGraph agent: retrieve relevant chunks → analyze with LLM → respond with a grounded answer.

Saturday extension: exposes tools via a custom MCP server (JSON-RPC 2.0 + STDIO), allowing Claude Desktop to query your knowledge base directly.

## Architecture

```
Markdown notes
      ↓
  ChromaDB          ← document ingestion + chunking + embeddings
      ↓
LangGraph Agent
  ├── retrieve      ← similarity search (top-3 chunks)
  ├── analyze       ← LLM synthesizes retrieved context
  └── respond       ← LLM produces grounded final answer
      ↓
 FastAPI REST        ← /research endpoint
      ↓
 MCP Server         ← STDIO transport, tools/list + tools/call (Sat Apr 18)
      ↓
Claude Desktop      ← queries your notes via MCP protocol
```

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI + uvicorn |
| Vector store | ChromaDB (Docker) |
| Agent | LangGraph |
| LLM | OpenRouter (Gemini Flash Lite / any model) |
| HTTP client | httpx (async) |
| Runtime | Python 3.13, uv |
| Infrastructure | Docker Compose |

## Setup

**Prerequisites:** Docker, Python 3.13, uv

```bash
# 1. Clone and install
git clone <repo-url>
cd ai-research-assistant
uv sync

# 2. Environment
cp .env.example .env
# Add your OPEN_ROUTER_API_KEY to .env

# 3. Start ChromaDB
docker compose up -d

# 4. Start the API
uv run uvicorn main:app --port 8001 --reload
```

## Usage

```bash
# Ingest your markdown documents (place .md files in raw/)
curl -X POST http://localhost:8001/ingest

# Query the knowledge base
curl "http://localhost:8001/research?query=What+is+function+calling"

# Check how many chunks are stored
curl -X POST http://localhost:8001/get_collection_count
```

**Example response:**
```json
{
  "answer": "Function calling is a mechanism that allows LLMs to invoke external tools..."
}
```

## Project structure

```
ai-research-assistant/
├── main.py              # FastAPI app, lifespan, endpoints
├── config.py            # Settings from .env
├── api.py               # HTTP client helper (OpenRouter)
├── helpers.py           # File utilities, text chunking
├── display.py           # Rich console output
├── rag/
│   ├── ingestion.py     # ChromaDB client, batch upsert
│   └── retrieval.py     # Similarity search, result flattening
├── agent/
│   ├── graph.py         # LangGraph StateGraph, node wiring
│   └── agent.py         # LLM calls (analyze + respond)
├── mcp_server/
│   ├── server.py        # Tool registry, dispatcher, main()
│   ├── protocol.py      # JSON-RPC 2.0 message builders, error codes
│   └── transport.py     # STDIO read/write loop
├── raw/                 # Your markdown documents (gitignored if sensitive)
├── docker-compose.yml   # ChromaDB service
└── .env.example         # Environment variable template
```

## Roadmap

- [x] RAG foundation — ChromaDB ingestion + similarity retrieval
- [x] LangGraph 3-node agent — retrieve → analyze → respond
- [x] Function calling + conditional routing (tool-mediated retrieval loop)
- [x] MCP server — JSON-RPC 2.0 + STDIO, 3 tools (`search_documents`, `summarize_text`, `get_metadata`), tested end-to-end via STDIO
- [ ] Langfuse observability — token tracking, latency, cost per request
- [ ] Claude Desktop integration — query your notes from Claude UI
