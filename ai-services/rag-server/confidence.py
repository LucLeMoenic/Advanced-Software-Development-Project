"""Maps a retrieval score to the confidence category the RAG contract needs.

This is a judgment call, not a fact: TF-IDF cosine similarity on short
markdown paragraphs rarely gets close to 1.0 even for a strong match, so the
thresholds have to be picked by looking at real scores from the actual
knowledge base, not assumed from theory. Whoever sets this should be able to
defend the numbers in the demo Q&A (marking criterion 4 asks for a graded
confidence category, not just a yes/no).
"""

from typing import List, Optional

CONFIDENCE_LEVELS = ("high", "medium", "low", "insufficient")


def categorize(top_score: float, second_score: Optional[float] = None) -> str:
    """Return one of CONFIDENCE_LEVELS for a top TF-IDF cosine score.

    TODO(you): pick real thresholds. Suggested approach:
      1. Run a handful of real questions against `get_index("student-3")`
         once the knowledge docs exist (Stage 1) and print `top_k` scores.
      2. Note the score for a question the KB clearly answers well, one it
         answers so-so, and one it can't answer at all.
      3. Set the three cut points from those observed numbers, not guesses.

    Args:
        top_score: cosine similarity (0..1) of the best-matching chunk.
        second_score: cosine similarity of the second-best chunk, if any —
            useful if you want a big gap between #1 and #2 to count as
            *more* confident than two close, mediocre scores.

    Returns:
        "insufficient" must mean the RAG contract's insufficient-context
        response applies (empty citations, no answer text asserted as fact).
    """
    raise NotImplementedError(
        "Fill in real thresholds once Stage 1 knowledge docs exist — "
        "see the TODO above for how to pick them from actual scores."
    )
