# Testcontainers Migration Plan

Migrate `tests/test_smoke.py` from "requires `docker-compose up` + running uvicorn"
to "requires only Docker + Python". Chroma runs as an ephemeral container managed
by pytest; FastAPI runs in-process via `TestClient`.

---

## 1. Current state (baseline)

- `tests/test_smoke.py` hits `http://localhost:8001` via `httpx.Client`.
- Prerequisite: `docker-compose up -d` (brings up `chromadb` + `app` services).
- `config.py:25` instantiates `settings = Settings()` at module import time;
  pydantic-settings reads `CHROMA_HOST` / `CHROMA_PORT` from env immediately.
- `rag/ingestion.py:14-15` constructs `chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)`.
- Tests ERROR (fixture setup) when the stack isn't up — WinError 10061.

## 2. Design decision

**Chosen: Chroma container + in-process FastAPI via `TestClient`.**

| Approach | What it replaces | Verdict |
|---|---|---|
| A. Chroma container + in-process app | `docker-compose up` AND running uvicorn | Chosen. Fast, hermetic. |
| B. Chroma container + keep running app | Only Chroma dependency | Rejected — keeps uvicorn-start friction for no benefit. |

## 3. The import-order trap

`settings = Settings()` runs at `config.py` import time. Testcontainers binds a
**dynamic host port** — the container's internal `8000` maps to a random host
port. Env vars must be set BEFORE any import reaches `config.py`.

### Two ways to handle it

**Option 1 — Lazy settings (recommended).**
Refactor `config.py`:

- Replace `settings = Settings()` with:
  - `@lru_cache(maxsize=1)`
  - `def get_settings() -> Settings: return Settings()`
- Update callers (at minimum `rag/ingestion.py:14-15`, plus any other
  `from config import settings` call site) to call `get_settings()`.
- Tests set env vars in a fixture; first `get_settings()` call inside the app
  picks them up.

**Option 2 — No refactor, but never import `main` at test-module top level.**
Import `main` inside fixtures AFTER env is set. Current `test_smoke.py` only
imports `httpx/os/pytest`, so this works. Fragile: any future
`from main import app` at the top of a test module silently breaks the suite.

**Recommendation: Option 1.** Small refactor, removes a landmine.

## 4. Dependencies

Add to `[dependency-groups].dev` in `pyproject.toml`:

- `testcontainers[chroma]>=4.8`
  - Gives `testcontainers.chroma.ChromaContainer`.
  - If the extra is flaky on Python 3.13, fall back to the generic
    `testcontainers.core.container.DockerContainer("chromadb/chroma:0.5.x")`.
- Host prerequisite: Docker Desktop running.

### Pin the image

Pin Chroma to a known version (e.g. `chromadb/chroma:0.5.x`) rather than
`:latest` — avoids surprise breakage from upstream pushes.

## 5. Fixture architecture (`tests/conftest.py` — new file)

All fixtures session-scoped.

### `chroma_container` (autouse=True, session)

1. Start `ChromaContainer(image="chromadb/chroma:0.5.x")` (or the generic
   `DockerContainer` variant, `.with_exposed_ports(8000)`).
2. Wait for readiness:
   - Prefer `wait_for_logs(container, "Application startup complete")`.
   - OR poll `http://<host>:<port>/api/v1/heartbeat` with `httpx` until 200.
3. Set:
   - `os.environ["CHROMA_HOST"] = container.get_container_host_ip()`
   - `os.environ["CHROMA_PORT"] = str(container.get_exposed_port(8000))`
4. `yield container`.
5. Teardown stops the container automatically via context manager.

### `app` (session, depends on `chroma_container`)

- Lazy import inside the function body: `from main import app`.
- If you took Option 1 above, also clear any cached settings:
  `from config import get_settings; get_settings.cache_clear()`.
- Return `app`.

### `client` (session, depends on `app`)

- `from fastapi.testclient import TestClient`
- `with TestClient(app) as c: yield c`
- Tests receive `client` unchanged — API surface of the fixture is identical.

### `ingest` (autouse=True, session, depends on `client`)

- Keep as-is; it seeds Chroma once per session via `POST /ingest`.

### Remove

- `require_server` fixture in `test_smoke.py:27-33` — the container IS the
  server guarantee.
- `client` fixture in `test_smoke.py:21-24` — moved to `conftest.py`.
- `BASE_URL` constant in `test_smoke.py:17` — no longer needed.

## 6. Changes to `tests/test_smoke.py`

- Delete lines 17 (`BASE_URL`), 21-24 (`client`), 27-33 (`require_server`).
- Delete the docstring references to `docker-compose up -d` (lines 6-11).
  Replace with: "Prerequisite: Docker running. `pytest tests/test_smoke.py -v`."
- Test functions themselves (`test_ingest_returns_success_message`, etc.)
  do NOT change — they still receive `client` by fixture injection.

## 7. Mark the module

Add `pytestmark = pytest.mark.integration` at the top of `test_smoke.py`.

Register the marker in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: tests that spin up Docker containers (slow)",
]
```

This keeps future fast unit tests runnable without Docker via
`pytest -m "not integration"`.

## 8. Trade-offs and gotchas

- **First run is slow.** Testcontainers pulls the Chroma image if not cached.
  Subsequent runs are fast (image cached, container startup ~3-5s).
- **Volume isolation is automatic.** Each session gets a fresh container —
  no more duplicate-ingest concern across runs. But add an explicit
  idempotency test: call `/ingest` twice, assert collection count unchanged.
- **CI needs Docker.** GitHub Actions `ubuntu-latest` has it; confirm any
  self-hosted runner does too. Without Docker-in-Docker, this suite skips.
- **OpenRouter / Firecrawl still hit real APIs.** Testcontainers only
  replaces Chroma. For truly hermetic tests, mock LLM / crawler via
  `httpx.MockTransport` or `respx`. For smoke-tier, real calls are fine.
- **Port collisions are impossible.** `get_exposed_port(8000)` returns the
  dynamic host port — never hardcode `8000` in tests.

## 9. Acceptance criteria

- [ ] `pytest tests/test_smoke.py -v` passes on a machine with only
      **Docker + Python** installed — no `docker-compose up`, no manual uvicorn.
- [ ] `docker-compose.yml` is untouched (still used for local dev runs).
- [ ] Two consecutive test runs produce identical results — no state leak.
- [ ] `pytest -m "not integration"` runs without Docker (zero tests selected
      for now; future-proof).
- [ ] `config.py` either refactored to lazy `get_settings()` (Option 1) OR
      documented constraint in `conftest.py` that `main` must never be
      imported at test-module top level (Option 2).

## 10. Order of operations (suggested)

1. Refactor `config.py` to `get_settings()` + update callers. Run existing
   tests with Docker up — they should still pass.
2. Add `testcontainers[chroma]` to dev deps. `uv sync`.
3. Create `tests/conftest.py` with the four fixtures. Run tests with Docker
   running but **no compose stack** — should pass.
4. Strip `require_server`, `client` fixture, and `BASE_URL` from
   `test_smoke.py`. Add `pytestmark = pytest.mark.integration`.
5. Register `integration` marker in `pyproject.toml`.
6. Run `pytest -v` with no containers, no compose. Tests spin up Chroma
   themselves. Final confirmation.

## 11. Out of scope

- LLM / Firecrawl mocking (separate concern; do after TC migration lands).
- Splitting smoke into true unit + integration tiers.
- Parallelization (`pytest-xdist`) — session-scoped container means each
  worker would need its own; save for later.
