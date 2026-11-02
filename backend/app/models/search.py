"""Domain schemas for semantic similarity search."""

from typing import List
from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    """Request schema for semantic similarity search."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The query or question to search relevant document passages for."
    )
    top_k: int = Field(
        default=6,
        ge=1,
        le=20,
        description="Maximum number of semantically relevant chunks to retrieve (between 1 and 20)."
    )

    @field_validator("question")
    @classmethod
    def validate_question_not_whitespace(cls, value: str) -> str:
        """Ensures the question contains non-whitespace content."""
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("question cannot be empty or whitespace only.")
        return trimmed


class SearchResultChunk(BaseModel):
    """Schema for an individual retrieved chunk."""
    chunk_id: str = Field(..., description="Unique deterministic identifier for the chunk")
    text: str = Field(..., description="Extracted text content of the retrieved chunk")
    filename: str = Field(..., description="Source document filename")
    page_number: int = Field(..., description="1-based page number where the chunk appears")
    chunk_index: int = Field(..., description="Sequential index of the chunk within the document")
    distance: float = Field(
        ...,
        description="Cosine distance from query vector (lower value indicates greater semantic similarity)"
    )


class SearchResponse(BaseModel):
    """Structured response schema returned by the semantic search endpoint."""
    query: str = Field(..., description="Sanitized query string that was searched")
    total_results: int = Field(..., description="Total number of chunks returned")
    results: List[SearchResultChunk] = Field(
        default_factory=list,
        description="Ordered list of top matching chunks (closest first)"
    )
    message: str = Field(..., description="Summary confirmation or diagnostic message")
