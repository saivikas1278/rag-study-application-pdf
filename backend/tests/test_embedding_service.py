"""Unit tests for the local text embedding service."""

import pytest
import numpy as np
from unittest.mock import MagicMock
from app.services.chunking_service import TextChunk
from app.services.embedding_service import (
    generate_chunk_embeddings,
    generate_query_embedding,
    get_embedding_model,
    EmbeddingGenerationError,
    EXPECTED_EMBEDDING_DIM,
)



def create_mock_chunk(chunk_id: str, text: str, page: int = 1) -> TextChunk:
    """Helper to create a valid TextChunk object."""
    return TextChunk(
        chunk_id=chunk_id,
        chunk_index=0,
        filename="test_notes.pdf",
        page_number=page,
        text=text,
        char_count=len(text)
    )


def test_empty_chunks_list_returns_empty():
    """Verify that an empty list of chunks returns an empty list without error."""
    result = generate_chunk_embeddings([])
    assert result == []


def test_invalid_chunk_type_raises_value_error():
    """Verify that passing non-TextChunk objects raises a ValueError."""
    invalid_chunks = ["This is just a string, not a TextChunk"]
    with pytest.raises(ValueError, match="expected TextChunk instance"):
        generate_chunk_embeddings(invalid_chunks)  # type: ignore


def test_empty_or_whitespace_chunk_text_raises_value_error():
    """Verify that chunks with empty or whitespace-only text raise a ValueError."""
    blank_chunk = create_mock_chunk("chunk_blank", "   \n  \t")
    with pytest.raises(ValueError, match="empty or whitespace-only text"):
        generate_chunk_embeddings([blank_chunk])


def test_mocked_model_preserves_order_and_dimensionality():
    """Verify that embeddings match chunk count, expected dimension, and exact order."""
    chunks = [
        create_mock_chunk("c1", "First chunk about neural networks."),
        create_mock_chunk("c2", "Second chunk about vector indexing."),
        create_mock_chunk("c3", "Third chunk about retrieval augmented generation."),
    ]

    # Create mock model returning 384-dim vectors with distinctive first values
    mock_model = MagicMock()
    mock_vectors = np.zeros((3, EXPECTED_EMBEDDING_DIM), dtype=np.float32)
    mock_vectors[0, 0] = 10.0
    mock_vectors[1, 0] = 20.0
    mock_vectors[2, 0] = 30.0

    mock_model.encode.return_value = mock_vectors

    embeddings = generate_chunk_embeddings(chunks, model=mock_model)

    # 1. Chunk count and dimensionality
    assert len(embeddings) == 3
    assert len(embeddings[0]) == EXPECTED_EMBEDDING_DIM
    assert len(embeddings[1]) == EXPECTED_EMBEDDING_DIM
    assert len(embeddings[2]) == EXPECTED_EMBEDDING_DIM

    # 2. Strict order preservation
    assert embeddings[0][0] == 10.0
    assert embeddings[1][0] == 20.0
    assert embeddings[2][0] == 30.0

    # 3. Model called with correct text list
    mock_model.encode.assert_called_once_with(
        [c.text for c in chunks],
        show_progress_bar=False,
        convert_to_numpy=True
    )


def test_non_finite_values_raise_embedding_error():
    """Verify that NaN or Infinity in model outputs raises EmbeddingGenerationError."""
    chunks = [create_mock_chunk("c1", "Valid text content.")]

    mock_model = MagicMock()
    invalid_vectors = np.zeros((1, EXPECTED_EMBEDDING_DIM), dtype=np.float32)
    invalid_vectors[0, 5] = np.nan  # Inject NaN
    mock_model.encode.return_value = invalid_vectors

    with pytest.raises(EmbeddingGenerationError, match="contain non-finite values"):
        generate_chunk_embeddings(chunks, model=mock_model)


def test_real_model_smoke_test():
    """Real-model smoke test verifying live SentenceTransformers inference."""
    chunks = [
        create_mock_chunk("real_c1", "Artificial intelligence and neural language modeling."),
        create_mock_chunk("real_c2", "Photosynthesis is the biological process used by plants.")
    ]

    # Runs inference on all-MiniLM-L6-v2
    embeddings = generate_chunk_embeddings(chunks)

    assert len(embeddings) == 2
    assert len(embeddings[0]) == EXPECTED_EMBEDDING_DIM
    assert len(embeddings[1]) == EXPECTED_EMBEDDING_DIM

    # Ensure all values are finite Python floats
    assert all(isinstance(val, float) for val in embeddings[0])
    assert all(isinstance(val, float) for val in embeddings[1])

    # Semantically distinct sentences should produce different vectors
    vec1 = np.array(embeddings[0])
    vec2 = np.array(embeddings[1])
    cosine_sim = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    assert cosine_sim < 0.95, f"Expected distinct vectors, got cosine similarity {cosine_sim}"


def test_generate_query_embedding_with_mock():
    """Verify that generate_query_embedding correctly encodes and validates single query."""
    mock_model = MagicMock()
    mock_vector = np.full((1, EXPECTED_EMBEDDING_DIM), 0.42, dtype=np.float32)
    mock_model.encode.return_value = mock_vector

    result = generate_query_embedding("What is RAG?", model=mock_model)

    assert len(result) == EXPECTED_EMBEDDING_DIM
    assert isinstance(result[0], float)
    assert result[0] == pytest.approx(0.42, abs=1e-5)
    mock_model.encode.assert_called_once_with(
        ["What is RAG?"],
        show_progress_bar=False,
        convert_to_numpy=True
    )


def test_generate_query_embedding_rejects_empty():
    """Verify ValueError is raised for blank or whitespace query strings."""
    with pytest.raises(ValueError, match="query string cannot be empty"):
        generate_query_embedding("")

    with pytest.raises(ValueError, match="query string cannot be empty"):
        generate_query_embedding("   \n\t  ")

