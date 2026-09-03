"""Tests for the AI advisory endpoint.

Both dependencies are mocked with `responses`, so the whole suite still runs
with no network and no model anywhere near it. The interesting assertions are
not on the returned text -- a mocked model returns whatever we told it to --
but on the *prompt this service builds*, which is the part the service is
actually responsible for.
"""

import json

import pytest
import requests
import responses

ADVISORY_PATH = "/api/advisory"
GENERATE_PATH = "/api/generate"


def ollama_request():
    """The request body this service sent to Ollama."""
    for call in responses.calls:
        if call.request.url.endswith(GENERATE_PATH):
            return json.loads(call.request.body)
    raise AssertionError("the service never called Ollama")


def prompt_sent():
    return ollama_request()["prompt"]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@responses.activate
def test_advisory_returns_text_model_and_destination(
    client, mock_destination, mock_ollama, model_tag, destination
):
    mock_destination()
    mock_ollama(completion="Pack breathable layers and a compact umbrella.")

    response = client.post(ADVISORY_PATH, json={"destination_id": 1})

    assert response.status_code == 200
    body = response.get_json()
    assert body["advisory"] == "Pack breathable layers and a compact umbrella."
    assert body["model"] == model_tag
    assert body["destination"] == destination


@responses.activate
def test_prompt_is_grounded_in_the_stored_rows(
    client, mock_destination, mock_ollama, destination, weather_notes, transit_options
):
    """The proof that the advisory is grounded rather than recalled.

    Every fact the model is allowed to use has to appear in the prompt, so the
    country, the stored visa requirement, a stored weather note and a stored
    transit detail must all be in there verbatim.
    """
    mock_destination()
    mock_ollama()

    client.post(ADVISORY_PATH, json={"destination_id": 1})

    prompt = prompt_sent()
    assert destination["country"] in prompt
    assert destination["visa_requirement"] in prompt
    assert weather_notes[0]["notes"] in prompt
    assert transit_options[0]["details"] in prompt


@responses.activate
def test_prompt_carries_the_travellers_month_and_interests(
    client, mock_destination, mock_ollama
):
    mock_destination()
    mock_ollama()

    client.post(
        ADVISORY_PATH,
        json={"destination_id": 1, "month": "April", "interests": "food and hiking"},
    )

    prompt = prompt_sent()
    assert "April" in prompt
    assert "food and hiking" in prompt


@responses.activate
def test_month_and_interests_are_optional(client, mock_destination, mock_ollama):
    mock_destination()
    mock_ollama()

    response = client.post(ADVISORY_PATH, json={"destination_id": 1})

    assert response.status_code == 200


@responses.activate
def test_prompt_states_when_a_destination_has_no_child_rows(
    client, database_url, mock_ollama
):
    """Seeded Fiji has no weather notes or transit options.

    The gap has to be stated rather than left blank, or the model fills the
    silence with plausible invented services.
    """
    fiji = {
        "id": 12,
        "country": "Fiji",
        "visa_requirement": "visa-free",
        "notes": "Visitor permit granted on arrival for short stays.",
    }
    responses.add(
        responses.GET, database_url + "/api/destinations/12", json=fiji, status=200
    )
    responses.add(responses.GET, database_url + "/api/weather-notes", json=[], status=200)
    responses.add(
        responses.GET, database_url + "/api/transit-options", json=[], status=200
    )
    mock_ollama()

    response = client.post(ADVISORY_PATH, json={"destination_id": 12})

    assert response.status_code == 200
    prompt = prompt_sent()
    assert "No weather notes are recorded" in prompt
    assert "No transit options are recorded" in prompt


@responses.activate
def test_prompt_forbids_facts_that_are_not_recorded(
    client, mock_destination, mock_ollama
):
    """Grounding is only as good as the instruction that enforces it."""
    mock_destination()
    mock_ollama()

    client.post(ADVISORY_PATH, json={"destination_id": 1})

    assert "Use only the recorded information below" in prompt_sent()


@responses.activate
def test_model_tag_comes_from_configuration(
    client, mock_destination, mock_ollama, model_tag
):
    """No model name is hardcoded: the configured tag is what gets requested."""
    mock_destination()
    mock_ollama()

    client.post(ADVISORY_PATH, json={"destination_id": 1})

    assert ollama_request()["model"] == model_tag


@responses.activate
def test_generation_is_not_streamed(client, mock_destination, mock_ollama):
    mock_destination()
    mock_ollama()

    client.post(ADVISORY_PATH, json={"destination_id": 1})

    assert ollama_request()["stream"] is False


# ---------------------------------------------------------------------------
# Bad requests
# ---------------------------------------------------------------------------


@responses.activate
def test_unknown_destination_returns_404(client, mock_destination, mock_ollama):
    mock_destination(row_id=999, status=404, payload={"error": "No rows with id 999"})
    mock_ollama()

    response = client.post(ADVISORY_PATH, json={"destination_id": 999})

    assert response.status_code == 404
    assert response.get_json() == {"error": "No rows with id 999"}


@responses.activate
def test_unknown_destination_never_reaches_the_model(
    client, mock_destination, mock_ollama
):
    """A missing destination means no grounding data, so nothing is generated."""
    mock_destination(row_id=999, status=404, payload={"error": "No rows with id 999"})
    mock_ollama()

    client.post(ADVISORY_PATH, json={"destination_id": 999})

    assert all(not call.request.url.endswith(GENERATE_PATH) for call in responses.calls)


@responses.activate
@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="missing"),
        pytest.param({"destination_id": None}, id="null"),
        pytest.param({"destination_id": "kyoto"}, id="not-a-number"),
        pytest.param({"destination_id": "1/../weather-notes/1"}, id="path-injection"),
    ],
)
def test_destination_id_must_be_an_integer(client, body):
    response = client.post(ADVISORY_PATH, json=body)

    assert response.status_code == 400
    assert "error" in response.get_json()
    # Nothing was reached: a bad id must not become part of a database URL.
    assert len(responses.calls) == 0


# ---------------------------------------------------------------------------
# Dependency failures -- two 503s, told apart by their message
# ---------------------------------------------------------------------------


@responses.activate
def test_database_down_returns_the_database_503(client):
    # Nothing registered, so `responses` raises a ConnectionError.
    response = client.post(ADVISORY_PATH, json={"destination_id": 1})

    assert response.status_code == 503
    assert response.get_json() == {"error": "database service unavailable"}


@responses.activate
def test_ollama_unreachable_returns_the_ai_503(client, mock_destination):
    mock_destination()  # the database is fine; only Ollama is missing

    response = client.post(ADVISORY_PATH, json={"destination_id": 1})

    assert response.status_code == 503
    assert response.get_json() == {"error": "ai service unavailable"}


@responses.activate
def test_ollama_error_status_returns_the_ai_503(
    client, mock_destination, mock_ollama
):
    mock_destination()
    mock_ollama(json={"error": "model not found"}, status=500)

    response = client.post(ADVISORY_PATH, json={"destination_id": 1})

    assert response.status_code == 503
    assert response.get_json() == {"error": "ai service unavailable"}


@responses.activate
def test_ollama_timeout_returns_the_ai_503(client, mock_destination, mock_ollama):
    mock_destination()
    mock_ollama(body=requests.exceptions.ReadTimeout("timed out"))

    response = client.post(ADVISORY_PATH, json={"destination_id": 1})

    assert response.status_code == 503
    assert response.get_json() == {"error": "ai service unavailable"}


@responses.activate
def test_ollama_reply_without_completion_text_returns_the_ai_503(
    client, mock_destination, mock_ollama
):
    mock_destination()
    mock_ollama(json={"done": True}, status=200)

    response = client.post(ADVISORY_PATH, json={"destination_id": 1})

    assert response.status_code == 503
    assert response.get_json() == {"error": "ai service unavailable"}
