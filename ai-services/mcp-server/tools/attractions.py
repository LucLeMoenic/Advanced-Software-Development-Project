"""Student 3 (Local Experience & Attraction Recommender) MCP tools.

Read-only tools backed by the student-3 database service's ``/api/data/*``
endpoints (``http://localhost:5303`` from the host, overridable with
``STUDENT3_DATABASE_API_URL`` for CI or a different host layout).

Call shape: each tool takes ONE object parameter named ``params`` rather
than flat keyword arguments. Reason: this SDK's default keyword-argument
tool schema silently drops any field it doesn't recognise instead of
rejecting the call — verified by calling ``MCPServer.call_tool`` directly
with a bogus field and inspecting the result before writing this module.
Wrapping the arguments in one Pydantic model with ``extra="forbid"`` is
what actually produces a structured validation error for an unknown field,
which the Stage 1 brief requires. Example calls:

    attractions.search({"params": {"category": "restaurant", "limit": 5}})
    attractions.get_reviews({"params": {"attraction_id": 3}})
"""

import os
from typing import Any, Optional

import requests
from pydantic import BaseModel, ConfigDict

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

DATABASE_API_URL = os.environ.get("STUDENT3_DATABASE_API_URL", "http://localhost:5303")
REQUEST_TIMEOUT = 5

ALLOWED_CATEGORIES = {"sight", "restaurant", "activity"}
MAX_LIMIT = 10
DEFAULT_LIMIT = 5


class SearchParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Optional[str] = None
    min_rating: Optional[float] = None
    limit: int = DEFAULT_LIMIT


class GetReviewsParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attraction_id: int


def _fetch_attractions(category: Optional[str] = None) -> list[dict[str, Any]]:
    response = requests.get(
        f"{DATABASE_API_URL}/api/data/attractions",
        params={"category": category} if category else None,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _fetch_attraction(attraction_id: int) -> Optional[dict[str, Any]]:
    response = requests.get(
        f"{DATABASE_API_URL}/api/data/attractions/{attraction_id}", timeout=REQUEST_TIMEOUT
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def register(mcp: MCPServer) -> None:
    @mcp.tool(name="attractions.search")
    def search(params: SearchParams) -> dict[str, Any]:
        """Search Student 3 attractions by category and/or minimum rating."""
        if params.category is not None and params.category not in ALLOWED_CATEGORIES:
            raise ToolError(
                f"category must be one of {sorted(ALLOWED_CATEGORIES)}, got {params.category!r}."
            )
        if not 1 <= params.limit <= MAX_LIMIT:
            raise ToolError(f"limit must be between 1 and {MAX_LIMIT}, got {params.limit}.")

        try:
            attractions = _fetch_attractions(params.category)
        except requests.exceptions.RequestException as exc:
            raise ToolError(f"student-3 database unavailable: {exc}") from exc

        if params.min_rating is not None:
            attractions = [a for a in attractions if (a.get("rating") or 0) >= params.min_rating]

        # TODO(you): add a "total_matches" field to the returned dict, equal
        # to len(attractions) counted AFTER the category/min_rating filters
        # above but BEFORE the params.limit slice below. Keep "attractions"
        # sliced to params.limit exactly as it is now.
        return {"attractions": attractions[: params.limit]}

    @mcp.tool(name="attractions.get_reviews")
    def get_reviews(params: GetReviewsParams) -> dict[str, Any]:
        """Get one attraction's reviews by attraction id."""
        try:
            attraction = _fetch_attraction(params.attraction_id)
        except requests.exceptions.RequestException as exc:
            raise ToolError(f"student-3 database unavailable: {exc}") from exc

        if attraction is None:
            raise ToolError(f"attraction {params.attraction_id} not found.")

        return {
            "attraction_id": attraction["id"],
            "name": attraction["name"],
            "reviews": attraction.get("reviews", []),
        }
