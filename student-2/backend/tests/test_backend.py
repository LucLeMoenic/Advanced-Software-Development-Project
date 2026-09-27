import json

import pytest
import httpx

from app import ItineraryGenerator, create_app
from ai_clients import IntegrationError, INSUFFICIENT_ANSWER, RagClient, validate_summary


@pytest.fixture(autouse=True)
def isolated_modes(monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("MCP_ENABLED", "false")
    monkeypatch.setenv("RAG_ENABLED", "false")


def test_summary_rejects_zero_duration_before_decimal_allocation():
    summary = FakeIntegrations().summary(12)
    summary.update(endDate="2026-10-09", totalBudget=0, dailyBudgetAllocation=0)
    with pytest.raises(IntegrationError) as caught:
        validate_summary(summary, 12)
    assert caught.value.status == 502


@pytest.mark.parametrize("status,expected", [(503, 503), (504, 504), (404, 502), (200, 200)])
def test_rag_http_client_uses_fixed_feature_and_maps_status(monkeypatch, status, expected):
    def respond(request):
        assert request.url.path == "/query"
        assert json.loads(request.content) == {"feature": "student-2", "question": "Budget?"}
        return httpx.Response(status, json={"answer": INSUFFICIENT_ANSWER, "citations": [], "confidence": "insufficient"})

    client_type = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client_type(transport=httpx.MockTransport(respond), **kwargs))
    client = RagClient("http://rag.invalid/")
    if expected == 200:
        assert client.advice("Budget?")["confidence"] == "insufficient"
    else:
        with pytest.raises(IntegrationError) as caught:
            client.advice("Budget?")
        assert caught.value.status == expected


def test_rag_client_stops_and_closes_oversized_response(monkeypatch):
    class LargeStream(httpx.AsyncByteStream):
        consumed = 0
        closed = False

        async def __aiter__(self):
            for index in range(100):
                self.consumed += 1024
                yield b"x" * 1024

        async def aclose(self):
            self.closed = True

    stream = LargeStream()
    client_type = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=stream))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client_type(transport=transport, **kwargs))
    with pytest.raises(IntegrationError) as caught:
        RagClient("http://rag.invalid").advice("Budget?")
    assert caught.value.status == 502
    assert stream.consumed == 16384
    assert stream.closed


class FakeIntegrations:
    def __init__(self):
        self.calls = []

    def summary(self, trip_id):
        self.calls.append(trip_id)
        return {"tripId": trip_id, "destination": "Tokyo", "startDate": "2026-10-10", "endDate": "2026-10-12",
                "dayCount": 3, "stopCount": 4, "plannedDayCount": 2, "unplannedDays": [3],
                "totalBudget": 900, "dailyBudgetAllocation": 300}

    def advice(self, question):
        self.calls.append(question)
        return {"answer": "Budget is the trip total. [budget#1]", "confidence": "high",
                "citations": [{"source": "Budget", "chunk_id": "budget#1", "snippet": "Trip total", "score": 0.8}]}


def test_integrations_are_disabled_without_upstream_calls():
    fake = FakeIntegrations()
    client = create_app(mcp_client=fake, rag_client=fake).test_client()
    for path in ("/api/trips/12/mcp-summary", "/api/itinerary-advice"):
        response = client.post(path)
        assert response.status_code == 503
        assert response.json["error"]["code"] == "mode_disabled"
    assert fake.calls == []


def test_enabled_integrations_use_fixed_contracts():
    fake = FakeIntegrations()
    client = create_app(mcp_client=fake, rag_client=fake, settings={"MCP_ENABLED": True, "RAG_ENABLED": True}).test_client()
    assert client.post("/api/trips/12/mcp-summary").json["summary"]["tripId"] == 12
    assert client.post("/api/itinerary-advice", json={"question": " Budget? "}).json["confidence"] == "high"
    assert fake.calls == [12, "Budget?"]


@pytest.mark.parametrize("payload", [None, [], {}, {"question": True}, {"question": " "}, {"question": "a" * 1001}, {"question": "Budget?", "feature": "student-3"}])
def test_advice_rejects_invalid_input_before_call(payload):
    fake = FakeIntegrations()
    response = create_app(rag_client=fake, settings={"RAG_ENABLED": True}).test_client().post("/api/itinerary-advice", json=payload)
    assert response.status_code == 400
    assert fake.calls == []


@pytest.mark.parametrize("code,status", [("dependency_unavailable", 503), ("dependency_timeout", 504), ("trip_not_found", 404)])
def test_integration_failure_mapping(code, status):
    class FailedClient:
        def summary(self, trip_id):
            raise IntegrationError(code)

    response = create_app(mcp_client=FailedClient(), settings={"MCP_ENABLED": True}).test_client().post("/api/trips/12/mcp-summary")
    assert response.status_code == status
    assert response.headers["X-Correlation-ID"]


@pytest.mark.parametrize("body,status", [
    ({"answer": INSUFFICIENT_ANSWER, "citations": [], "confidence": "insufficient"}, 200),
    ({"answer": "Unsupported advice", "citations": [], "confidence": "high"}, 502),
    ({"answer": "A guess", "citations": [], "confidence": "insufficient"}, 502),
])
def test_advice_validates_upstream_results(body, status):
    class Client:
        def advice(self, question):
            return body

    response = create_app(rag_client=Client(), settings={"RAG_ENABLED": True}).test_client().post("/api/itinerary-advice", json={"question": "Budget?"})
    assert response.status_code == status


class FakeDatabase:
    def __init__(self):
        self.calls = []
        self.trip = {"id": 11, "user": "Alex", "destination": "Osaka", "startDate": "2026-10-10", "endDate": "2026-10-11", "budget": 1500, "interests": "food"}

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if method == "POST" and path == "/api/data/itineraries":
            return {**self.trip, "stops": [{"id": 12, **payload["stops"][0]}]}, 201
        if method == "POST" and path == "/api/data/stops":
            return {"id": len(self.calls), **payload}, 201
        if method == "GET" and path == "/api/data/stops/7":
            return {"id": 7, "tripId": 11, "day": 1, "activity": "Old stop", "notes": "", "sortOrder": 0}, 200
        if method == "PUT" and path == "/api/data/stops/7":
            return {"id": 7, **payload}, 200
        if method == "PUT" and path == "/api/data/trips/11/stops":
            return [{"id": index + 20, "tripId": 11, **stop} for index, stop in enumerate(payload["stops"])], 200
        if method == "GET" and path.endswith("/11"):
            return {**self.trip, "stops": []}, 200
        return [], 200


class FakeGenerator:
    def generate(self, trip, existing_stops=None, target_day=None):
        if target_day is not None:
            return [{"day": target_day, "activity": "Market walk", "notes": "Taste local food.", "sortOrder": 0}], "ai"
        return [
            {"day": 1, "activity": "Market walk", "notes": "Taste local food.", "sortOrder": 0},
            {"day": 1, "activity": "Castle visit", "notes": "Visit the grounds.", "sortOrder": 1},
            {"day": 2, "activity": "Museum visit", "notes": "See local exhibits.", "sortOrder": 0},
            {"day": 2, "activity": "Canal walk", "notes": "Walk before dinner.", "sortOrder": 1},
        ], "ai"


def valid_trip():
    return {"user": "Alex", "destination": "Osaka", "startDate": "2026-10-10", "endDate": "2026-10-11", "budget": 1500, "interests": "food"}


@pytest.mark.parametrize("path,payload", [
    ("/api/trips", valid_trip()),
    ("/api/trips/11/regenerate", None),
    ("/api/stops/7/regenerate", None),
])
def test_disabled_ai_never_calls_generator(path, payload):
    class ForbiddenGenerator:
        def generate(self, *args):
            raise AssertionError("Disabled AI must not call the generator")

    client = create_app(FakeDatabase(), ForbiddenGenerator(), settings={"AI_ENABLED": False}).test_client()
    response = client.post(path, json=payload)
    assert response.status_code in (200, 201)
    assert response.get_json()["generationMode"] == "fallback"
    assert client.get("/api/capabilities").get_json() == {
        "aiEnabled": False, "mcpEnabled": False, "ragEnabled": False,
    }


def test_invalid_mode_configuration_fails_at_startup():
    with pytest.raises(ValueError, match="MCP_ENABLED"):
        create_app(settings={"MCP_ENABLED": "yes"})


def test_create_runs_orchestration_and_persists_stops():
    database = FakeDatabase()
    response = create_app(database, FakeGenerator()).test_client().post("/api/trips", json=valid_trip())
    assert response.status_code == 201
    body = response.get_json()
    assert body["generationMode"] == "ai"
    assert [stage["stage"] for stage in body["agentTrace"]] == ["Plan", "Act", "Observe", "Adapt"]
    assert any(call[1] == "/api/data/itineraries" for call in database.calls)
    assert not any(call[1] == "/api/data/trips" for call in database.calls)


def test_invalid_trip_does_not_call_dependencies():
    database = FakeDatabase()
    response = create_app(database, FakeGenerator()).test_client().post("/api/trips", json={"destination": "X"})
    assert response.status_code == 400
    assert database.calls == []


def test_generator_validation_and_fallback_cover_every_day():
    trip = valid_trip()
    with pytest.raises(ValueError):
        ItineraryGenerator.validate([{"day": 1, "activity": "Museum", "notes": "Morning visit"}], trip)
    fallback = ItineraryGenerator.fallback(trip)
    assert len(fallback) == 4
    assert {stop["day"] for stop in fallback} == {1, 2}


def test_generator_requests_the_exact_itinerary_array_schema(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            generated = FakeGenerator().generate(valid_trip())[0]
            return {"response": json.dumps([
                {key: stop[key] for key in ("day", "activity", "notes")}
                for stop in generated
            ])}

    request_payload = {}

    def post(url, json, timeout):
        request_payload.update(json)
        return Response()

    monkeypatch.setattr("app.requests.post", post)
    stops, mode = ItineraryGenerator("http://ollama", "llama3.2:3b").generate(valid_trip())

    assert mode == "ai"
    assert len(stops) == 4
    assert request_payload["format"]["type"] == "array"
    assert request_payload["format"]["minItems"] == 4
    assert request_payload["format"]["maxItems"] == 4


def test_regenerate_one_stop_preserves_its_day_and_identity():
    response = create_app(FakeDatabase(), FakeGenerator()).test_client().post("/api/stops/7/regenerate")
    assert response.status_code == 200
    assert response.get_json()["stop"]["id"] == 7
    assert response.get_json()["stop"]["activity"] == "Market walk"


def test_regenerate_trip_uses_one_atomic_replace_without_deleting_first():
    database = FakeDatabase()
    response = create_app(database, FakeGenerator()).test_client().post("/api/trips/11/regenerate")
    assert response.status_code == 200
    assert any(call[0:2] == ("PUT", "/api/data/trips/11/stops") for call in database.calls)
    assert not any(call[0] == "DELETE" for call in database.calls)


def test_invalid_stop_is_rejected_before_database_call():
    database = FakeDatabase()
    response = create_app(database, FakeGenerator()).test_client().post("/api/trips/11/stops", json={"day": 0})
    assert response.status_code == 400
    assert database.calls == []


def test_stop_outside_trip_is_rejected_before_database_write():
    database = FakeDatabase()
    response = create_app(database, FakeGenerator()).test_client().post("/api/trips/11/stops", json={
        "day": 3, "activity": "Outside trip", "notes": "", "sortOrder": 0,
    })
    assert response.status_code == 400
    assert "2-day trip" in response.get_json()["error"]["fields"]["day"]
    assert [call[0:2] for call in database.calls] == [("GET", "/api/data/trips/11")]


def test_stop_update_validates_target_trip_before_write():
    database = FakeDatabase()
    response = create_app(database, FakeGenerator()).test_client().put("/api/stops/7", json={
        "tripId": 11, "day": 3, "activity": "Outside trip", "notes": "", "sortOrder": 0,
    })
    assert response.status_code == 400
    assert not any(call[0] == "PUT" for call in database.calls)


def test_stop_update_preserves_server_owned_trip_id():
    database = FakeDatabase()
    response = create_app(database, FakeGenerator()).test_client().put("/api/stops/7", json={
        "tripId": 999, "day": 1, "activity": "Updated stop", "notes": "New notes", "sortOrder": 99,
    })
    assert response.status_code == 200
    write = next(call for call in database.calls if call[0:2] == ("PUT", "/api/data/stops/7"))
    assert write[2]["tripId"] == 11
    assert write[2]["sortOrder"] == 0