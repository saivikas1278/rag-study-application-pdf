"""Comparison Service coordinating Multi-Document Retrieval and Contrast Matrix Generation.

Performs balanced retrieval across two distinct documents from ChromaDB, constructs a
structured comparative prompt for Gemini, and parses partitioned citations.
"""

import time
import logging
from typing import Optional, Any, List, Set, Tuple

from fastapi import HTTPException, status
from google import genai
from google.genai import types

from app.config import settings
from app.models.comparison import ComparisonRequest, ComparisonResponse
from app.models.qa import Citation
from app.services.vector_store_service import VectorStoreService, SearchResultItem
from app.services.embedding_service import generate_query_embedding
from app.services.llm_service import (
    LLMConfigurationError,
    LLMRateLimitError,
    LLMModelUnavailableError,
    LLMServiceError,
    is_insufficient_context_refusal,
)

logger = logging.getLogger("rag-backend.comparison")

COMPARISON_SYSTEM_INSTRUCTION = """You are an elite Academic Comparative Analyst and Study Mentor. Your mission is to provide rigorous, clear, and pedagogically rich comparisons between two study documents.

CORE ANALYSIS GUIDELINES:
1. STRICT FACTUAL GROUNDING:
   - All claims must be grounded in the provided excerpts in <context_documents>.
   - Never hallucinate nonexistent sections, dates, formulas, or claims.
   - If either document lacks sufficient information on a particular point, explicitly state: "Document context does not specify this aspect."

2. 5-DIMENSION MATRIX STRUCTURE:
   Structure your comparative analysis into these 5 clear dimensions:
   ### 🎯 1. Core Objectives & Scope
   Compare the primary mission, target audience, and scope of Document A vs. Document B.

   ### 🤝 2. Shared Concepts & Common Ground
   Detail foundational principles, shared definitions, or theories that both documents agree upon.

   ### ⚖️ 3. Key Differences & Discrepancies
   Provide a clean Markdown comparison table:
   | Dimension / Aspect | Document A | Document B |
   |---|---|---|
   | ... | ... | ... |
   Follow the table with specific explanations of conflicting claims, divergent methodologies, or different terminology.

   ### 💡 4. Unique Insights & Exclusive Coverage
   - **Exclusive to Document A**: Key concepts covered only here.
   - **Exclusive to Document B**: Key concepts covered only here.

   ### 🧩 5. Unified Synthesis & Study Recommendations
   Provide actionable guidance on how a student or researcher should synthesize knowledge from both documents for mastery.

3. EXPLICIT CITATIONS:
   - When referencing claims from Document A, cite using format: [filename, Page X]
   - When referencing claims from Document B, cite using format: [filename, Page X]
"""


def compare_study_documents(
    payload: ComparisonRequest,
    vector_store: Optional[VectorStoreService] = None,
    embedding_model: Optional[Any] = None,
    llm_client: Optional[Any] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> ComparisonResponse:
    """Performs multi-document comparison across two indexed PDFs.

    Args:
        payload: Validated ComparisonRequest with doc_a, doc_b, and optional focus.
        vector_store: Optional VectorStoreService instance for testing/injection.
        embedding_model: Optional embedding model instance.
        llm_client: Optional Google GenAI client instance.
        api_key: Optional API key override.
        model_name: Optional model override.

    Returns:
        ComparisonResponse with structured matrix and partitioned citations.
    """
    doc_a = payload.doc_a
    doc_b = payload.doc_b
    focus = payload.comparison_focus

    # 1. Resolve vector store
    store = vector_store or VectorStoreService()

    # 2. Formulate comparative search query
    search_query = (
        f"Compare and contrast: {focus}"
        if focus and focus.strip()
        else "Core thesis, key principles, definitions, methodology, and conclusions"
    )

    try:
        query_emb = generate_query_embedding(search_query, model=embedding_model)
    except Exception as e:
        logger.error(f"Failed to generate query embedding for comparison: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embedding for comparison query: {str(e)}"
        )

    # 3. Perform balanced dual-retrieval
    try:
        chunks_a: List[SearchResultItem] = store.search(
            query_embedding=query_emb,
            n_results=payload.top_k_per_doc,
            filter_filename=doc_a
        )
        chunks_b: List[SearchResultItem] = store.search(
            query_embedding=query_emb,
            n_results=payload.top_k_per_doc,
            filter_filename=doc_b
        )
    except Exception as e:
        logger.error(f"Vector search failed during document comparison: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed during comparison retrieval: {str(e)}"
        )

    # 4. Handle missing document scenarios
    if not chunks_a and not chunks_b:
        return ComparisonResponse(
            doc_a=doc_a,
            doc_b=doc_b,
            comparison_focus=focus,
            matrix_markdown=(
                f"I could not find indexed passages for either '{doc_a}' or '{doc_b}' in the knowledge base. "
                "Please verify that both PDF files have been uploaded and indexed before comparing."
            ),
            citations_a=[],
            citations_b=[],
            model_used=model_name or settings.gemini_model,
            has_sufficient_context=False
        )

    if not chunks_a:
        return ComparisonResponse(
            doc_a=doc_a,
            doc_b=doc_b,
            comparison_focus=focus,
            matrix_markdown=(
                f"Could not find indexed passages for '{doc_a}'. "
                f"'{doc_b}' is indexed, but comparison requires both documents to be present in the active knowledge base."
            ),
            citations_a=[],
            citations_b=[],
            model_used=model_name or settings.gemini_model,
            has_sufficient_context=False
        )

    if not chunks_b:
        return ComparisonResponse(
            doc_a=doc_a,
            doc_b=doc_b,
            comparison_focus=focus,
            matrix_markdown=(
                f"Could not find indexed passages for '{doc_b}'. "
                f"'{doc_a}' is indexed, but comparison requires both documents to be present in the active knowledge base."
            ),
            citations_a=[],
            citations_b=[],
            model_used=model_name or settings.gemini_model,
            has_sufficient_context=False
        )

    # 5. Build dual-document context prompt
    context_lines = ["<context_documents>"]

    context_lines.append(f"\n=== DOCUMENT A: {doc_a} ===")
    for idx, c in enumerate(chunks_a, start=1):
        clean_text = c.text.strip().replace("\n", " ")
        context_lines.append(f"[Excerpt A{idx} | Source: {c.filename}, Page {c.page_number}]: {clean_text}")

    context_lines.append(f"\n=== DOCUMENT B: {doc_b} ===")
    for idx, c in enumerate(chunks_b, start=1):
        clean_text = c.text.strip().replace("\n", " ")
        context_lines.append(f"[Excerpt B{idx} | Source: {c.filename}, Page {c.page_number}]: {clean_text}")

    context_lines.append("</context_documents>\n")

    user_prompt = (
        f"{''.join(context_lines)}\n"
        f"TASK: Generate a comprehensive 5-dimension Comparative Contrast Matrix comparing '{doc_a}' and '{doc_b}'.\n"
    )
    if focus and focus.strip():
        user_prompt += f"SPECIAL COMPARISON FOCUS: {focus.strip()}\n"

    # 6. Initialize GenAI client
    active_key = api_key or settings.gemini_api_key
    active_model = model_name or settings.gemini_model

    if not active_key or active_key == "your_gemini_api_key_here":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini API key is not configured on the server."
        )

    try:
        active_client = llm_client or genai.Client(api_key=active_key)
    except Exception as e:
        logger.error(f"Failed to initialize Google GenAI client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize Google GenAI client: {str(e)}"
        )

    # 7. Execute generation with retry loop
    max_retries = 2
    retry_delay = 1.5
    response = None

    for attempt in range(max_retries + 1):
        try:
            response = active_client.models.generate_content(
                model=active_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=COMPARISON_SYSTEM_INSTRUCTION,
                    temperature=0.3,
                )
            )
            break
        except Exception as e:
            err_msg = str(e).lower()
            err_type = type(e).__name__
            is_transient = (
                "503" in err_msg
                or "unavailable" in err_msg
                or "high demand" in err_msg
                or "500" in err_msg
                or "servererror" in err_type.lower()
            )

            if is_transient and attempt < max_retries:
                logger.warning(f"Transient Gemini failure during comparison. Retrying in {retry_delay}s: {e}")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue

            logger.error(f"Gemini API call failed during comparison [{err_type}]: {e}")
            if "429" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Gemini API rate limit or quota exceeded. Please wait a moment and try again."
                )
            elif "503" in err_msg or "unavailable" in err_msg:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Gemini model '{active_model}' is currently experiencing high demand. Please try again shortly."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Document comparison failed: {err_type}"
                )

    if not response or not getattr(response, "text", None) or not response.text.strip():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini model returned an empty response for document comparison."
        )

    matrix_text = response.text.strip()
    is_insufficient = is_insufficient_context_refusal(matrix_text)

    # 8. Partition and collect verified citations
    citations_a: List[Citation] = []
    citations_b: List[Citation] = []

    if not is_insufficient:
        seen_a: Set[Tuple[str, int]] = set()
        for c in chunks_a:
            key = (c.filename, c.page_number)
            if key not in seen_a:
                seen_a.add(key)
                citations_a.append(Citation(filename=c.filename, page_number=c.page_number))

        seen_b: Set[Tuple[str, int]] = set()
        for c in chunks_b:
            key = (c.filename, c.page_number)
            if key not in seen_b:
                seen_b.add(key)
                citations_b.append(Citation(filename=c.filename, page_number=c.page_number))

    return ComparisonResponse(
        doc_a=doc_a,
        doc_b=doc_b,
        comparison_focus=focus,
        matrix_markdown=matrix_text,
        citations_a=citations_a,
        citations_b=citations_b,
        model_used=active_model,
        has_sufficient_context=not is_insufficient
    )
