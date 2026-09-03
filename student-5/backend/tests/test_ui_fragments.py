"""Tests for the server-rendered HTML fragments.

These assert on rendered markup rather than JSON, so they check three things:
the fragment carries the stored data, it is HTML the frontend can swap in, and
a write really did reach the database service before the refreshed table came
back.
"""

import json

import responses


def html_of(response):
    assert response.headers["Content-Type"].startswith("text/html")
    return response.get_data(as_text=True)


def sent_json(index):
    return json.loads(responses.calls[index].request.body)


# ---------------------------------------------------------------------------
# Read-only fragments
# ---------------------------------------------------------------------------


@responses.activate
def test_options_fragment_lists_destinations(client, database_url, destination):
    responses.add(
        responses.GET, database_url + "/api/destinations", json=[destination], status=200
    )

    response = client.get("/ui/destinations/options")

    body = html_of(response)
    assert response.status_code == 200
    assert '<option class="destination-option" value="1">Japan</option>' in body


@responses.activate
def test_weather_fragment_renders_seeded_notes_as_a_definition_list(
    client, database_url, weather_notes
):
    responses.add(
        responses.GET,
        database_url + "/api/weather-notes",
        json=weather_notes,
        status=200,
    )

    response = client.get("/ui/weather?destination_id=1")

    body = html_of(response)
    assert "<dl" in body
    assert "Spring (Mar-May)" in body
    assert "Mild days and heavy cherry blossom crowds." in body


@responses.activate
def test_weather_fragment_filters_by_destination(client, database_url, weather_notes):
    responses.add(
        responses.GET,
        database_url + "/api/weather-notes",
        json=weather_notes,
        status=200,
    )

    client.get("/ui/weather?destination_id=1")

    assert "destination_id=1" in responses.calls[0].request.url


@responses.activate
def test_visa_fragment_shows_the_stored_requirement(
    client, database_url, destination
):
    responses.add(
        responses.GET,
        database_url + "/api/destinations/1",
        json=destination,
        status=200,
    )

    response = client.get("/ui/visa?destination_id=1")

    body = html_of(response)
    assert 'class="visa-callout"' in body
    assert "visa-free" in body
    assert "Short-stay tourist entry for Australian passport holders." in body


@responses.activate
def test_transit_fragment_renders_a_table(client, database_url, transit_options):
    responses.add(
        responses.GET,
        database_url + "/api/transit-options",
        json=transit_options,
        status=200,
    )

    response = client.get("/ui/transit?destination_id=1")

    body = html_of(response)
    assert "<table" in body
    assert "rail" in body
    assert "A Japan Rail Pass covers most Shinkansen services." in body


@responses.activate
def test_fragments_ask_for_a_destination_instead_of_failing(client):
    """No destination_id yet is the normal first state of the page, not an error."""
    response = client.get("/ui/weather")

    assert response.status_code == 200
    assert "Choose a destination" in html_of(response)


@responses.activate
def test_manage_table_has_edit_and_delete_controls_per_row(
    client, database_url, destination
):
    responses.add(
        responses.GET, database_url + "/api/destinations", json=[destination], status=200
    )

    response = client.get("/ui/destinations/table")

    body = html_of(response)
    assert 'id="destinations-manage"' in body
    assert 'hx-post="/ui/destinations/1"' in body
    assert 'hx-post="/ui/destinations/1/delete"' in body
    # Writes must not point the browser at the JSON API.
    assert "/api/destinations" not in body


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


@responses.activate
def test_create_posts_to_the_database_then_returns_the_refreshed_table(
    client, database_url, destination
):
    created = {
        "id": 13,
        "country": "Portugal",
        "visa_requirement": "visa-free",
        "notes": "Schengen short-stay rules apply.",
    }
    responses.add(
        responses.POST, database_url + "/api/destinations", json=created, status=201
    )
    responses.add(
        responses.GET,
        database_url + "/api/destinations",
        json=[destination, created],
        status=200,
    )

    response = client.post(
        "/ui/destinations",
        data={
            "country": "Portugal",
            "visa_requirement": "visa-free",
            "notes": "Schengen short-stay rules apply.",
        },
    )

    body = html_of(response)
    assert response.status_code == 200
    assert sent_json(0) == {
        "country": "Portugal",
        "visa_requirement": "visa-free",
        "notes": "Schengen short-stay rules apply.",
    }
    # The table came from a fresh read, so the new row is in it.
    assert "Portugal" in body
    assert 'id="destinations-manage"' in body


@responses.activate
def test_create_omits_blank_notes_so_the_column_stays_null(client, database_url):
    responses.add(
        responses.POST, database_url + "/api/destinations", json={"id": 13}, status=201
    )
    responses.add(responses.GET, database_url + "/api/destinations", json=[], status=200)

    client.post(
        "/ui/destinations",
        data={"country": "Portugal", "visa_requirement": "visa-free", "notes": ""},
    )

    assert sent_json(0) == {"country": "Portugal", "visa_requirement": "visa-free"}


@responses.activate
def test_create_surfaces_the_database_validation_message(client, database_url):
    responses.add(
        responses.POST,
        database_url + "/api/destinations",
        json={"error": "Missing required field(s): country"},
        status=400,
    )
    responses.add(responses.GET, database_url + "/api/destinations", json=[], status=200)

    response = client.post("/ui/destinations", data={"visa_requirement": "eVisa"})

    body = html_of(response)
    assert response.status_code == 200
    assert "Missing required field(s): country" in body


@responses.activate
def test_row_edit_updates_then_returns_the_refreshed_table(client, database_url):
    updated = {
        "id": 1,
        "country": "Japan",
        "visa_requirement": "eVisa",
        "notes": "Rules changed.",
    }
    responses.add(
        responses.PUT, database_url + "/api/destinations/1", json=updated, status=200
    )
    responses.add(
        responses.GET, database_url + "/api/destinations", json=[updated], status=200
    )

    response = client.post(
        "/ui/destinations/1",
        data={
            "country": "Japan",
            "visa_requirement": "eVisa",
            "notes": "Rules changed.",
        },
    )

    body = html_of(response)
    assert sent_json(0) == {
        "country": "Japan",
        "visa_requirement": "eVisa",
        "notes": "Rules changed.",
    }
    assert 'value="eVisa"' in body


@responses.activate
def test_row_edit_clears_notes_with_null_not_an_empty_string(client, database_url):
    """Emptying the notes box has to clear the column, not fail validation.

    The database accepts null for destinations.notes but rejects "" for every
    field, so an emptied box must be sent as null.
    """
    cleared = {
        "id": 1,
        "country": "Japan",
        "visa_requirement": "visa-free",
        "notes": None,
    }
    responses.add(
        responses.PUT, database_url + "/api/destinations/1", json=cleared, status=200
    )
    responses.add(
        responses.GET, database_url + "/api/destinations", json=[cleared], status=200
    )

    client.post(
        "/ui/destinations/1",
        data={"country": "Japan", "visa_requirement": "visa-free", "notes": "  "},
    )

    assert sent_json(0)["notes"] is None


@responses.activate
def test_delete_removes_the_row_then_returns_the_refreshed_table(
    client, database_url, destination
):
    responses.add(responses.DELETE, database_url + "/api/destinations/1", status=204)
    responses.add(responses.GET, database_url + "/api/destinations", json=[], status=200)

    response = client.post("/ui/destinations/1/delete")

    body = html_of(response)
    assert response.status_code == 200
    assert responses.calls[0].request.method == "DELETE"
    assert destination["country"] not in body
    assert "No destinations are recorded yet." in body


# ---------------------------------------------------------------------------
# Advisory fragment
# ---------------------------------------------------------------------------


@responses.activate
def test_advisory_fragment_renders_an_article_with_the_model_in_the_footer(
    client, mock_destination, mock_ollama, model_tag
):
    mock_destination()
    mock_ollama(completion="Pack layers for cool evenings.")

    response = client.post(
        "/ui/advisory",
        data={"destination_id": "1", "month": "April", "interests": "food"},
    )

    body = html_of(response)
    assert '<article class="advisory-result">' in body
    assert "Pack layers for cool evenings." in body
    assert "<footer" in body
    assert model_tag in body


@responses.activate
def test_advisory_fragment_always_carries_the_verification_warning(
    client, mock_destination, mock_ollama
):
    """The warning cannot depend on the model remembering to write it."""
    mock_destination()
    mock_ollama(completion="Packing\n- A coat")

    response = client.post("/ui/advisory", data={"destination_id": "1"})

    assert "Smartraveller" in html_of(response)


@responses.activate
def test_advisory_fragment_renders_each_line_as_its_own_paragraph(
    client, mock_destination, mock_ollama
):
    """The model returns plain text; the fragment must not rely on frontend CSS."""
    mock_destination()
    mock_ollama(completion="Packing\n\n- A coat\n- Walking shoes")

    body = html_of(client.post("/ui/advisory", data={"destination_id": "1"}))

    assert body.count('<p class="advisory-line">') == 3


@responses.activate
def test_advisory_fragment_without_a_destination_prompts_instead_of_generating(client):
    response = client.post("/ui/advisory", data={})

    assert response.status_code == 200
    assert "Choose a destination" in html_of(response)
    assert len(responses.calls) == 0


# ---------------------------------------------------------------------------
# Dependency failures stay readable
#
# A fragment that answered 503 would not be swapped in by HTMX, so the page
# would simply not react. These return 200 with the problem as content.
# ---------------------------------------------------------------------------


@responses.activate
def test_fragment_renders_a_message_when_the_database_is_down(client):
    response = client.get("/ui/destinations/table")

    body = html_of(response)
    assert response.status_code == 200
    assert "travel database is unavailable" in body


@responses.activate
def test_advisory_fragment_renders_a_message_when_ollama_is_down(
    client, mock_destination
):
    mock_destination()  # only Ollama is missing

    response = client.post("/ui/advisory", data={"destination_id": "1"})

    body = html_of(response)
    assert response.status_code == 200
    assert "travel adviser is unavailable" in body
