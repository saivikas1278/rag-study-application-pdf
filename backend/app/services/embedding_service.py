"""Local text embedding service using Sentence Transformers.

Generates dense numerical vector representations for TextChunk objects
using a locally cached SentenceTransformer model (all-MiniLM-L6-v2).
"""

import math
from typing import List, Optional, Any
import numpy as np
from app.services.chunking_service import TextChunk
from app.config import settings

# Default model producing 384-dimensional dense semantic vectors
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EXPECTED_EMBEDDING_DIM = 384

# Module-level cache to ensure the model is loaded into memory only once
_cached_model: Optional[Any] = None
_cached_model_name: Optional[str] = None


class EmbeddingGenerationError(Exception):
    """Raised when vector embedding generation or validation fails."""
    pass


def get_embedding_model(model_name: Optional[str] = None) -> Any:
    """Lazily loads and caches the SentenceTransformer model singleton.

    Args:
        model_name: Optional model identifier. Defaults to settings or all-MiniLM-L6-v2.

    Returns:
        The cached SentenceTransformer instance.
    """
    global _cached_model, _cached_model_name

    target_model = model_name or settings.embedding_model_name or DEFAULT_EMBEDDING_MODEL

    if _cached_model is None or _cached_model_name != target_model:
        from sentence_transformers import SentenceTransformer
        _cached_model = SentenceTransformer(target_model)
        _cached_model_name = target_model

    return _cached_model


def generate_chunk_embeddings(
    chunks: List[TextChunk],
    model: Optional[Any] = None,
    model_name: Optional[str] = None
) -> List[List[float]]:
    """Generates numerical vector embeddings for a list of TextChunk objects.

    Preserves the exact order of input chunks. Each returned vector is guaranteed
    to contain finite, non-null numerical values with consistent dimensionality.

    Args:
        chunks: List of TextChunk objects to be embedded.
        model: Optional pre-loaded or mock model instance (useful for unit testing).
        model_name: Optional model name if loading the singleton model.

    Returns:
        A list of float vectors (List[List[float]]) matching the order of input chunks.
        Returns an empty list [] if input chunks is empty.

    Raises:
        ValueError: If any chunk is invalid, malformed, or has empty/blank text.
        EmbeddingGenerationError: If embeddings contain non-finite numbers (NaN/Inf)
            or inconsistent vector dimensions.
    """
    # 1. Handle empty input list gracefully
    if not chunks:
        return []

    # 2. Validate input chunks and their text content
    texts_to_embed: List[str] = []
    for idx, chunk in enumerate(chunks):
        if not isinstance(chunk, TextChunk):
            raise ValueError(
                f"Invalid chunk object at index {idx}: expected TextChunk instance, "
                f"got {type(chunk).__name__}"
            )
        if not chunk.text or not chunk.text.strip():
            raise ValueError(
                f"Validation failed: Chunk at index {idx} (ID: '{chunk.chunk_id}') "
                "contains empty or whitespace-only text."
            )
        texts_to_embed.append(chunk.text)

    # 3. Retrieve model (injected mock or cached singleton)
    active_model = model or get_embedding_model(model_name=model_name)

    # 4. Generate embeddings
    try:
        raw_embeddings = active_model.encode(
            texts_to_embed,
            show_progress_bar=False,
            convert_to_numpy=True
        )
    except Exception as e:
        raise EmbeddingGenerationError(f"Model encoding failed: {str(e)}")

    # Ensure numpy array
    embeddings_array = np.asarray(raw_embeddings, dtype=np.float32)

    # 5. Validate finite values (no NaN or Inf)
    if not np.all(np.isfinite(embeddings_array)):
        raise EmbeddingGenerationError(
            "Generated embeddings contain non-finite values (NaN or Inf)."
        )

    # 6. Verify dimensionality and shape
    if len(embeddings_array.shape) != 2 or embeddings_array.shape[0] != len(chunks):
        raise EmbeddingGenerationError(
            f"Expected embedding matrix of shape ({len(chunks)}, D), "
            f"got {embeddings_array.shape}"
        )

    expected_dim = embeddings_array.shape[1]
    if expected_dim <= 0:
        raise EmbeddingGenerationError(
            f"Invalid embedding dimension ({expected_dim}) returned by model."
        )

    # 7. Convert to standard Python List[List[float]] preserving chunk order
    result: List[List[float]] = [
        vec.tolist() for vec in embeddings_array
    ]

    return result


def generate_query_embedding(
    query: str,
    model: Optional[Any] = None,
    model_name: Optional[str] = None
) -> List[float]:
    """Generates a dense numerical vector embedding for a single text query string.

    Uses the same SentenceTransformer model and embedding dimension as document chunks.

    Args:
        query: Non-empty search question or query string.
        model: Optional pre-loaded or mock model instance (useful for unit testing).
        model_name: Optional model identifier.

    Returns:
        A list of float values representing the dense semantic vector.

    Raises:
        ValueError: If query is empty or whitespace-only.
        EmbeddingGenerationError: If the model returns non-finite values or an invalid shape.
    """
    if not query or not query.strip():
        raise ValueError("query string cannot be empty or whitespace only.")

    active_model = model or get_embedding_model(model_name=model_name)

    try:
        raw_embedding = active_model.encode(
            [query.strip()],
            show_progress_bar=False,
            convert_to_numpy=True
        )
    except Exception as e:
        raise EmbeddingGenerationError(f"Model query encoding failed: {str(e)}")

    embedding_array = np.asarray(raw_embedding, dtype=np.float32)

    if not np.all(np.isfinite(embedding_array)):
        raise EmbeddingGenerationError(
            "Generated query embedding contains non-finite values (NaN or Inf)."
        )

    if len(embedding_array.shape) != 2 or embedding_array.shape[0] != 1:
        raise EmbeddingGenerationError(
            f"Expected query embedding matrix of shape (1, D), got {embedding_array.shape}"
        )

    expected_dim = embedding_array.shape[1]
    if expected_dim <= 0:
        raise EmbeddingGenerationError(
            f"Invalid query embedding dimension ({expected_dim}) returned by model."
        )

    return embedding_array[0].tolist()

