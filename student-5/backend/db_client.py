"""Typed HTTP client for the Student 5 database microservice.

Marked requirement: the backend never opens the SQLite file. Every read and
write travels over HTTP to the database service, and this module is the only
part of the backend that knows how to speak to it.

Design note: these methods return a ``DatabaseResponse`` instead of raising on
4xx. The backend's job is to hand the database's own status code and body back
to its caller unchanged, so a "failure" like 404 is still a perfectly normal
return value here. The single exception is a transport failure -- if the
database service cannot be reached there is no status code to forward, so we
raise ``DatabaseUnavailable`` and let ``app.py`` translate that into a 503.
"""

from typing import Any, Dict, NamedTuple, Optional

import requests

# Long enough to ride out a container that is still warming up, short enough
# that a dead database service does not hang the backend's own workers.
DEFAULT_TIMEOUT_SECONDS = 5.0

DESTINATIONS_PATH = "/api/destinations"
WEATHER_NOTES_PATH = "/api/weather-notes"
TRANSIT_OPTIONS_PATH = "/api/transit-options"

JSONObject = Dict[str, Any]


class DatabaseUnavailable(Exception):
    """Raised when the database service cannot be reached at all.

    Covers connection refused, DNS failure and read timeouts -- anything where
    no HTTP response came back.
    """


class DatabaseResponse(NamedTuple):
    """One reply from the database service: status code plus decoded JSON.

    ``payload`` is ``None`` when the reply carries no JSON body, most notably
    the ``204 No Content`` returned by a successful DELETE.
    """

    status_code: int
    payload: Any


def _decode(response: requests.Response) -> Any:
    """Decode a JSON body, tolerating the empty/non-JSON replies (e.g. 204)."""
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return None


class DatabaseClient:
    """Thin wrapper over the database service's JSON API."""

    def __init__(
        self, base_url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # -- transport ----------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[JSONObject] = None,
        json_body: Any = None,
    ) -> DatabaseResponse:
        url = self.base_url + path
        try:
            response = requests.request(
                method,
                url,
                params=params,
                json=json_body,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise DatabaseUnavailable(f"{method} {url} failed: {exc}") from exc
        return DatabaseResponse(response.status_code, _decode(response))

    @staticmethod
    def _filter(destination_id: Optional[Any]) -> Optional[JSONObject]:
        """Build the ?destination_id= query string, or nothing if unfiltered."""
        if destination_id is None:
            return None
        return {"destination_id": destination_id}

    # -- generic CRUD, shared by all three resources -------------------------
    #
    # ``data`` is passed straight through to the database service. Because its
    # PUT uses partial-merge semantics, callers should send only the fields
    # they actually want to change; omitted fields keep their stored value.

    def _list(self, path: str, destination_id: Optional[Any]) -> DatabaseResponse:
        return self._request("GET", path, params=self._filter(destination_id))

    def _get(self, path: str, row_id: int) -> DatabaseResponse:
        return self._request("GET", "{}/{}".format(path, row_id))

    def _create(self, path: str, data: Any) -> DatabaseResponse:
        return self._request("POST", path, json_body=data)

    def _update(self, path: str, row_id: int, data: Any) -> DatabaseResponse:
        return self._request("PUT", "{}/{}".format(path, row_id), json_body=data)

    def _delete(self, path: str, row_id: int) -> DatabaseResponse:
        return self._request("DELETE", "{}/{}".format(path, row_id))

    # -- destinations --------------------------------------------------------
    #
    # The database ignores destination_id here (destinations are not filtered
    # by themselves); the parameter exists so all three resources share one
    # signature and the passthrough routes can stay generic.

    def list_destinations(
        self, destination_id: Optional[Any] = None
    ) -> DatabaseResponse:
        return self._list(DESTINATIONS_PATH, destination_id)

    def get_destination(self, row_id: int) -> DatabaseResponse:
        return self._get(DESTINATIONS_PATH, row_id)

    def create_destination(self, data: Any) -> DatabaseResponse:
        return self._create(DESTINATIONS_PATH, data)

    def update_destination(self, row_id: int, data: Any) -> DatabaseResponse:
        return self._update(DESTINATIONS_PATH, row_id, data)

    def delete_destination(self, row_id: int) -> DatabaseResponse:
        return self._delete(DESTINATIONS_PATH, row_id)

    # -- weather notes -------------------------------------------------------

    def list_weather_notes(
        self, destination_id: Optional[Any] = None
    ) -> DatabaseResponse:
        return self._list(WEATHER_NOTES_PATH, destination_id)

    def get_weather_note(self, row_id: int) -> DatabaseResponse:
        return self._get(WEATHER_NOTES_PATH, row_id)

    def create_weather_note(self, data: Any) -> DatabaseResponse:
        return self._create(WEATHER_NOTES_PATH, data)

    def update_weather_note(self, row_id: int, data: Any) -> DatabaseResponse:
        return self._update(WEATHER_NOTES_PATH, row_id, data)

    def delete_weather_note(self, row_id: int) -> DatabaseResponse:
        return self._delete(WEATHER_NOTES_PATH, row_id)

    # -- transit options -----------------------------------------------------

    def list_transit_options(
        self, destination_id: Optional[Any] = None
    ) -> DatabaseResponse:
        return self._list(TRANSIT_OPTIONS_PATH, destination_id)

    def get_transit_option(self, row_id: int) -> DatabaseResponse:
        return self._get(TRANSIT_OPTIONS_PATH, row_id)

    def create_transit_option(self, data: Any) -> DatabaseResponse:
        return self._create(TRANSIT_OPTIONS_PATH, data)

    def update_transit_option(self, row_id: int, data: Any) -> DatabaseResponse:
        return self._update(TRANSIT_OPTIONS_PATH, row_id, data)

    def delete_transit_option(self, row_id: int) -> DatabaseResponse:
        return self._delete(TRANSIT_OPTIONS_PATH, row_id)
