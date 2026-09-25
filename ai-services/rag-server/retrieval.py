"""Loads each feature's knowledge base and retrieves the closest chunks.

Retrieval is TF-IDF + cosine similarity, implemented with the standard
library only (no scikit-learn/numpy). Two reasons:

1. On this 8 GB host, embedding every query with a model (e.g.
   ``nomic-embed-text``) would compete for RAM with whichever
   implementer/reviewer pair the agentic loop already has loaded — plain
   TF-IDF needs no model load at all.
2. scikit-learn has no prebuilt wheel for Python 3.14 (this machine) and
   failed to compile from source here; pinning an older scikit-learn would
   risk the same gap on a grader's machine or a CI Python version we don't
   control. A ~50-line pure-Python TF-IDF avoids that whole dependency
   fragility.

This is an assumption pending group agreement on the RAG contract (see the
shared server READMEs) — a more capable embedding model can replace this
module later without changing the `/query` contract.
"""

import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

KNOWLEDGE_ROOT = Path(os.environ.get("RAG_KNOWLEDGE_ROOT", Path(__file__).parent / "knowledge"))

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Without stripping these, an unrelated question (e.g. "What is the capital
# of France?") scores close to 0.25 purely from sharing "what/is/the/of"
# with real chunks — too close to genuine topical matches (0.27-0.40 in this
# knowledge base) to leave room for a clean "insufficient" threshold. IDF
# already discounts common words, but not enough on a 33-chunk corpus this
# small, so an explicit stopword list is needed as well.
_STOPWORDS = frozenset(
    """
    a an and are as at be by can do does did for from had has have how i if
    in into is it its of on or so than that the their there these this to
    was we were what when where which who why will with you your
    """.split()
)


def _tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


@dataclass
class Chunk:
    source: str
    chunk_id: str
    text: str


class FeatureIndex:
    """A TF-IDF index over one feature's knowledge chunks."""

    def __init__(self, chunks: List[Chunk]):
        self.chunks = chunks
        self._doc_term_counts: List[Counter] = [Counter(_tokenize(c.text)) for c in chunks]
        self._idf: Dict[str, float] = {}
        if chunks:
            doc_count = len(chunks)
            df: Counter = Counter()
            for counts in self._doc_term_counts:
                df.update(counts.keys())
            self._idf = {
                term: math.log((1 + doc_count) / (1 + freq)) + 1.0 for term, freq in df.items()
            }
        self._doc_vectors = [self._tfidf_vector(counts) for counts in self._doc_term_counts]

    def _tfidf_vector(self, term_counts: Counter) -> Dict[str, float]:
        total_terms = sum(term_counts.values()) or 1
        return {
            term: (count / total_terms) * self._idf.get(term, 0.0)
            for term, count in term_counts.items()
        }

    @staticmethod
    def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        shared = a.keys() & b.keys()
        numerator = sum(a[t] * b[t] for t in shared)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return numerator / (norm_a * norm_b)

    def top_k(self, question: str, k: int = 3) -> List[Tuple[Chunk, float]]:
        """Return up to ``k`` (chunk, score) pairs, highest score first."""
        if not self.chunks:
            return []
        query_vector = self._tfidf_vector(Counter(_tokenize(question)))
        scored = [
            (chunk, self._cosine(query_vector, doc_vector))
            for chunk, doc_vector in zip(self.chunks, self._doc_vectors)
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]


def _chunk_markdown(path: Path) -> List[Chunk]:
    """Split a markdown file into paragraph chunks.

    The first ``# Heading`` becomes the citation source name; falls back to
    the filename if the file has no top-level heading.
    """
    text = path.read_text(encoding="utf-8")
    heading_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    source = heading_match.group(1).strip() if heading_match else path.stem

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    for i, paragraph in enumerate(paragraphs):
        if paragraph.startswith("#"):
            continue
        chunks.append(Chunk(source=source, chunk_id=f"{path.stem}#{i}", text=paragraph))
    return chunks


_indexes: Dict[str, FeatureIndex] = {}


def get_index(feature: str) -> FeatureIndex:
    """Load (and cache) the TF-IDF index for one feature's knowledge folder."""
    if feature in _indexes:
        return _indexes[feature]

    feature_dir = KNOWLEDGE_ROOT / feature
    chunks: List[Chunk] = []
    if feature_dir.is_dir():
        for md_path in sorted(feature_dir.glob("*.md")):
            chunks.extend(_chunk_markdown(md_path))

    index = FeatureIndex(chunks)
    _indexes[feature] = index
    return index


def reset_cache() -> None:
    """Drop cached indexes so a test or a knowledge-base edit is picked up."""
    _indexes.clear()
