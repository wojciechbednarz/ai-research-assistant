# AI Research Assistant

I built this to learn how MCP servers work from the inside. The RAG layer and LangGraph agent came along as the natural host for the MCP tools.

A RAG-powered personal knowledge assistant that answers questions from your own documents using a LangGraph agent pipeline and ChromaDB vector store.

## What it does

Ingest your markdown notes into ChromaDB, then query them in natural language. The `/research` endpoint runs a 3-node LangGraph agent: retrieve relevant chunks → analyze with LLM → respond with a grounded answer.

Additionally exposes tools via a custom MCP server (JSON-RPC 2.0 + STDIO), allowing Claude Desktop to query your knowledge base directly.

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
 MCP Server         ← STDIO transport, tools/list + tools/call
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
| Observability | Langfuse (`@observe` traces on LangGraph nodes) |
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
# Add OPEN_ROUTER_API_KEY + LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY to .env

# 3. Start everything
docker compose up --build
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

> **First-run note:** the first `/ingest` call downloads ChromaDB's `all-MiniLM-L6-v2` embedding model (~80 MB) on the fly. Allow 30–60 seconds for warmup. Subsequent calls reuse the cached model. A `GPU device discovery failed` warning is expected — embeddings fall back to CPU inside the container.

**Example — grounded answer (English query against Polish corpus):**
```json
{
  "answer": "Function Calling (or Tool Use) is a methodology that enables Large Language Models (LLMs) to interact with external tools and services by generating structured data...",
  "sources": [
    "Schemat łączenia LLM z narzędziami (Function Calling / Tool Use)",
    "Minimalny przykład prezentujący to, jak agent posługuje się narzędziami znajduje się w katalogu 01_02_tools.",
    "Zobaczmy teraz jak Function Calling działa w praktyce poprzez przykład [01_02_tool_use]..."
  ],
  "confidence": "high"
}
```

**Example — honest refusal when corpus is insufficient:**
```json
{
  "answer": "Nie ma informacji na temat RAG w dostarczonych materiałach.",
  "sources": [],
  "confidence": "low"
}
```
The agent refuses to fabricate when retrieval doesn't surface grounded sources, rather than guessing from related concepts. This is enforced by the `respond_llm` prompt and validated by Langfuse traces.

## Project structure

```
ai-research-assistant/
├── main.py              # FastAPI app, lifespan, endpoints
├── config.py            # Settings from .env (lazy-loaded via lru_cache)
├── schemas.py           # Pydantic models: MCPTool, RespondResponse
├── api.py               # HTTP client helper (OpenRouter)
├── helpers.py           # File utilities, text chunking, token estimation
├── display.py           # Rich console output (CLI only)
├── rag/
│   ├── ingestion.py     # ChromaDB client, batch upsert
│   └── retrieval.py     # Hybrid BM25 + vector search, re-ranking
├── agent/
│   ├── graph.py         # LangGraph StateGraph, build_graph/run_graph
│   ├── agent.py         # LLM calls (analyze + respond)
│   ├── decorators.py    # @llm_retry with exponential backoff
│   ├── llm_output_parser.py  # JSON/regex/LLM fallback parsers
│   ├── prompts.py       # System + user prompt templates
│   └── tools/           # Tool definitions and handlers
├── mcp_server/
│   ├── __main__.py      # Entry point: python -m mcp_server
│   ├── server.py        # Tool registry, dispatcher
│   ├── protocol.py      # JSON-RPC 2.0 message builders, error codes
│   └── transport.py     # STDIO read/write loop + validation
├── tests/
│   ├── conftest.py      # Testcontainers fixtures (ChromaDB, TestClient)
│   ├── test_integration.py   # End-to-end tests (requires Docker)
│   ├── test_helpers.py
│   ├── test_llm_output_parser.py
│   ├── test_mcp_protocol.py
│   ├── test_retrieval.py
│   └── test_schemas.py
├── raw/                 # Your markdown documents
├── docker-compose.yml   # ChromaDB + app services
└── .env.example         # Environment variable template
```

## Lessons

**Agentic RAG vs naive RAG.** A single retrieval + prompt is brittle. Wrapping retrieval in a LangGraph loop with a conditional edge (`tool_calls -> re-retrieve`) lets the agent ask for more context before committing to an answer. The agent can decide mid-run that the first retrieval was not enough.

**MCP from scratch.** Implemented JSON-RPC 2.0 over STDIO without an SDK. This showed me exactly what `initialize`, `tools/list`, and `tools/call` look like on the wire, which SDK abstractions normally hide. The STDIO transport is newline-delimited JSON; the protocol complexity is in the dispatcher, not the transport.

**Retry + fallback decorator.** OpenRouter would occasionally return 500s mid-session and the whole pipeline would crash. Added `@llm_retry` with exponential backoff and a fallback model swap after max retries. Should have done it from the start.

**ChromaDB persistence and API drift.** Lost a full ingestion run after the first `docker compose down`. ChromaDB requires `IS_PERSISTENT=TRUE` and a named Docker volume mounted at `/data`, which is not obvious from the quickstart docs. Also hit the v1 to v2 API path migration the hard way when the healthcheck would not pass.

**Anti-hallucination as a feature.** The system returns `confidence: low` with empty `sources` when retrieval doesn't surface grounded chunks, rather than synthesizing from prior LLM knowledge. This is enforced by the `respond_llm` system prompt and validated against vague queries (e.g. "What is AI?" → honest refusal) and specific queries (e.g. "function calling" → high-confidence cited answer). For a portfolio piece, the refusal mode is more credible than the happy path — anyone can get an LLM to talk; getting it to shut up about things it cannot ground takes prompt discipline.

**Multilingual retrieval works without configuration.** The corpus is Polish (AI Devs 4 course material). The `all-MiniLM-L6-v2` embedding model is multilingual enough that English queries ("function calling") retrieve Polish chunks and the LLM responds in the query's language. Polish queries return Polish answers with Polish sources. No language-specific tuning was needed — the embedding model and the synthesis LLM handle the language switch transparently.

**Acronym gaps in semantic search.** "Co to jest RAG?" returned empty sources even though the corpus is *about* building RAG systems. The course rarely uses the literal acronym "RAG" — it spells out "Retrieval Augmented Generation" or describes the pattern in Polish. The embedding model did not bridge the acronym → concept gap. Two options for production: (1) maintain a synonym/alias map at query time, (2) augment ingestion with a glossary chunk that links acronyms to their expansions. Worth knowing before a recruiter asks "why did this query miss?"

**STDIO transport is a deadlock minefield.** Three independent bugs stacked during the MCP HTTP bridge work: (1) `for line in sys.stdin:` uses 8KB block buffering on pipes — small JSON messages never trigger a yield, use `sys.stdin.readline()` instead; (2) ChromaDB SQLite locks block the second process when both main and the MCP subprocess open the same collection — fixed with lazy init in the subprocess; (3) `await process.stderr.read(1024)` blocks until 1024 bytes or EOF — never use it as a non-blocking probe, wrap with `asyncio.wait_for(..., timeout=...)` if you need a peek. Streamable HTTP transport (planned next) eliminates all three categories — HTTP frames are self-delimiting and there are no shared file locks.
