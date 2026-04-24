import os
import pytest
import httpx

try:
    from testcontainers.chroma import ChromaContainer as _ChromaContainer

    def _make_container():
        return _ChromaContainer("chromadb/chroma")

except ImportError:
    from testcontainers.core.container import DockerContainer

    def _make_container():
        return DockerContainer("chromadb/chroma").with_exposed_ports(8000)


@pytest.fixture(scope="session", autouse=True)
def chroma_container():
    with _make_container() as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(8000)

        # Poll until Chroma is ready
        base = f"http://{host}:{port}"
        for endpoint in ("/api/v2/heartbeat", "/api/v1/heartbeat"):
            try:
                for _ in range(30):
                    try:
                        r = httpx.get(f"{base}{endpoint}", timeout=2)
                        if r.status_code == 200:
                            break
                    except httpx.TransportError:
                        import time

                        time.sleep(1)
                break
            except Exception:
                continue

        os.environ["CHROMA_HOST"] = host
        os.environ["CHROMA_PORT"] = str(port)
        yield container


@pytest.fixture(scope="session")
def app(chroma_container):
    from config import get_settings

    get_settings.cache_clear()
    from main import app

    return app


@pytest.fixture(scope="session")
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def ingest(client):
    resp = client.post("/ingest")
    assert resp.status_code == 200, f"Ingestion preflight failed: {resp.text}"
