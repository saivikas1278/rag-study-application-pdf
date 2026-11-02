"""Unit and integration tests for POST /api/search endpoint."""

import io
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.chunking_service import TextChunk
from app.services.vector_store_service import VectorStoreService
from app.services.embedding_service import EmbeddingGenerationError
from app.models.search import SearchRequest, SearchResponse

client = TestClient(app)


# ============================================================================
# Helpers & Fixtures
# ============================================================================

def create_sample_chunk(
    chunk_id: str,
    text: str,
    filename: str = "deep_learning.pdf",
    page_number: int = 1,
    chunk_index: int = 0
) -> TextChunk:
    """Helper to construct a valid TextChunk instance."""
    return TextChunk(
        chunk_id=chunk_id,
        chunk_index=chunk_index,
        filename=filename,
        page_number=page_number,
        text=text,
        char_count=len(text)
    )


@pytest.fixture
def populated_vector_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provides an isolated ChromaDB vector store pre-populated with synthetic chunks."""
    store = VectorStoreService(
        persist_directory=tmp_path / "test_search_chroma",
        collection_name="test_search_col"
    )

    chunk_ai = create_sample_chunk(
        chunk_id="dl_p3_c0",
        text="Gradient descent iteratively minimizes loss functions across training epochs.",
        filename="neural_networks.pdf",
        page_number=3,
        chunk_index=0
    )
    chunk_bio = create_sample_chunk(
        chunk_id="bio_p1_c0",
        text="Mitochondria are the powerhouses of eukaryotic cells generating ATP.",
        filename="cell_biology.pdf",
        page_number=1,
        chunk_index=0
    )

    # Orthogonal 384-dimensional synthetic embeddings
    vec_ai = [1.0] + [0.0] * 383
    vec_bio = [0.0, 1.0] + [0.0] * 382

    store.add_chunks([chunk_ai, chunk_bio], [vec_ai, vec_bio])

    monkeypatch.setattr("app.services.search_service.default_vector_store", store)
    return store


@pytest.fixture
def mock_query_embedding_generator(monkeypatch: pytest.MonkeyPatch):
    """Mocks query vectorization for fast, deterministic search tests."""
    def _mock_query_embed(query: str, model=None, model_name=None):
        # If query mentions neural or gradient, align with AI vector
        if any(term in query.lower() for term in ["neural", "gradient", "loss", "ai"]):
            return [0.95] + [0.0] * 383
        # If query mentions biology or cell, align with Bio vector
        elif any(term in query.lower() for term in ["cell", "mitochondria", "bio"]):
            return [0.0, 0.95] + [0.0] * 382
        # Default unit vector
        return [0.5, 0.5] + [0.0] * 382

    monkeypatch.setattr("app.services.search_service.generate_query_embedding", _mock_query_embed)
    return _mock_query_embed


# ============================================================================
# Search API Tests
# ============================================================================

def test_search_retrieves_relevant_chunk_with_metadata(
    populated_vector_store,
    mock_query_embedding_generator
):
    """Verify that a valid question retrieves the semantically matching chunk with full metadata."""
    payload = {
        "question": "How does gradient descent optimize neural network parameters?",
        "top_k": 2
    }

    response = client.post("/api/search", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["query"] == payload["question"]
    assert data["total_results"] == 2
    assert len(data["results"]) == 2
    assert "Retrieved 2 relevant passage(s)" in data["message"]

    # The closest result must be the AI chunk
    top_chunk = data["results"][0]
    assert top_chunk["chunk_id"] == "dl_p3_c0"
    assert top_chunk["filename"] == "neural_networks.pdf"
    assert top_chunk["page_number"] == 3
    assert top_chunk["chunk_index"] == 0
    assert "Gradient descent" in top_chunk["text"]
    assert top_chunk["distance"] < 0.1  # Highly similar (cosine distance near 0)


def test_search_preserves_source_filename_and_page_number(
    populated_vector_store,
    mock_query_embedding_generator
):
    """Verify source filename and 1-based page number are preserved without modification."""
    response = client.post(
        "/api/search",
        json={"question": "What is the function of mitochondria in eukaryotic cells?"}
    )

    assert response.status_code == 200
    data = response.json()

    top_chunk = data["results"][0]
    assert top_chunk["filename"] == "cell_biology.pdf"
    assert top_chunk["page_number"] == 1
    assert "Mitochondria" in top_chunk["text"]


def test_search_custom_top_k(populated_vector_store, mock_query_embedding_generator):
    """Verify that top_k restricts the number of returned chunks."""
    response = client.post(
        "/api/search",
        json={"question": "general question", "top_k": 1}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 1
    assert len(data["results"]) == 1


def test_search_rejects_invalid_top_k():
    """Verify validation boundaries for top_k (ge=1, le=20)."""
    # top_k < 1
    res_zero = client.post("/api/search", json={"question": "test", "top_k": 0})
    assert res_zero.status_code == 422

    res_neg = client.post("/api/search", json={"question": "test", "top_k": -5})
    assert res_neg.status_code == 422

    # top_k > 20
    res_high = client.post("/api/search", json={"question": "test", "top_k": 21})
    assert res_high.status_code == 422


def test_search_rejects_empty_or_whitespace_question():
    """Verify that empty, blank, or whitespace-only questions trigger HTTP 422."""
    # Empty string
    res_empty = client.post("/api/search", json={"question": ""})
    assert res_empty.status_code == 422

    # Whitespace only
    res_whitespace = client.post("/api/search", json={"question": "     \n\t  "})
    assert res_whitespace.status_code == 422
    assert "whitespace only" in str(res_whitespace.json())

    # Missing question field
    res_missing = client.post("/api/search", json={})
    assert res_missing.status_code == 422


def test_search_rejects_oversized_question():
    """Verify that questions exceeding 1000 characters trigger HTTP 422."""
    long_question = "Explain " + "x" * 1005
    res = client.post("/api/search", json={"question": long_question})
    assert res.status_code == 422


def test_search_empty_vector_store_behavior(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify searching an empty vector store returns 0 results with an informative message."""
    empty_store = VectorStoreService(
        persist_directory=tmp_path / "empty_store",
        collection_name="empty_search_col"
    )
    monkeypatch.setattr("app.services.search_service.default_vector_store", empty_store)

    response = client.post("/api/search", json={"question": "What is machine learning?"})

    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 0
    assert data["results"] == []
    assert "No documents are currently indexed" in data["message"]


def test_search_embedding_failure_returns_500(
    populated_vector_store,
    monkeypatch: pytest.MonkeyPatch
):
    """Verify that failure during query embedding returns HTTP 500 without leaking stack traces."""
    def _failing_query_embed(*args, **kwargs):
        raise EmbeddingGenerationError("SentenceTransformer out of memory")

    monkeypatch.setattr("app.services.search_service.generate_query_embedding", _failing_query_embed)

    response = client.post("/api/search", json={"question": "Test failure"})
    assert response.status_code == 500
    assert "Failed to generate query vector embedding" in response.json()["detail"]


def test_search_chromadb_failure_returns_500(
    mock_query_embedding_generator,
    monkeypatch: pytest.MonkeyPatch
):
    """Verify that database query failure returns HTTP 500 safely."""
    mock_store = MagicMock()
    mock_store.count.return_value = 5  # Has documents
    mock_store.search.side_effect = RuntimeError("ChromaDB index file corrupted")
    monkeypatch.setattr("app.services.search_service.default_vector_store", mock_store)

    response = client.post("/api/search", json={"question": "Test database failure"})
    assert response.status_code == 500
    assert "Failed to query vector database." in response.json()["detail"]


def test_existing_endpoints_remain_functional():
    """Regression test verifying that root and health check endpoints remain healthy."""
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "AI PDF Study Assistant API is running" in res_root.json()["message"]

    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"
