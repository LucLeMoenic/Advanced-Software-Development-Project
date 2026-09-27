"""Retrieval mechanics and explicit regressions against the real feature corpora."""

import retrieval
import confidence
import json
import pytest
from pathlib import Path

DOC_A = """# Sydney Sights

The Sydney Opera House is a sail-shaped performing arts venue on Sydney
Harbour, rated 4.7 stars.

Royal Botanic Gardens Victoria is a free garden on the Yarra River, rated
4.7 stars.
"""

DOC_B = """# Booking Notes

Chin Chin Melbourne is a busy restaurant that reviewers say needs a
booking in advance, especially on weekends.
"""


def _write_knowledge(tmp_path, feature="student-3"):
    feature_dir = tmp_path / feature
    feature_dir.mkdir()
    (feature_dir / "sights.md").write_text(DOC_A, encoding="utf-8")
    (feature_dir / "booking.md").write_text(DOC_B, encoding="utf-8")
    return tmp_path


def test_chunk_markdown_uses_heading_as_source(tmp_path, monkeypatch):
    monkeypatch.setattr(retrieval, "KNOWLEDGE_ROOT", _write_knowledge(tmp_path))
    retrieval.reset_cache()

    index = retrieval.get_index("student-3")

    assert len(index.chunks) == 3
    assert {c.source for c in index.chunks} == {"Sydney Sights", "Booking Notes"}


def test_top_k_ranks_the_relevant_chunk_first(tmp_path, monkeypatch):
    monkeypatch.setattr(retrieval, "KNOWLEDGE_ROOT", _write_knowledge(tmp_path))
    retrieval.reset_cache()
    index = retrieval.get_index("student-3")

    ranked = index.top_k("Do I need to book Chin Chin in advance?", k=1)

    assert ranked[0][0].source == "Booking Notes"


def test_stopword_only_overlap_scores_near_zero(tmp_path, monkeypatch):
    """Regression test: before stripping stopwords, a question sharing only
    words like "what/is/the" with the corpus scored ~0.25 here, uncomfortably
    close to genuine topical matches (0.27-0.40) and unusable for an
    insufficient-context threshold.
    """
    monkeypatch.setattr(retrieval, "KNOWLEDGE_ROOT", _write_knowledge(tmp_path))
    retrieval.reset_cache()
    index = retrieval.get_index("student-3")

    ranked = index.top_k("What is the capital of France?", k=1)

    assert ranked[0][1] < 0.05


def test_unknown_feature_returns_no_chunks(tmp_path, monkeypatch):
    monkeypatch.setattr(retrieval, "KNOWLEDGE_ROOT", _write_knowledge(tmp_path))
    retrieval.reset_cache()

    index = retrieval.get_index("student-99")

    assert index.top_k("anything", k=3) == []


def test_itinerary_knowledge_retrieval_scores(monkeypatch):
    monkeypatch.setattr(retrieval, "KNOWLEDGE_ROOT", Path(__file__).resolve().parents[1] / "knowledge")
    retrieval.reset_cache()
    index = retrieval.get_index("student-2")
    assert len(index.chunks) == 6
    fixtures = json.loads(Path(__file__).with_name("itinerary-questions.json").read_text())
    for fixture in fixtures:
        score = index.top_k(fixture["question"], 1)[0][1]
        print(f"{fixture['split']} relevant={fixture['relevant']} score={score:.4f}: {fixture['question']}")
        if fixture["relevant"]:
            assert score > 0
        assert (confidence.categorize(score) != "insufficient") == fixture["relevant"]


@pytest.mark.parametrize("case", json.loads(Path(__file__).with_name("grounding-questions.json").read_text()), ids=lambda case: case["id"])
def test_cross_feature_candidates_do_not_prove_answerability(monkeypatch, case):
    monkeypatch.setattr(retrieval, "KNOWLEDGE_ROOT", Path(__file__).resolve().parents[1] / "knowledge")
    retrieval.reset_cache()
    ranked = retrieval.get_index(case["feature"]).top_k(case["question"], 3)
    retained = {chunk.chunk_id for chunk, score in ranked if score >= confidence.MIN_RELEVANCE}
    assert case["candidate"] in retained
    print(json.dumps({"id": case["id"], "answerable": case["answerable"],
                      "ranked": [[chunk.chunk_id, round(score, 4)] for chunk, score in ranked]}))
