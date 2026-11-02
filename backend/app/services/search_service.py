"""Semantic Search Service for AI PDF Study Assistant.

Orchestrates query vectorization and similarity retrieval:
1. Validates that indexed documents exist in the vector store.
2. Converts the student question into a dense numerical vector using the same
   cached SentenceTransformers model used for document chunking.
3. Retrieves the top-k nearest matching chunks from persistent ChromaDB.
4. Formats and returns results with page numbers, filenames, chunk IDs, and cosine distances.
"""

import logging
from typing import Optional, Any, List

from fastapi import HTTPException, status

from app.models.search import SearchResponse, SearchResultChunk
from app.services.embedding_service import (
    generate_query_embedding,
    EmbeddingGenerationError,
)
from app.services.vector_store_service import (
    VectorStoreService,
    vector_store_service as default_vector_store,
)

logger = logging.getLogger("rag-backend.search")


def search_documents(
    question: str,
    top_k: int = 6,
    vector_store: Optional[VectorStoreService] = None,
    embedding_model: Optional[Any] = None
) -> SearchResponse:
    """Executes semantic similarity search for a user question against indexed PDF chunks.

    Args:
        question: Validated, non-empty user question string.
        top_k: Maximum number of closest chunks to retrieve (1 to 20).
        vector_store: Optional VectorStoreService instance (allows injection for testing).
        embedding_model: Optional pre-loaded SentenceTransformer model or mock.

    Returns:
        SearchResponse with retrieved SearchResultChunk items and diagnostic message.

    Raises:
        HTTPException:
            - 500 Internal Server Error: Vector embedding or database retrieval failure.
    """
    active_store = vector_store or default_vector_store

    # 1. Check if vector store is currently empty
    total_indexed = active_store.count()
    if total_indexed == 0:
        logger.info("Search requested on empty vector store; returning 0 results.")
        return SearchResponse(
            query=question,
            total_results=0,
            results=[],
            message="No documents are currently indexed in the vector store. Please upload a study PDF first."
        )

    # 2. Generate dense semantic embedding for the query
    try:
        query_embedding = generate_query_embedding(
            query=question,
            model=embedding_model
        )
    except (ValueError, EmbeddingGenerationError) as e:
        logger.error(f"Embedding generation failure for query '{question}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate query vector embedding."
        )
    except Exception as e:
        logger.error(f"Unexpected query embedding failure: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate query vector embedding."
        )

    # 3. Query ChromaDB for top-k matching chunks
    try:
        raw_results = active_store.search(
            query_embedding=query_embedding,
            n_results=top_k
        )
    except Exception as e:
        logger.error(f"ChromaDB retrieval failure for query '{question}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query vector database."
        )

    # 4. Format search results into API schema
    chunk_items: List[SearchResultChunk] = [
        SearchResultChunk(
            chunk_id=item.chunk_id,
            text=item.text,
            filename=item.filename,
            page_number=item.page_number,
            chunk_index=item.chunk_index,
            distance=round(item.distance, 6)
        )
        for item in raw_results
    ]

    message = (
        f"Retrieved {len(chunk_items)} relevant passage(s) matching your query."
        if chunk_items
        else "No matching passages found for your query."
    )

    return SearchResponse(
        query=question,
        total_results=len(chunk_items),
        results=chunk_items,
        message=message
    )
