# Code Review — `ai-research-assistant`

**Date:** 2026-04-24
**Scope:** Full codebase (~1,066 LOC across ~20 `.py` files) reviewed against the unified general + AI/LLM backend checklist (`code-review.md` + `code-review-ai.md`).
**Reviewer role:** Senior / Lead Backend Engineer.

Findings are grouped into three buckets. Each item cites `file:line` and states a concrete fix.

---

## Must fix — blocks merge

### 1. Hardcoded Kinesis example baked into every first `analyze_llm` call
**File:** `agent/agent.py:37-40`

```python
{"role": "user", "content": "What is the retention period of Kinesis?"},
{"role": "assistant", "content": None, "tool_calls": [{"type": "function", "function": {"name": "search_documents", "arguments": "{\"query\": \"Kinesis retention period\"}"}}]},
```

Every first-turn request ships a fabricated prior exchange to the LLM. Pollutes context, wastes tokens, biases answers toward AWS/Kinesis framings. Remove — this is a dev artifact.

### 2. `/health` returns a Python `set`, not a dict
**File:** `main.py:71`

```python
return {"App is running"}
```

That's a set literal. FastAPI's JSON encoder will fail or coerce it to an array — not the documented health-check shape. Change to `{"status": "App is running"}`.

### 3. `@llm_retry` hardcodes `self` as the first arg; breaks non-method callers
**Files:** `agent/decorators.py:21`, applied at `agent/tools/handlers.py:13` (`summarize_text`)

```python
async def wrapper(self, *args, **kwargs) -> dict | str:
    ...
    return await func(self, *args, **kwargs)
```

`summarize_text` is a plain async function, not a method. Any caller doing `await summarize_text(text=..., max_tokens=..., client=...)` raises `TypeError: missing 'self'`. Drop `self` from the wrapper signature (`async def wrapper(*args, **kwargs)`), or move `summarize_text` into a class.

### 4. MCP `summarize_text` handler is a string formatter, not a summary
**File:** `mcp_server/server.py:114`

```python
TOOLS["summarize_text"]["handler"] = lambda args: f"Summary of {args['text'][:100]}"
```

Any MCP client (Claude Desktop, tests) invoking `tools/call` on `summarize_text` gets silent garbage. Either wire it to the LLM or remove the tool from the registry.

### 5. Subprocess dies on any handler exception
**Files:** `mcp_server/transport.py:26-29`, `mcp_server/server.py:92`

`run_server` has no try/except around `handler_fn(request)`. If a lambda handler raises (malformed args, ChromaDB hiccup, LLM failure), the while-loop crashes, the subprocess exits, and the next `/mcp_server` request hangs on `await process.stdout.readline()` (main.py:138) forever. Wrap handler dispatch in try/except → return `ERROR_INTERNAL`. Also wrap the individual `TOOLS[name]["handler"](args)` call in `server.py:92`.

### 6. LLM tool-call arguments parsed without validation
**File:** `agent/graph.py:51,56`

```python
args = json.loads(last_message["tool_calls"][0]["function"]["arguments"])
...
"tool_call_id": last_message["tool_calls"][0]["id"],
```

If the LLM hallucinates malformed `tool_calls` (missing `function`, non-JSON `arguments`, no `id`), `json.loads` or the key accesses raise and bubble up through LangGraph — whole `/research` request fails. Validate structure and fall back to plain retrieval on the original question.

### 7. `summarize_text` tool call has no graph branch — silent wrong behavior
**File:** `agent/graph.py:47-67`

`TOOL_LIST` advertises both `search_documents` and `summarize_text` to the LLM (`agent/tools/definitions.py:28`), but `make_retrieve_node` only handles `search_documents`. If the LLM picks `summarize_text`, the `if` at line 50 is true (it has `tool_calls`) but `args.get("query", state["question"])` falls back to the user question and runs a search — not a summary. The tool-call loop never terminates correctly. Either drop `summarize_text` from `TOOL_LIST` until implemented, or add a `summarize` branch.

### 8. Sync ChromaDB calls block the event loop
**Files:** `rag/retrieval.py:9`, `rag/ingestion.py:17,23,31`, `agent/graph.py:53,64`, `main.py:84,93`

`chromadb.HttpClient` is a synchronous HTTP client. Called from FastAPI async handlers and LangGraph async nodes without `asyncio.to_thread`. Under concurrent traffic, one slow ChromaDB query stalls every other request on the same worker. Wrap all ChromaDB calls in `asyncio.to_thread(...)` or use an async HTTP client against ChromaDB's REST API directly.

---

## Should fix — important but not blocking

### 9. `response_cache` is unbounded and unlocked
**File:** `main.py:33,99-109`

Plain dict, no eviction, no write lock. Under diverse queries this grows without bound; under concurrent identical queries you can double-call the LLM. Use `cachetools.TTLCache` and guard writes with an `asyncio.Lock`.

### 10. Dead code — entire `agent/tools/handlers.py` module is unused
`dispatch_handler` and `HANDLERS` are never called. The only live tool path is in `agent/graph.py` retrieve node. Delete or wire up.

### 11. Bare `except Exception`
**Files:** `main.py:144`, `agent/decorators.py:27,39`

Each hides real bugs (e.g., `BrokenPipeError` on the MCP subprocess, `ValidationError` from Pydantic, `asyncio.TimeoutError`) behind a generic 500 / retry. Catch the specific expected types and use `logger.exception(...)` to preserve tracebacks.

### 12. No raw-response logging before parsing LLM output
**Files:** `agent/agent.py:55,84`, `api.py:18`

Violates the Debug Response Ritual. Add a `debug_response(response)` or `logger.debug("openrouter raw", extra={"response": response})` before `response["choices"][0]["message"]` on every integration.

### 13. Wrong return-type hints
- `api.py:8` — `-> httpx.Response` but returns `dict` (`response.json()`).
- `rag/retrieval.py:6` — `-> QueryResult` but returns `list[dict]`.
- `agent/graph.py:71` — `-> None` but returns the final state dict.
- `main.py:75` — `-> None` but returns `{"message": "Ingestion complete"}`.

Mypy/ruff would catch most of these if wired into CI.

### 14. `confidence: str` accepts any string
**File:** `schemas.py:37`

System prompt instructs the LLM to return `high|medium|low`, but Pydantic lets any garbage through. Use `Literal["high", "medium", "low"]` so a hallucinated value is caught at the response boundary, not two layers later.

### 15. No length limit on `/research?query=`
**File:** `main.py:97`

Unbounded user input forwarded to the LLM. Set `query: str = Query(..., min_length=1, max_length=500)` — cost + DOS control.

### 16. No `temperature` / `max_tokens` in OpenRouter payloads
**File:** `agent/agent.py:46-51,76-80`

Relies on provider defaults that vary across models and can silently change. Set explicitly in `config.py` (e.g., `temperature=0` for `respond_llm`, `temperature=0.2` for `analyze_llm`).

### 17. Mutable-list accumulator signature in `analyze_llm`
**File:** `agent/agent.py:25-56`

Takes `messages: list`, shadows it with a new list on first call, returns `(messages + [message], message)`. The pattern is non-obvious: the caller only works because it does `full_messages, message = await ...`. Rename the parameter to `prior_messages` and add a docstring clarifying that callers must use the returned list.

### 18. `@observe` may not capture OpenRouter token usage / latency
**Files:** `agent/agent.py:23,58`, `agent/graph.py:70`

Decorator wraps `analyze_llm`/`respond_llm`, but the actual HTTP call is a level deeper in `send_post_request`. Langfuse sees inputs/outputs but may miss provider-level metadata. Verify in the Langfuse UI that cost/token metrics show up; if not, instrument `send_post_request` instead.

### 19. `chunk_text` infinite-loop risk
**File:** `helpers.py:27-41`

If `overlap >= chunk_size`, `start += chunk_size - overlap <= 0` and the loop never advances. Add a guard that raises `ValueError` when `overlap >= chunk_size`.

### 20. Inconsistent logging
`main.py` + `agent/decorators.py` use `logging`; everywhere else uses `print_header`/Rich to stderr (`display.py:7`). In production, Rich output isn't parseable by log aggregators. Standardise on `logging`; reserve Rich for CLI entrypoints only.

### 21. Payload logged in full on every LLM call
**File:** `api.py:10`

```python
print_header(f"Sending POST request to {url} with payload: {payload}")
```

Bearer token is in headers (not logged, good), but the full message history — including user queries that could be PII in some contexts — is dumped to stderr. At minimum, move to DEBUG level; ideally log a summary (model, message_count, question_length) not the raw payload.

### 22. MCP init response is read and discarded
**File:** `main.py:47`

`await process.stdout.readline()` — no check that it's a `result` for `id: 1`. If the subprocess errors on init, the app starts anyway and the first `/mcp_server` request hangs on `readline()`. Parse the init response, assert shape, fail-fast on error.

### 23. `estimate_tokens = len(text) // 3`
**File:** `helpers.py:64`

Rough for English, materially worse for the Polish corpus in `raw/`. Polish averages closer to 2 chars/token. Under-budgeting risks silent truncation. Use `tiktoken` (`cl100k_base`) for accuracy.

### 24. Only E2E smoke tests exist
**File:** `tests/test_smoke.py`

No unit tests for `chunk_text`, `parse_message`, `truncate_to_budget`, `route_after_analyze`, or the retry decorator. All tests require a running Docker stack + OpenRouter — slow, flaky, expensive. Add a `tests/unit/` tier that mocks `send_post_request` and uses an in-process ChromaDB.

### 25. Cache test doesn't prove the cache was hit
**File:** `tests/test_smoke.py:85-93`

Two identical LLM calls at low temperature will often produce identical JSON. Mock the cache or count calls on a spy to actually verify cache hit.

### 26. Required but unused env vars
**File:** `config.py:13,17`

`OPENAI_API_KEY` is declared required but never imported. `FIRECRAWL_API_KEY` is required but Firecrawl isn't used anywhere in the code. App refuses to start without envars it doesn't need. Remove or mark `Optional[str] = None`.

### 27. `parse_message` is dead code
**File:** `helpers.py:44-59`

Defined but not imported anywhere. Either wire it into `mcp_server/transport.py` (which currently does no validation of JSON-RPC shape) or delete.

---

## Consider — low priority

### 28. Graph compiled on every request
**File:** `agent/graph.py:72-85`

The graph structure is static. Compile once at startup (store on `app.state.compiled_graph`), reuse across requests. Small latency win, cleaner code.

### 29. Lazy singleton via mutable list
**File:** `mcp_server/server.py:100-105`

`_db: list[ChromaDB] = []` used as a cell. Works, but `functools.cache`/`lru_cache` on `get_collection`, or a small class, would read more naturally.

### 30. System prompt invites infinite tool loops
**File:** `agent/prompts.py:1-5`

"You MUST call search_documents if the provided context does not contain a clear answer" — no loop guard in the graph. If the corpus genuinely lacks the answer, the LLM can keep calling `search_documents` in a cycle. Add a `max_tool_iterations` counter in `AgentState` and enforce it in `route_after_analyze`.

### 31. Tool schemas duplicated between OpenAI and MCP formats
**Files:** `agent/tools/definitions.py`, `mcp_server/server.py:7-55`

Different wire formats, so not strictly DRY-able, but a single Pydantic source of truth with per-format emitters would prevent drift when you add a fourth tool.

### 32. Magic numbers
- `main.py:32` — `timeout=60`
- `main.py:103` — `3600` TTL
- `agent/agent.py:31,65` — `max_tokens=3000`
- `rag/retrieval.py:6` — `n_results=3`

Move to `config.py`.

### 33. `print_results` in `display.py:36-55` appears unused
Dev/exploratory artifact. Remove if nothing references it.

### 34. `Firecrawl` / `trio` deps listed but not imported in any `.py` file
Remove from `pyproject.toml` to keep the dep tree honest.

---

## Numbered fix checklist

Work through in this order — sequence matters; later fixes can conflict with earlier ones if done out of order.

### Step 1 — Correctness (Must fix first)
1. Remove hardcoded Kinesis example — `agent/agent.py:37-40`
2. Fix `/health` set-vs-dict bug — `main.py:71`
3. Fix `@llm_retry` wrapper to not hardcode `self` — `agent/decorators.py:21`
4. Replace `summarize_text` MCP placeholder handler or remove the tool — `mcp_server/server.py:114`
5. Wrap handler dispatch in try/except so subprocess loop survives errors — `mcp_server/transport.py:26`, `mcp_server/server.py:92`
6. Validate LLM `tool_calls` shape before parsing — `agent/graph.py:51,56`
7. Either drop `summarize_text` from `TOOL_LIST` or add a real graph branch — `agent/tools/definitions.py:28` + `agent/graph.py:47-67`

### Step 2 — Error handling
8. Replace bare `except Exception` with specific types and `logger.exception` — `main.py:144`, `agent/decorators.py:27,39`

### Step 3 — Async and I/O
9. Wrap all sync ChromaDB calls in `asyncio.to_thread` — `rag/retrieval.py:9`, `rag/ingestion.py:17,23,31`, `agent/graph.py:53,64`, `main.py:84,93`
10. Parse and validate MCP init response, fail-fast on error — `main.py:47`

### Step 4 — Security & boundaries
11. Add length limit on `/research?query=` — `main.py:97`
12. Tighten `confidence` schema to `Literal["high", "medium", "low"]` — `schemas.py:37`
13. Add explicit `temperature` / `max_tokens` to OpenRouter payloads — `agent/agent.py:46-51,76-80`

### Step 5 — Structure (DRY, naming, dead code)
14. Delete `agent/tools/handlers.py` (or wire it up) — whole module
15. Delete `helpers.py:parse_message` if not wired into MCP transport — `helpers.py:44-59`
16. Fix wrong return-type hints — `api.py:8`, `rag/retrieval.py:6`, `agent/graph.py:71`, `main.py:75`
17. Rename mutable-list accumulator param to `prior_messages` + docstring — `agent/agent.py:25`
18. Add guard in `chunk_text` for `overlap >= chunk_size` — `helpers.py:27-41`
19. Make `OPENAI_API_KEY` and `FIRECRAWL_API_KEY` optional or remove — `config.py:13,17`
20. Remove unused `Firecrawl` / `trio` deps from `pyproject.toml`
21. Move magic numbers (timeout, TTL, max_tokens, n_results) to `config.py`
22. Replace `response_cache` with `cachetools.TTLCache` + `asyncio.Lock` — `main.py:33,99-109`
23. Compile the LangGraph once at startup — `agent/graph.py:72-85`
24. Consider `functools.cache` / small class over `_db: list[ChromaDB]` cell — `mcp_server/server.py:100-105`
25. Replace naive `estimate_tokens` with `tiktoken` — `helpers.py:62-64`
26. Remove unused `print_results` if nothing references it — `display.py:36-55`

### Step 6 — Observability
27. Add raw-response logging / `debug_response` before parsing LLM output — `agent/agent.py:55,84`, `api.py:18`
28. Verify Langfuse `@observe` captures OpenRouter tokens/latency; if not, instrument `send_post_request` — `agent/agent.py:23,58`
29. Standardise on `logging` (move `print_header` observability calls behind DEBUG) — project-wide, starting at `api.py:10`
30. Redact or summarise payload in the POST-request log line — `api.py:10`
31. Add loop guard (`max_tool_iterations`) to prevent infinite tool-call cycles — `agent/graph.py` + `AgentState`

### Step 7 — Tests
32. Add a `tests/unit/` tier with mocked OpenRouter and in-process ChromaDB — covering `chunk_text`, `parse_message`, `truncate_to_budget`, `route_after_analyze`, `@llm_retry` behavior
33. Prove cache hit in the caching test via a spy on `send_post_request` — `tests/test_smoke.py:85-93`

### Step 8 — Re-review
Re-run the three-bucket summary. Any remaining "Must fix" item blocks merge.
