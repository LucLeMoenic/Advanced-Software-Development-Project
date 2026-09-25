"""Tests the hand-rolled TF-IDF retrieval, using a throwaway knowledge base
in a tmp_path fixture rather than the real student-3 docs, so this suite
doesn't break every time someone edits the knowledge content.
"""

import retrieval

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
