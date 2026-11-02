"""Unit and integration tests for POST /api/documents/upload endpoint."""

import io
import pytest
import pymupdf as fitz
from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.services.chunking_service import TextChunk
from app.services.vector_store_service import VectorStoreService
from app.services.embedding_service import EmbeddingGenerationError
from app.services.ingestion_service import sanitize_filename

client = TestClient(app)


# ============================================================================
# Test Fixtures & Helpers
# ============================================================================

def create_sample_pdf_bytes(pages: list[str]) -> bytes:
    """Helper to generate valid in-memory PDF bytes with text per page."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        if text.strip():
            page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def mock_vector_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provides an isolated ChromaDB vector store backed by a temporary directory."""
    store = VectorStoreService(
        persist_directory=tmp_path / "test_chroma",
        collection_name="test_upload_collection"
    )
    monkeypatch.setattr("app.services.ingestion_service.default_vector_store", store)
    return store


@pytest.fixture
def mock_embedding_generator(monkeypatch: pytest.MonkeyPatch):
    """Mocks vector embedding generation to keep tests fast, deterministic, and offline."""
    def _mock_generate(chunks, model=None, model_name=None):
        # Return deterministic 384-dimensional unit vectors
        return [[0.05 * (i + 1)] * 384 for i in range(len(chunks))]

    monkeypatch.setattr("app.services.ingestion_service.generate_chunk_embeddings", _mock_generate)
    return _mock_generate


# ============================================================================
# Unit Tests: Filename Sanitization
# ============================================================================

def test_sanitize_filename():
    """Verify filename sanitization eliminates traversal, control chars, and bad extensions."""
    assert sanitize_filename("simple_notes.pdf") == "simple_notes.pdf"
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("..\\..\\Windows\\System32\\calc.pdf") == "calc.pdf"
    assert sanitize_filename("Lecture Notes (Biology #1)!.pdf") == "Lecture_Notes_Biology_1.pdf"
    assert sanitize_filename("   spaced  document  .pdf  ") == "spaced_document.pdf"
    assert sanitize_filename("no_extension") == "no_extension.pdf"
    assert sanitize_filename("") == "document.pdf"
    assert sanitize_filename(None) == "document.pdf"
    assert sanitize_filename("....pdf") == "document.pdf"


# ============================================================================
# API Integration Tests: Upload Endpoint
# ============================================================================

def test_upload_successful_two_page_pdf(mock_vector_store, mock_embedding_generator):
    """Verify successful upload of a two-page PDF with correct metadata and chunk indexing."""
    pdf_bytes = create_sample_pdf_bytes([
        "Introduction to Artificial Intelligence and RAG systems.",
        "Deep Neural Networks and ChromaDB persistent storage."
    ])

    files = {
        "file": ("ai_study_guide.pdf", io.BytesIO(pdf_bytes), "application/pdf")
    }

    response = client.post("/api/documents/upload", files=files)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["filename"] == "ai_study_guide.pdf"
    assert data["total_pages"] == 2
    assert data["total_chunks"] == 2
    assert data["embedding_model"] == settings.embedding_model_name
    assert "Successfully processed and indexed" in data["message"]

    # Verify vector store actually contains the indexed chunks
    assert mock_vector_store.count() == 2
    assert mock_vector_store.get_all_filenames() == ["ai_study_guide.pdf"]


def test_upload_invalid_file_extension(mock_vector_store, mock_embedding_generator):
    """Verify rejection of files with non-PDF extensions."""
    files = {
        "file": ("notes.txt", io.BytesIO(b"Just plain text"), "text/plain")
    }
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 400
    assert "Only PDF documents with a .pdf extension are accepted" in response.json()["detail"]


def test_upload_invalid_pdf_signature(mock_vector_store, mock_embedding_generator):
    """Verify rejection of files named .pdf but lacking the %PDF- magic signature."""
    fake_pdf = b"NOT_A_REAL_PDF_HEADER_CONTENT_12345"
    files = {
        "file": ("fake_document.pdf", io.BytesIO(fake_pdf), "application/pdf")
    }
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 400
    assert "valid PDF signature header (%PDF-)" in response.json()["detail"]



def test_upload_empty_file(mock_vector_store, mock_embedding_generator):
    """Verify rejection of empty (0-byte) file uploads."""
    files = {
        "file": ("empty.pdf", io.BytesIO(b""), "application/pdf")
    }
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 400
    assert "The uploaded file is empty" in response.json()["detail"]


def test_upload_oversized_file(mock_vector_store, mock_embedding_generator, monkeypatch: pytest.MonkeyPatch):
    """Verify rejection of files exceeding max allowed size with HTTP 413."""
    # Temporarily set max upload size to 1 MB for testing
    monkeypatch.setattr(settings, "max_upload_size_mb", 1)

    # Create 1.1 MB payload with valid PDF header
    oversized_data = b"%PDF-1.4\n" + b"A" * (1024 * 1024 + 100)
    files = {
        "file": ("large_book.pdf", io.BytesIO(oversized_data), "application/pdf")
    }
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 413
    assert "File exceeds maximum allowed size" in response.json()["detail"]


def test_upload_corrupted_pdf_structure(mock_vector_store, mock_embedding_generator):
    """Verify rejection of truncated or corrupted PDF structures."""
    # Starts with %PDF- header but contains unparseable junk
    corrupted_data = b"%PDF-1.4\nMalformed trailer << /Size 0 >> trailer %%EOF garbage"
    files = {
        "file": ("corrupt.pdf", io.BytesIO(corrupted_data), "application/pdf")
    }
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 400
    assert "Corrupted or invalid PDF structure" in response.json()["detail"]


def test_upload_scanned_image_pdf_no_text(mock_vector_store, mock_embedding_generator):
    """Verify rejection of PDFs containing pages but zero extractable text."""
    blank_pdf = create_sample_pdf_bytes(["", ""])
    files = {
        "file": ("scanned_document.pdf", io.BytesIO(blank_pdf), "application/pdf")
    }
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 400
    assert "contains no extractable text" in response.json()["detail"]


def test_upload_password_protected_pdf(mock_vector_store, mock_embedding_generator):
    """Verify rejection of password-protected/encrypted PDFs."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Classified study notes.")
    encrypted_bytes = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw="student_secret",
        owner_pw="master_secret"
    )
    doc.close()

    files = {
        "file": ("locked.pdf", io.BytesIO(encrypted_bytes), "application/pdf")
    }
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 400
    assert "password-protected" in response.json()["detail"]


def test_upload_embedding_failure_rolls_back_cleanly(mock_vector_store, monkeypatch: pytest.MonkeyPatch):
    """Verify that an embedding failure returns HTTP 500 without writing partial data to ChromaDB."""
    def _failing_embeddings(*args, **kwargs):
        raise EmbeddingGenerationError("Model GPU memory exhausted")

    monkeypatch.setattr("app.services.ingestion_service.generate_chunk_embeddings", _failing_embeddings)

    pdf_bytes = create_sample_pdf_bytes(["Sample text that will fail during embedding."])
    files = {
        "file": ("fail_embedding.pdf", io.BytesIO(pdf_bytes), "application/pdf")
    }
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 500
    assert "Failed to generate vector embeddings" in response.json()["detail"]

    # ChromaDB must remain empty
    assert mock_vector_store.count() == 0


def test_upload_chromadb_failure_handles_gracefully(mock_embedding_generator, monkeypatch: pytest.MonkeyPatch):
    """Verify that vector storage failure returns HTTP 500 without leaking stack traces or internal paths."""
    mock_store = MagicMock()
    mock_store.add_chunks.side_effect = RuntimeError("Disk I/O error writing parquet file")
    monkeypatch.setattr("app.services.ingestion_service.default_vector_store", mock_store)

    pdf_bytes = create_sample_pdf_bytes(["Valid text content."])
    files = {
        "file": ("store_failure.pdf", io.BytesIO(pdf_bytes), "application/pdf")
    }
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 500
    assert "Failed to index document chunks into vector database." in response.json()["detail"]


def test_upload_reupload_idempotency_and_replacement(mock_vector_store, mock_embedding_generator):
    """Verify that re-uploading a document replaces stale chunks atomically."""
    # First upload: 1 page
    pdf_v1 = create_sample_pdf_bytes(["Version 1 content."])
    res1 = client.post(
        "/api/documents/upload",
        files={"file": ("syllabus.pdf", io.BytesIO(pdf_v1), "application/pdf")}
    )
    assert res1.status_code == 200
    assert mock_vector_store.count() == 1
    assert mock_vector_store.get_all_filenames() == ["syllabus.pdf"]

    # Second upload: same filename, 2 pages
    pdf_v2 = create_sample_pdf_bytes([
        "Version 2 updated page 1.",
        "Version 2 updated page 2."
    ])
    res2 = client.post(
        "/api/documents/upload",
        files={"file": ("syllabus.pdf", io.BytesIO(pdf_v2), "application/pdf")}
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total_pages"] == 2
    assert data2["total_chunks"] == 2

    # Vector store count should reflect replacement (2 chunks total, not 1 + 2 = 3)
    assert mock_vector_store.count() == 2
    assert mock_vector_store.get_all_filenames() == ["syllabus.pdf"]


def test_failed_reupload_preserves_existing_document(mock_vector_store, mock_embedding_generator, monkeypatch: pytest.MonkeyPatch):
    """Verify that if a replacement upload fails, the original document chunks remain intact."""
    # Initial successful upload
    pdf_v1 = create_sample_pdf_bytes(["Original syllabus content that must survive."])
    res1 = client.post(
        "/api/documents/upload",
        files={"file": ("important_doc.pdf", io.BytesIO(pdf_v1), "application/pdf")}
    )
    assert res1.status_code == 200
    assert mock_vector_store.count() == 1

    # Attempt re-upload with a corrupt payload
    corrupt_pdf = b"%PDF-corrupt_content_12345"
    res2 = client.post(
        "/api/documents/upload",
        files={"file": ("important_doc.pdf", io.BytesIO(corrupt_pdf), "application/pdf")}
    )
    assert res2.status_code == 400

    # Original chunks must still exist in vector store!
    assert mock_vector_store.count() == 1
    assert mock_vector_store.get_all_filenames() == ["important_doc.pdf"]
