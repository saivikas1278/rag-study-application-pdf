"""Integration tests for POST /api/query endpoint."""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.models.qa import Citation, GroundedAnswer
from app.models.search import SearchResponse, SearchResultChunk
from app.services.llm_service import (
    LLMConfigurationError,
    LLMRateLimitError,
    LLMModelUnavailableError,
    LLMServiceError,
)

client = TestClient(app)


# ============================================================================
# Helpers & Fixtures
# ============================================================================

def create_sample_chunk(
    chunk_id: str,
    text: str,
    filename: str = "sample.pdf",
    page_number: int = 1
) -> SearchResultChunk:
    """Helper to construct a SearchResultChunk instance."""
    return SearchResultChunk(
        chunk_id=chunk_id,
        text=text,
        filename=filename,
        page_number=page_number,
        chunk_index=0,
        distance=0.08
    )


# ============================================================================
# Query API Tests
# ============================================================================

def test_query_successful_grounded_answer(monkeypatch: pytest.MonkeyPatch):
    """Verify that a valid query retrieves context and returns a grounded answer with citations."""
    sample_chunk = create_sample_chunk(
        chunk_id="bio_c1",
        text="Mitochondria produce cellular ATP through oxidative phosphorylation.",
        filename="biology.pdf",
        page_number=1
    )

    # 1. Mock search retrieval
    mock_search = MagicMock(return_value=SearchResponse(
        query="What is the function of mitochondria?",
        total_results=1,
        results=[sample_chunk],
        message="Retrieved 1 passage."
    ))
    monkeypatch.setattr("app.services.query_service.search_documents", mock_search)

    # 2. Mock LLM service
    mock_llm = MagicMock(return_value=GroundedAnswer(
        answer="Mitochondria produce ATP through oxidative phosphorylation [biology.pdf, Page 1].",
        citations=[Citation(filename="biology.pdf", page_number=1)],
        model_used="gemini-2.5-flash",
        has_sufficient_context=True
    ))
    monkeypatch.setattr("app.services.query_service.generate_grounded_answer", mock_llm)

    payload = {
        "question": "What is the function of mitochondria?",
        "top_k": 3
    }
    response = client.post("/api/query", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["question"] == payload["question"]
    assert "Mitochondria produce ATP" in data["answer"]
    assert data["has_sufficient_context"] is True
    assert data["model_used"] == "gemini-2.5-flash"
    assert len(data["citations"]) == 1
    assert data["citations"][0]["filename"] == "biology.pdf"
    assert data["citations"][0]["page_number"] == 1

    # Verify search was called with top_k=3
    mock_search.assert_called_once_with(
        question=payload["question"],
        top_k=3,
        vector_store=None,
        embedding_model=None
    )


def test_query_insufficient_context_from_llm(monkeypatch: pytest.MonkeyPatch):
    """Verify response behavior when LLM determines retrieved passages are insufficient."""
    sample_chunk = create_sample_chunk(
        chunk_id="hist_c1",
        text="World War II ended in 1945.",
        filename="history.pdf",
        page_number=12
    )

    mock_search = MagicMock(return_value=SearchResponse(
        query="What is photosynthesis?",
        total_results=1,
        results=[sample_chunk],
        message="Retrieved 1 passage."
    ))
    monkeypatch.setattr("app.services.query_service.search_documents", mock_search)

    mock_llm = MagicMock(return_value=GroundedAnswer(
        answer="The uploaded documents do not contain sufficient information to answer this question.",
        citations=[],
        model_used="gemini-2.5-flash",
        has_sufficient_context=False
    ))
    monkeypatch.setattr("app.services.query_service.generate_grounded_answer", mock_llm)

    response = client.post("/api/query", json={"question": "What is photosynthesis?"})

    assert response.status_code == 200
    data = response.json()
    assert data["has_sufficient_context"] is False
    assert data["citations"] == []
    assert "do not contain sufficient information" in data["answer"]


def test_query_empty_retrieval_does_not_invoke_gemini(monkeypatch: pytest.MonkeyPatch):
    """Verify that if search returns 0 chunks, safe fallback is returned without calling Gemini."""
    mock_search = MagicMock(return_value=SearchResponse(
        query="Any question",
        total_results=0,
        results=[],
        message="No documents indexed."
    ))
    monkeypatch.setattr("app.services.query_service.search_documents", mock_search)

    mock_llm = MagicMock()
    monkeypatch.setattr("app.services.query_service.generate_grounded_answer", mock_llm)

    response = client.post("/api/query", json={"question": "Any question"})

    assert response.status_code == 200
    data = response.json()
    assert data["has_sufficient_context"] is False
    assert data["citations"] == []
    assert "do not contain sufficient information" in data["answer"]

    # Gemini must NOT be called
    mock_llm.assert_not_called()


def test_query_invalid_or_empty_question():
    """Verify validation guards on question field (non-empty, non-whitespace, max length)."""
    # Empty string
    res_empty = client.post("/api/query", json={"question": ""})
    assert res_empty.status_code == 422

    # Whitespace only
    res_ws = client.post("/api/query", json={"question": "   \n\t  "})
    assert res_ws.status_code == 422
    assert "whitespace only" in str(res_ws.json())

    # Missing question
    res_miss = client.post("/api/query", json={})
    assert res_miss.status_code == 422

    # Oversized question (> 1000 chars)
    res_long = client.post("/api/query", json={"question": "Q" * 1005})
    assert res_long.status_code == 422


def test_query_invalid_top_k():
    """Verify validation guards on top_k (between 1 and 20)."""
    res_low = client.post("/api/query", json={"question": "Valid query", "top_k": 0})
    assert res_low.status_code == 422

    res_neg = client.post("/api/query", json={"question": "Valid query", "top_k": -2})
    assert res_neg.status_code == 422

    res_high = client.post("/api/query", json={"question": "Valid query", "top_k": 21})
    assert res_high.status_code == 422


def test_query_missing_gemini_api_key(monkeypatch: pytest.MonkeyPatch):
    """Verify HTTP 500 when Gemini API key is missing or unconfigured."""
    sample_chunk = create_sample_chunk("c1", "Some content", "doc.pdf", 1)
    mock_search = MagicMock(return_value=SearchResponse(
        query="test", total_results=1, results=[sample_chunk], message="ok"
    ))
    monkeypatch.setattr("app.services.query_service.search_documents", mock_search)

    def _failing_llm(*args, **kwargs):
        raise LLMConfigurationError("Gemini API key is not configured.")

    monkeypatch.setattr("app.services.query_service.generate_grounded_answer", _failing_llm)

    response = client.post("/api/query", json={"question": "What is this?"})
    assert response.status_code == 500
    assert "Gemini API is not configured" in response.json()["detail"]


def test_query_rate_limit_error_handling(monkeypatch: pytest.MonkeyPatch):
    """Verify HTTP 429 is returned when Gemini returns a rate-limit error."""
    sample_chunk = create_sample_chunk("c1", "Some content", "doc.pdf", 1)
    mock_search = MagicMock(return_value=SearchResponse(
        query="test", total_results=1, results=[sample_chunk], message="ok"
    ))
    monkeypatch.setattr("app.services.query_service.search_documents", mock_search)

    def _rate_limited_llm(*args, **kwargs):
        raise LLMRateLimitError("429 Quota Exceeded")

    monkeypatch.setattr("app.services.query_service.generate_grounded_answer", _rate_limited_llm)

    response = client.post("/api/query", json={"question": "What is this?"})
    assert response.status_code == 429
    assert "rate limit or quota exceeded" in response.json()["detail"]


def test_query_unavailable_model_error_handling(monkeypatch: pytest.MonkeyPatch):
    """Verify HTTP 503 is returned when the configured Gemini model is unavailable."""
    sample_chunk = create_sample_chunk("c1", "Some content", "doc.pdf", 1)
    mock_search = MagicMock(return_value=SearchResponse(
        query="test", total_results=1, results=[sample_chunk], message="ok"
    ))
    monkeypatch.setattr("app.services.query_service.search_documents", mock_search)

    def _unavailable_model_llm(*args, **kwargs):
        raise LLMModelUnavailableError("Model not found")

    monkeypatch.setattr("app.services.query_service.generate_grounded_answer", _unavailable_model_llm)

    response = client.post("/api/query", json={"question": "What is this?"})
    assert response.status_code == 503
    assert "currently unavailable" in response.json()["detail"]


def test_query_retrieval_failure_handling(monkeypatch: pytest.MonkeyPatch):
    """Verify HTTP 500 when the underlying semantic retrieval service fails."""
    def _failing_search(*args, **kwargs):
        raise HTTPException(status_code=500, detail="Failed to query vector database.")

    monkeypatch.setattr("app.services.query_service.search_documents", _failing_search)

    response = client.post("/api/query", json={"question": "Any question"})
    assert response.status_code == 500
    assert "Failed to query vector database" in response.json()["detail"]


def test_query_citation_verification_discards_hallucinated_sources(monkeypatch: pytest.MonkeyPatch):
    """Verify that citations returned by the LLM are strictly filtered to retrieved source metadata."""
    real_chunk = create_sample_chunk("c1", "Photosynthesis text", "botany.pdf", 4)

    mock_search = MagicMock(return_value=SearchResponse(
        query="test", total_results=1, results=[real_chunk], message="ok"
    ))
    monkeypatch.setattr("app.services.query_service.search_documents", mock_search)

    # LLM hallucinates a citation to 'fake_source.pdf' page 99 alongside the real citation
    mock_llm = MagicMock(return_value=GroundedAnswer(
        answer="Photosynthesis occurs in chloroplasts [botany.pdf, Page 4] and [fake_source.pdf, Page 99].",
        citations=[
            Citation(filename="botany.pdf", page_number=4),
            Citation(filename="fake_source.pdf", page_number=99)
        ],
        model_used="gemini-2.5-flash",
        has_sufficient_context=True
    ))
    monkeypatch.setattr("app.services.query_service.generate_grounded_answer", mock_llm)

    response = client.post("/api/query", json={"question": "Where does photosynthesis occur?"})
    assert response.status_code == 200
    data = response.json()

    # The verified citations list must ONLY include botany.pdf:4
    assert len(data["citations"]) == 1
    assert data["citations"][0]["filename"] == "botany.pdf"
    assert data["citations"][0]["page_number"] == 4


def test_existing_endpoints_remain_functional():
    """Regression test verifying that root, health, upload, and search routes are operational."""
    # Root
    res_root = client.get("/")
    assert res_root.status_code == 200

    # Health
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"


def test_query_high_demand_error_handling(monkeypatch: pytest.MonkeyPatch):
    """Verify HTTP 503 with clear high-demand message is returned when model is overloaded."""
    sample_chunk = create_sample_chunk("c1", "Some content", "doc.pdf", 1)
    mock_search = MagicMock(return_value=SearchResponse(
        query="what are his strengths and weakness", total_results=1, results=[sample_chunk], message="ok"
    ))
    monkeypatch.setattr("app.services.query_service.search_documents", mock_search)

    def _high_demand_llm(*args, **kwargs):
        raise LLMModelUnavailableError(
            "Gemini model 'gemini-2.5-flash' is currently experiencing high demand. Please try again shortly."
        )

    monkeypatch.setattr("app.services.query_service.generate_grounded_answer", _high_demand_llm)

    response = client.post("/api/query", json={"question": "what are his strengths and weakness"})
    assert response.status_code == 503
    data = response.json()
    assert "currently experiencing high demand" in data["detail"]
    assert "Please try again shortly" in data["detail"]

