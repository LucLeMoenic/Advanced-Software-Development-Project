"""Offline retrieval checks for Student 5's travel logistics knowledge base (no model calls)."""

import re
from pathlib import Path

import pytest

import confidence
import retrieval

DOCUMENTS = {
    "airport-arrival": "Airport Arrival and Border Steps",
    "how-the-advisory-works": "How the Travel Advisory Works",
    "local-transit-types": "Local Transit Types",
    "official-sources": "Official Sources and Smartraveller",
    "passport-and-entry-documents": "Passport Validity and Entry Documents",
    "seasonal-packing": "Seasonal Weather and Packing",
    "travel-insurance-and-health": "Travel Insurance and Health Preparation",
    "visa-categories": "Visa Requirement Categories",
}

RELEVANT = [
    ("What is the difference between visa on arrival and an eVisa?", "visa-categories#3"),
    ("What are the Smartraveller advice levels?", "official-sources#2"),
    ("What should I pack for the wet season?", "seasonal-packing#3"),
    ("Is rideshare available everywhere?", "local-transit-types#4"),
    ("How do I get from the airport to the city?", "local-transit-types#6"),
    ("Can I bring my prescription medicines?", "airport-arrival#3"),
    ("Do I need an onward ticket?", "passport-and-entry-documents#3"),
    ("Are seasons reversed in Europe for Australians?", "seasonal-packing#1"),
    ("Which MCP tools does the service use?", "how-the-advisory-works#3"),
    ("What happens if Ollama is unavailable?", "how-the-advisory-works#2"),
]
INSUFFICIENT = [
    "What is the capital of France?",
    "Best restaurants in Tokyo?",
    "Who won the football world cup?",
    "How much does a hotel cost?",
]
# Destination-specific visa rules live in the database, not the knowledge base;
# generic overlap ("visa", "need") must never reach medium confidence.
DESTINATION_SPECIFIC = ["What visa do I need for Japan?"]


@pytest.fixture(scope="module")
def index():
    original = retrieval.KNOWLEDGE_ROOT
    retrieval.KNOWLEDGE_ROOT = Path(__file__).resolve().parents[1] / "knowledge"
    retrieval.reset_cache()
    yield retrieval.get_index("student-5")
    retrieval.KNOWLEDGE_ROOT = original
    retrieval.reset_cache()


def retained(index, question):
    return [(chunk, score) for chunk, score in index.top_k(question, 3) if score >= confidence.MIN_RELEVANCE]


def test_every_document_is_indexed_with_its_heading_as_source(index):
    stems = {chunk.chunk_id.split("#")[0] for chunk in index.chunks}
    assert stems == set(DOCUMENTS)
    for chunk in index.chunks:
        stem = chunk.chunk_id.split("#")[0]
        assert chunk.source == DOCUMENTS[stem]
        assert re.fullmatch(r"[a-zA-Z0-9_-]+#\d+", chunk.chunk_id)
        assert len(chunk.text) <= 2000
    for stem in DOCUMENTS:
        ids = [chunk.chunk_id for chunk in index.chunks if chunk.chunk_id.startswith(f"{stem}#")]
        assert ids == [f"{stem}#{n}" for n in range(1, len(ids) + 1)]


def test_review_metadata_and_disclaimer_are_never_retrievable(index):
    assert not any("Last reviewed" in chunk.text for chunk in index.chunks)
    for stem in DOCUMENTS:
        text = (retrieval.KNOWLEDGE_ROOT / "student-5" / f"{stem}.md").read_text(encoding="utf-8")
        assert "Last reviewed: 2026-09" in text and "not legal, migration or medical advice" in text


@pytest.mark.parametrize("question,expected", RELEVANT)
def test_relevant_questions_retrieve_the_expected_chunk(index, question, expected):
    kept = retained(index, question)
    print(question, [(chunk.chunk_id, round(score, 4)) for chunk, score in kept])
    assert kept[0][0].chunk_id == expected
    assert confidence.categorize(kept[0][1]) in {"medium", "high"}


@pytest.mark.parametrize("question", INSUFFICIENT)
def test_off_topic_questions_are_insufficient(index, question):
    assert retained(index, question) == []


@pytest.mark.parametrize("question", DESTINATION_SPECIFIC)
def test_destination_specific_questions_stay_below_medium(index, question):
    scores = [score for _, score in index.top_k(question, 3)]
    assert max(scores) < confidence.MEDIUM_RELEVANCE
