"""Release 2 post-commit CI/CD endpoint tests for the Student 3 backend/API.

The two endpoint functions under test (run by the "Post-commit endpoint tests"
step of .github/workflows/student-3.yml):

    1. GET  /api/attractions   (list + ?category= filter)
    2. POST /api/attractions   (create + validation)

Unlike test_backend_attractions.py, which mocks database_client, these tests
run the REAL backend app against the REAL database app: database_client's HTTP
transport is swapped for the database service's Flask test client, so a request
travels frontend-facing route -> database_client -> /api/data/* -> SQLite
exactly as in the deployed system, with a fresh temp database per test.
"""

import sys

import pytest

import database_client as backend_db_client


class _DatabaseResponse:
    """Just enough of requests.Response for database_client's use."""

    def __init__(self, flask_response):
        self.status_code = flask_response.status_code
        self._flask_response = flask_response

    def json(self):
        return self._flask_response.get_json()


@pytest.fixture
def db_service(database_client):
    """A plain (non context-preserving) client for the real database app.

    The conftest `database_client`/`backend_client` fixtures use
    `with app.test_client()`, which keeps each Flask app context open after a
    request; nesting one app's request inside the other's then pops contexts in
    the wrong order. They are used here only for setup (temp DATABASE_PATH,
    schema, fresh module load); the calls use plain clients.
    """
    return sys.modules["student3_database_app"].app.test_client()


@pytest.fixture
def api(backend_client, db_service, monkeypatch):
    """The real backend app, with database_client's HTTP transport replaced by
    the real database app (no mocks of either service's logic)."""

    def route_to_database_app(method, path, params=None, json=None, **_ignored):
        return _DatabaseResponse(db_service.open(path, method=method, query_string=params, json=json))

    monkeypatch.setattr(backend_db_client, "_request", route_to_database_app)
    return sys.modules["student3_backend_app"].app.test_client()


def _seed(db_client, *rows):
    """Insert rows straight into the database service, independent of POST /api/attractions."""
    for row in rows:
        assert db_client.post("/api/data/attractions", json=row).status_code == 201


SIGHT = {"name": "Opera House", "category": "sight", "description": "Harbour icon", "rating": 4.8}
CAFE = {"name": "Corner Cafe", "category": "restaurant", "description": None, "rating": 4.1}
KAYAK = {"name": "Harbour Kayak", "category": "activity", "description": "Paddle tour", "rating": 4.5}


# --------------------------------------------------------------------------
# Endpoint 1: GET /api/attractions
# --------------------------------------------------------------------------


def test_get_attractions_returns_empty_list_for_empty_catalogue(api):
    response = api.get("/api/attractions")

    assert response.status_code == 200
    assert response.get_json() == []


def test_get_attractions_returns_all_rows_in_id_order_with_full_shape(api, db_service):
    _seed(db_service, SIGHT, CAFE, KAYAK)

    response = api.get("/api/attractions")

    assert response.status_code == 200
    body = response.get_json()
    assert [a["name"] for a in body] == ["Opera House", "Corner Cafe", "Harbour Kayak"]
    assert [a["id"] for a in body] == sorted(a["id"] for a in body)
    assert set(body[0]) == {"id", "name", "category", "description", "rating"}
    assert body[0]["rating"] == 4.8
    assert body[1]["description"] is None


@pytest.mark.parametrize(
    ("category", "expected_names"),
    [
        ("sight", ["Opera House"]),
        ("restaurant", ["Corner Cafe"]),
        ("activity", ["Harbour Kayak"]),
    ],
)
def test_get_attractions_category_filter_returns_only_that_category(
    api, db_service, category, expected_names
):
    _seed(db_service, SIGHT, CAFE, KAYAK)

    response = api.get(f"/api/attractions?category={category}")

    assert response.status_code == 200
    body = response.get_json()
    assert [a["name"] for a in body] == expected_names
    assert {a["category"] for a in body} == {category}


def test_get_attractions_unknown_category_returns_empty_list_not_error(api, db_service):
    _seed(db_service, SIGHT)

    response = api.get("/api/attractions?category=nightclub")

    assert response.status_code == 200
    assert response.get_json() == []


def test_get_attractions_returns_502_when_database_unreachable(api, monkeypatch):
    def unreachable(method, path, **kwargs):
        raise backend_db_client.DatabaseUnavailableError("connection refused")

    monkeypatch.setattr(backend_db_client, "_request", unreachable)

    response = api.get("/api/attractions")

    assert response.status_code == 502
    assert response.get_json()["error"] == "database_unavailable"


# --------------------------------------------------------------------------
# Endpoint 2: POST /api/attractions
# --------------------------------------------------------------------------


def test_post_attraction_creates_row_and_returns_201_with_id(api):
    response = api.post("/api/attractions", json=SIGHT)

    assert response.status_code == 201
    created = response.get_json()
    assert isinstance(created["id"], int)
    assert {k: created[k] for k in SIGHT} == SIGHT


def test_post_attraction_is_persisted_and_visible_via_get_endpoints(api):
    created = api.post("/api/attractions", json=KAYAK).get_json()

    listed = api.get("/api/attractions").get_json()
    fetched = api.get(f"/api/attractions/{created['id']}")

    assert [a["id"] for a in listed] == [created["id"]]
    assert fetched.status_code == 200
    assert fetched.get_json()["name"] == "Harbour Kayak"


def test_post_attraction_trims_whitespace_and_defaults_optional_fields_to_null(api):
    response = api.post("/api/attractions", json={"name": "  Quiet Park  ", "category": " sight "})

    assert response.status_code == 201
    created = response.get_json()
    assert created["name"] == "Quiet Park"
    assert created["category"] == "sight"
    assert created["description"] is None
    assert created["rating"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"category": "sight"},
        {"name": "No Category"},
        {"name": "   ", "category": "sight"},
        {"name": "Blank Category", "category": "   "},
    ],
    ids=["empty-body", "missing-name", "missing-category", "blank-name", "blank-category"],
)
def test_post_attraction_rejects_missing_required_fields_with_400_and_stores_nothing(api, payload):
    response = api.post("/api/attractions", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"
    assert api.get("/api/attractions").get_json() == []


def test_post_attraction_with_non_json_body_is_rejected_with_400(api):
    response = api.post("/api/attractions", data="name=Form&category=sight")

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_post_attraction_returns_502_when_database_unreachable(api, monkeypatch):
    def unreachable(method, path, **kwargs):
        raise backend_db_client.DatabaseUnavailableError("connection refused")

    monkeypatch.setattr(backend_db_client, "_request", unreachable)

    response = api.post("/api/attractions", json=SIGHT)

    assert response.status_code == 502
    assert response.get_json()["error"] == "database_unavailable"
