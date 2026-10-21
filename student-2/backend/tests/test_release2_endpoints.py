import importlib.util
from io import BytesIO
import threading
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import urlparse
from urllib.response import addinfourl

import pytest
from werkzeug.serving import make_server

from app import DatabaseClient, DependencyError, create_app


@pytest.fixture
def client(tmp_path):
    path = Path(__file__).resolve().parents[2] / "database" / "app.py"
    spec = importlib.util.spec_from_file_location("itinerary_database", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = make_server("127.0.0.1", 0, module.create_app(str(tmp_path / "itinerary.db")))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    app = create_app(database_client=DatabaseClient(f"http://127.0.0.1:{server.server_port}"), settings={
        "AI_ENABLED": False, "MCP_ENABLED": False, "RAG_ENABLED": False, "MULTI_AGENT_ENABLED": False,
    })
    try:
        yield app.test_client()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def criteria():
    return {"user": "Synthetic Release 2 traveller", "destination": "Osaka", "startDate": "2026-11-01",
            "endDate": "2026-11-02", "budget": 900, "interests": "Parks"}


def test_create_endpoint_persists_complete_disabled_ai_itinerary(client):
    response = client.post("/api/trips", json=criteria())
    assert response.status_code == 201
    saved = response.json
    assert saved["generationMode"] == "fallback" and saved["id"] > 0
    assert len(saved["stops"]) == 4
    assert [stop["day"] for stop in saved["stops"]] == [1, 1, 2, 2]
    reopened = client.get(f"/api/trips/{saved['id']}").json
    assert reopened["stops"] == saved["stops"] and reopened["budget"] == 900


def test_create_endpoint_rejects_invalid_input_without_write(client):
    before = client.get("/api/trips").json
    response = client.post("/api/trips", json={**criteria(), "endDate": "2026-01-01"})
    assert response.status_code == 400
    assert response.json["error"]["fields"]
    assert client.get("/api/trips").json == before


def test_update_endpoint_persists_changes_and_preserves_stops(client):
    saved = client.post("/api/trips", json=criteria()).json
    url = f"/api/trips/{saved['id']}"
    response = client.put(url, json={**criteria(), "budget": 1200})
    assert response.status_code == 200 and response.json["budget"] == 1200
    reopened = client.get(url).json
    assert reopened["budget"] == 1200 and reopened["stops"] == saved["stops"]


def test_update_endpoint_invalid_and_missing_records(client):
    saved = client.post("/api/trips", json=criteria()).json
    url = f"/api/trips/{saved['id']}"
    before = client.get(url).json
    assert client.put(url, json={**criteria(), "budget": -1}).status_code == 400
    assert client.get(url).json == before
    assert client.put("/api/trips/999999", json=criteria()).status_code == 404


def test_cloud_smoke_uses_current_disabled_routes_and_cleans_up(client, monkeypatch):
    path = Path(__file__).resolve().parents[3] / "scripts" / "deploy" / "smoke_cloud.py"
    spec = importlib.util.spec_from_file_location("smoke_cloud", path)
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    before = client.get("/api/trips").json

    def gateway(request, timeout):
        path = urlparse(request.full_url).path
        if path.startswith("/itinerary-api/"):
            response = client.open(path.replace("/itinerary-api/", "/api/", 1),
                                   method=request.method, data=request.data, content_type="application/json")
            return addinfourl(BytesIO(response.data), {}, request.full_url, response.status_code)
        return addinfourl(BytesIO(b"<html>Gateway fixture</html>"), {}, request.full_url, 200)

    monkeypatch.setattr(smoke, "urlopen", gateway)
    student1_check = Mock()
    monkeypatch.setattr(smoke, "check_student1", student1_check)
    smoke.run("https://smoke.invalid")
    student1_check.assert_called_once()
    assert client.get("/api/trips").json == before


@pytest.mark.parametrize("method,path", [("post", "/api/trips"), ("put", "/api/trips/1")])
def test_endpoint_dependency_outage_is_explicit(method, path):
    class Unavailable:
        def request(self, *args):
            raise DependencyError("The database is unavailable.")
    client = create_app(database_client=Unavailable(), settings={"AI_ENABLED": False}).test_client()
    result = getattr(client, method)(path, json=criteria())
    assert result.status_code == 503 and result.json["error"]["code"] == "dependency_unavailable"
