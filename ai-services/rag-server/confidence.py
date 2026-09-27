"""Maps a retrieval score to the confidence category the RAG contract needs.

This is a judgment call, not a fact: TF-IDF cosine similarity on short
markdown paragraphs rarely gets close to 1.0 even for a strong match, so the
thresholds have to be picked by looking at real scores from the actual
knowledge base, not assumed from theory. Whoever sets this should be able to
defend the numbers in the demo Q&A (marking criterion 4 asks for a graded
confidence category, not just a yes/no).
"""

import math
from typing import Optional

CONFIDENCE_LEVELS = ("high", "medium", "low", "insufficient")
MIN_RELEVANCE = 0.15
MEDIUM_RELEVANCE = 0.30
HIGH_RELEVANCE = 0.40


def categorize(top_score: float, second_score: Optional[float] = None) -> str:
    if not math.isfinite(top_score) or top_score < MIN_RELEVANCE:
        return "insufficient"
    if top_score >= HIGH_RELEVANCE:
        return "high"
    if top_score >= MEDIUM_RELEVANCE:
        return "medium"
    return "low"
