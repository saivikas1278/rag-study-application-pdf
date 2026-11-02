"""Domain schemas for document upload and ingestion."""

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Structured response schema returned after successful PDF ingestion."""
    status: str = Field(default="success", description="Upload processing status ('success')")
    filename: str = Field(..., description="Sanitized filename of the ingested document")
    total_pages: int = Field(..., description="Total number of extracted pages from the PDF")
    total_chunks: int = Field(..., description="Total number of chunks indexed into vector storage")
    embedding_model: str = Field(..., description="Identifier of the embedding model used for vectorization")
    message: str = Field(..., description="User-facing confirmation message summarizing upload results")
