"""Builds the evidence the shared Multi-Agent Server is given.

The Multi-Agent Server never reads application data itself: this backend decides
exactly which catalogue facts the Planner, Worker and Reviewer may use. Each
evidence entry is one attraction (title = its exact name) plus its rating and up
to two review comments, within the server's size limits.
"""

MAX_EVIDENCE = 30  # the Multi-Agent Server accepts at most 30 entries
MAX_TITLE = 120
MAX_TEXT = 800
MAX_COMMENTS = 2
MAX_COMMENT_LENGTH = 160


def evidence_id(attraction_id):
    return f"attraction-{attraction_id}"


def _text(attraction, comments):
    parts = [f"{attraction['name']} is a {attraction['category']}."]
    if attraction.get("description"):
        parts.append(str(attraction["description"]).strip())
    rating = attraction.get("rating")
    parts.append(f"Rating: {rating if rating is not None else 'not rated'}.")
    for comment in comments[:MAX_COMMENTS]:
        parts.append(f"Review: {comment[:MAX_COMMENT_LENGTH]}")
    return " ".join(parts)[:MAX_TEXT]


def build_evidence(attractions, reviews):
    """Return Multi-Agent Server evidence entries, best-rated attractions first."""
    comments_by_attraction = {}
    for review in reviews:
        comment = (review.get("comment") or "").strip()
        if comment:
            comments_by_attraction.setdefault(review["attraction_id"], []).append(comment)

    ranked = sorted(attractions, key=lambda a: (-(a.get("rating") or 0), a["id"]))
    return [
        {
            "id": evidence_id(a["id"]),
            "title": a["name"].strip()[:MAX_TITLE],
            "text": _text(a, comments_by_attraction.get(a["id"], [])),
        }
        for a in ranked[:MAX_EVIDENCE]
        if a.get("name") and a["name"].strip()
    ]
