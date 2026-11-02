"""Domain schemas for multi-document comparison and contrast matrices."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from app.models.qa import Citation


class ComparisonRequest(BaseModel):
    """Request payload for comparing two indexed study documents."""
    doc_a: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Filename of the first document to compare."
    )
    doc_b: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Filename of the second document to compare."
    )
    comparison_focus: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional custom focus lens or comparative question (e.g. 'Compare methodologies only')."
    )
    top_k_per_doc: int = Field(
        default=5,
        ge=1,
        le=15,
        description="Number of relevant chunks to retrieve from each document independently."
    )

    @field_validator("doc_a", "doc_b")
    @classmethod
    def sanitize_filenames(cls, value: str) -> str:
        """Strips whitespace and normalizes filename."""
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Document filename cannot be empty or whitespace.")
        return trimmed

    @field_validator("doc_b")
    @classmethod
    def ensure_distinct_documents(cls, value: str, info) -> str:
        """Validates that doc_a and doc_b are different files."""
        doc_a = info.data.get("doc_a")
        if doc_a and doc_a.strip().lower() == value.strip().lower():
            raise ValueError("Cannot compare a document with itself. Please select two distinct documents.")
        return value


class ComparisonResponse(BaseModel):
    """Structured response containing the comparative contrast matrix and partitioned citations."""
    doc_a: str = Field(..., description="First document compared")
    doc_b: str = Field(..., description="Second document compared")
    comparison_focus: Optional[str] = Field(default=None, description="Custom focus lens applied, if any")
    matrix_markdown: str = Field(..., description="Structured 5-dimension comparison matrix in Markdown")
    citations_a: List[Citation] = Field(
        default_factory=list,
        description="Page citations extracted from Document A"
    )
    citations_b: List[Citation] = Field(
        default_factory=list,
        description="Page citations extracted from Document B"
    )
    model_used: str = Field(..., description="Gemini model identifier used for generation")
    has_sufficient_context: bool = Field(
        ...,
        description="Whether sufficient context was retrieved from both documents"
    )
