"""Unit and integration tests for Multi-Document Comparison API."""

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.comparison import ComparisonRequest, ComparisonResponse
from app.services.comparison_service import compare_study_documents
from app.services.vector_store_service import SearchResultItem

client = TestClient(app)


def test_compare_rejects_identical_documents():
    """Validates that a document cannot be compared with itself."""
    response = client.post(
        "/api/documents/compare",
        json={
            "doc_a": "notes_ch1.pdf",
            "doc_b": "notes_ch1.pdf",
            "comparison_focus": "Compare everything"
        }
    )
    assert response.status_code == 422
    data = response.json()
    assert "distinct" in str(data).lower() or "itself" in str(data).lower()


def test_compare_rejects_empty_filename():
    """Validates that empty filenames are rejected."""
    response = client.post(
        "/api/documents/compare",
        json={
            "doc_a": "   ",
            "doc_b": "notes_ch2.pdf"
        }
    )
    assert response.status_code == 422


def test_compare_missing_both_documents():
    """Verifies graceful handling when neither document exists in vector store."""
    mock_store = MagicMock()
    mock_store.search.return_value = []

    mock_emb = MagicMock()
    mock_emb.encode.return_value = [[0.1] * 384]

    payload = ComparisonRequest(doc_a="missing_a.pdf", doc_b="missing_b.pdf")
    res = compare_study_documents(
        payload=payload,
        vector_store=mock_store,
        embedding_model=mock_emb,
        api_key="mock_key"
    )

    assert res.has_sufficient_context is False
    assert "could not find indexed passages" in res.matrix_markdown.lower()
    assert len(res.citations_a) == 0
    assert len(res.citations_b) == 0


def test_compare_one_document_missing():
    """Verifies graceful handling when only one document has indexed passages."""
    mock_store = MagicMock()
    # First call (doc_a) returns chunk, second call (doc_b) returns empty
    mock_store.search.side_effect = [
        [SearchResultItem(chunk_id="1", text="Sample A text", filename="doc_a.pdf", page_number=1, chunk_index=0, distance=0.1)],
        []
    ]

    mock_emb = MagicMock()
    mock_emb.encode.return_value = [[0.1] * 384]

    payload = ComparisonRequest(doc_a="doc_a.pdf", doc_b="doc_b.pdf")
    res = compare_study_documents(
        payload=payload,
        vector_store=mock_store,
        embedding_model=mock_emb,
        api_key="mock_key"
    )

    assert res.has_sufficient_context is False
    assert "could not find indexed passages for 'doc_b.pdf'" in res.matrix_markdown.lower()


def test_compare_successful_matrix_synthesis():
    """Tests successful dual-retrieval and structured matrix output with partitioned citations."""
    mock_store = MagicMock()
    chunks_a = [
        SearchResultItem(chunk_id="a1", text="Machine learning relies on statistical models.", filename="lecture_a.pdf", page_number=2, chunk_index=0, distance=0.1),
        SearchResultItem(chunk_id="a2", text="Supervised learning needs labels.", filename="lecture_a.pdf", page_number=3, chunk_index=1, distance=0.12)
    ]
    chunks_b = [
        SearchResultItem(chunk_id="b1", text="Deep learning utilizes multilayer neural networks.", filename="textbook_b.pdf", page_number=14, chunk_index=0, distance=0.15)
    ]

    mock_store.search.side_effect = [chunks_a, chunks_b]

    mock_emb = MagicMock()
    mock_emb.encode.return_value = [[0.1] * 384]

    # Mock GenAI client
    mock_client = MagicMock()
    mock_gen_response = MagicMock()
    mock_gen_response.text = (
        "### 🎯 1. Core Objectives & Scope\n"
        "Lecture A covers foundational ML [lecture_a.pdf, Page 2], while Textbook B focuses on deep neural nets [textbook_b.pdf, Page 14].\n\n"
        "### ⚖️ 3. Key Differences & Discrepancies\n"
        "| Aspect | Lecture A | Textbook B |\n"
        "|---|---|---|\n"
        "| Architecture | Classical stats | Deep layers |"
    )
    mock_client.models.generate_content.return_value = mock_gen_response

    payload = ComparisonRequest(
        doc_a="lecture_a.pdf",
        doc_b="textbook_b.pdf",
        comparison_focus="Compare model architectures"
    )

    res = compare_study_documents(
        payload=payload,
        vector_store=mock_store,
        embedding_model=mock_emb,
        llm_client=mock_client,
        api_key="valid_test_key"
    )

    assert res.has_sufficient_context is True
    assert "Core Objectives" in res.matrix_markdown
    assert res.doc_a == "lecture_a.pdf"
    assert res.doc_b == "textbook_b.pdf"
    assert res.comparison_focus == "Compare model architectures"

    # Verify partitioned citations
    assert len(res.citations_a) == 2
    assert res.citations_a[0].filename == "lecture_a.pdf"
    assert res.citations_a[0].page_number == 2

    assert len(res.citations_b) == 1
    assert res.citations_b[0].filename == "textbook_b.pdf"
    assert res.citations_b[0].page_number == 14
