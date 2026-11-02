"""Query Service coordinating Retrieval-Augmented Generation (RAG).

Connects semantic search retrieval (search_service) to the Gemini LLM service (llm_service):
1. Retrieves top-k semantically relevant chunks from persistent ChromaDB.
2. If no chunks are retrieved, safely returns an insufficient-context response without calling Gemini.
3. If chunks exist, sends them to Gemini with prompt-injection shielding and citation constraints.
4. Verifies citations against retrieved source metadata.
5. Formats structured QueryResponse with verified citations and diagnostic flags.
"""

import logging
from typing import Optional, Any, Set, Tuple

from fastapi import HTTPException, status

from app.config import settings
from app.models.qa import QueryResponse, Citation
from app.services.search_service import search_documents
from app.services.llm_service import (
    generate_grounded_answer,
    LLMConfigurationError,
    LLMRateLimitError,
    LLMModelUnavailableError,
    LLMServiceError,
)
from app.services.vector_store_service import VectorStoreService

logger = logging.getLogger("rag-backend.query")


def process_study_query(
    question: str,
    top_k: int = 6,
    vector_store: Optional[VectorStoreService] = None,
    embedding_model: Optional[Any] = None,
    llm_client: Optional[Any] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> QueryResponse:
    """Executes end-to-end RAG answering for a student question.

    Args:
        question: Validated, non-empty student question.
        top_k: Number of relevant chunks to retrieve (1 to 20).
        vector_store: Optional VectorStoreService instance (allows injection for testing).
        embedding_model: Optional embedding model instance (allows injection for testing).
        llm_client: Optional Google GenAI client instance (allows injection for testing).
        api_key: Optional Gemini API key override. Defaults to settings.gemini_api_key.
        model_name: Optional Gemini model name override. Defaults to settings.gemini_model.

    Returns:
        QueryResponse containing grounded answer, verified citations, and context sufficiency.

    Raises:
        HTTPException:
            - 400 Bad Request: Invalid question input.
            - 429 Too Many Requests: Gemini rate limit / quota exceeded.
            - 500 Internal Server Error: Retrieval failure, unconfigured API key, or generation error.
            - 503 Service Unavailable: Configured model unavailable.
    """
    clean_question = question.strip() if question else ""
    if not clean_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or whitespace only."
        )

    active_model = model_name or settings.gemini_model or "gemini-2.5-flash"

    # 1. Retrieve relevant passages using semantic search service
    try:
        search_response = search_documents(
            question=clean_question,
            top_k=top_k,
            vector_store=vector_store,
            embedding_model=embedding_model
        )
    except HTTPException:
        # Re-raise explicit HTTP exceptions from search service (e.g. 500 on ChromaDB/embedding failure)
        raise
    except Exception as e:
        logger.error(f"Unexpected retrieval failure during query processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document passages from knowledge base."
        )

    # 2. Check if any passages were retrieved
    # If 0 passages found, return safe fallback immediately without invoking Gemini
    if search_response.total_results == 0 or not search_response.results:
        logger.info(f"0 passages retrieved for query '{clean_question}'; returning fallback.")
        return QueryResponse(
            question=clean_question,
            answer="The uploaded documents do not contain sufficient information to answer this question.",
            citations=[],
            has_sufficient_context=False,
            model_used=active_model
        )

    # 3. Generate grounded answer using Gemini LLM service
    try:
        grounded_answer = generate_grounded_answer(
            question=clean_question,
            passages=search_response.results,
            client=llm_client,
            api_key=api_key,
            model_name=active_model
        )
    except LLMConfigurationError as e:
        logger.error(f"Gemini configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini API is not configured. Please set GEMINI_API_KEY in the backend environment."
        )
    except LLMRateLimitError as e:
        logger.warning(f"Gemini rate limit exceeded: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Gemini API rate limit or quota exceeded. Please try again shortly."
        )
    except LLMModelUnavailableError as e:
        logger.error(f"Gemini model unavailable: {e}")
        err_msg = str(e)
        if not err_msg or "unavailable" not in err_msg.lower():
            err_msg = f"Gemini model '{active_model}' is currently unavailable: {err_msg}".strip(": ")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=err_msg
        )
    except LLMServiceError as e:
        logger.error(f"Gemini generation failure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate answer from study materials. Please check server logs for details."
        )
    except Exception as e:
        logger.error(f"Unexpected query failure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your query."
        )

    # 4. Strict Citation Verification
    # Ensure every citation corresponds strictly to actual retrieved source metadata
    valid_sources: Set[Tuple[str, int]] = {
        (chunk.filename, chunk.page_number) for chunk in search_response.results
    }

    verified_citations: list[Citation] = []
    if grounded_answer.has_sufficient_context:
        for citation in grounded_answer.citations:
            if (citation.filename, citation.page_number) in valid_sources:
                verified_citations.append(citation)

    return QueryResponse(
        question=clean_question,
        answer=grounded_answer.answer,
        citations=verified_citations,
        has_sufficient_context=grounded_answer.has_sufficient_context,
        model_used=grounded_answer.model_used
    )
