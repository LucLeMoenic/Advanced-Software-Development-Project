import os
import sys

import pytest
import responses

# Make app.py / db_client.py importable when pytest is invoked from the
# repository root.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app  # noqa: E402

# Hostnames that do not resolve, so an un-mocked request can never accidentally
# reach a real service.
DATABASE_API_URL = "http://test-database:8080"
OLLAMA_URL = "http://test-ollama:11434"

# A tag no real registry serves. If a test passes while asserting on this, the
# model really did come from configuration rather than a literal in the code.
APPLICATION_MODEL = "test-model:0b"


@pytest.fixture
def database_url():
    return DATABASE_API_URL


@pytest.fixture
def ollama_url():
    return OLLAMA_URL


@pytest.fixture
def model_tag():
    return APPLICATION_MODEL


@pytest.fixture
def client(database_url, ollama_url, model_tag):
    app = create_app(
        {
            "DATABASE_API_URL": database_url,
            "OLLAMA_URL": ollama_url,
            "APPLICATION_MODEL": model_tag,
        }
    )
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Grounding data
#
# Trimmed copies of the seeded Japan row and its children. Using real seed text
# rather than "foo"/"bar" is what makes the grounding assertions meaningful: a
# prompt that contains "cherry blossom" can only have got it from the database.
# ---------------------------------------------------------------------------

SEEDED_DESTINATION = {
    "id": 1,
    "country": "Japan",
    "visa_requirement": "visa-free",
    "notes": "Short-stay tourist entry for Australian passport holders.",
}

SEEDED_WEATHER_NOTES = [
    {
        "id": 1,
        "destination_id": 1,
        "season": "Spring (Mar-May)",
        "notes": "Mild days and heavy cherry blossom crowds.",
    },
    {
        "id": 2,
        "destination_id": 1,
        "season": "Summer (Jun-Aug)",
        "notes": "Hot and humid with the tsuyu rains through June.",
    },
]

SEEDED_TRANSIT_OPTIONS = [
    {
        "id": 1,
        "destination_id": 1,
        "type": "rail",
        "details": "A Japan Rail Pass covers most Shinkansen services.",
    },
]


@pytest.fixture
def destination():
    return SEEDED_DESTINATION


@pytest.fixture
def weather_notes():
    return SEEDED_WEATHER_NOTES


@pytest.fixture
def transit_options():
    return SEEDED_TRANSIT_OPTIONS


@pytest.fixture
def mock_destination(database_url, destination, weather_notes, transit_options):
    """Register the three database reads the advisory flow performs.

    Returns a callable so tests can opt into a different destination reply --
    a 404, say -- while keeping the child-row mocks in place.
    """

    def register(row_id=1, status=200, payload=None):
        responses.add(
            responses.GET,
            "{}/api/destinations/{}".format(database_url, row_id),
            json=destination if payload is None else payload,
            status=status,
        )
        responses.add(
            responses.GET,
            database_url + "/api/weather-notes",
            json=weather_notes,
            status=200,
        )
        responses.add(
            responses.GET,
            database_url + "/api/transit-options",
            json=transit_options,
            status=200,
        )

    return register


@pytest.fixture
def mock_ollama(ollama_url):
    """Register a reply from the Ollama generate endpoint."""

    def register(completion="Pack layers. Carry your passport. Buy a rail pass.", **kwargs):
        # `body` is how a raised exception (e.g. a timeout) is registered, and
        # responses rejects being given both body and json.
        if "body" not in kwargs:
            kwargs.setdefault("json", {"response": completion})
        responses.add(responses.POST, ollama_url + "/api/generate", **kwargs)

    return register
