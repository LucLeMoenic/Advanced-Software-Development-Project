import os

import requests

DATABASE_API_URL = os.environ.get("DATABASE_API_URL", "http://student3-database:8080")
REQUEST_TIMEOUT = 5


class DatabaseUnavailableError(Exception):
    """The database service could not be reached (connection/timeout)."""


class DatabaseResponseError(Exception):
    """The database service responded, but not in the shape we expected."""


def _request(method, path, **kwargs):
    try:
        response = requests.request(
            method, f"{DATABASE_API_URL}{path}", timeout=REQUEST_TIMEOUT, **kwargs
        )
    except requests.exceptions.RequestException as exc:
        raise DatabaseUnavailableError(str(exc)) from exc
    return response


def list_attractions(category=None):
    params = {"category": category} if category else None
    response = _request("GET", "/api/data/attractions", params=params)
    if response.status_code != 200:
        raise DatabaseResponseError(f"unexpected status {response.status_code}")
    return response.json()


def get_attraction(attraction_id):
    response = _request("GET", f"/api/data/attractions/{attraction_id}")
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise DatabaseResponseError(f"unexpected status {response.status_code}")
    return response.json()


def create_attraction(payload):
    response = _request("POST", "/api/data/attractions", json=payload)
    if response.status_code == 400:
        return None, response.json()
    if response.status_code != 201:
        raise DatabaseResponseError(f"unexpected status {response.status_code}")
    return response.json(), None


def update_attraction(attraction_id, payload):
    response = _request("PUT", f"/api/data/attractions/{attraction_id}", json=payload)
    if response.status_code == 404:
        return None, "not_found"
    if response.status_code == 400:
        return None, response.json()
    if response.status_code != 200:
        raise DatabaseResponseError(f"unexpected status {response.status_code}")
    return response.json(), None


def delete_attraction(attraction_id):
    response = _request("DELETE", f"/api/data/attractions/{attraction_id}")
    if response.status_code == 404:
        return False
    if response.status_code != 204:
        raise DatabaseResponseError(f"unexpected status {response.status_code}")
    return True


def list_reviews(attraction_id=None):
    params = {"attraction_id": attraction_id} if attraction_id else None
    response = _request("GET", "/api/data/reviews", params=params)
    if response.status_code != 200:
        raise DatabaseResponseError(f"unexpected status {response.status_code}")
    return response.json()


def create_review(payload):
    response = _request("POST", "/api/data/reviews", json=payload)
    if response.status_code == 400:
        return None, response.json()
    if response.status_code != 201:
        raise DatabaseResponseError(f"unexpected status {response.status_code}")
    return response.json(), None
