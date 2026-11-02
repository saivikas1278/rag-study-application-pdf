"""Text chunking service for AI PDF Study Assistant.

Splits extracted PDF document pages into smaller, overlapping text chunks
while strictly preserving page-number boundaries and source document metadata.
"""

from typing import List
from pydantic import BaseModel, Field
from app.services.pdf_service import ExtractedPDFDocument


# ============================================================================
# Domain Schemas & Data Models
# ============================================================================

class TextChunk(BaseModel):
    """Represents an individual text chunk extracted from a specific document page."""
    chunk_id: str = Field(..., description="Unique deterministic identifier for the chunk")
    chunk_index: int = Field(..., description="0-based sequential index within the document")
    filename: str = Field(..., description="Source PDF filename")
    page_number: int = Field(..., description="1-based page number where this text originated")
    text: str = Field(..., description="Chunk text content")
    char_count: int = Field(..., description="Character count of the chunk text")


class ChunkedDocument(BaseModel):
    """Structured container holding all chunks created from an extracted PDF document."""
    filename: str = Field(..., description="Source PDF filename")
    total_chunks: int = Field(..., description="Total number of chunks produced")
    chunk_size: int = Field(..., description="Target character size per chunk")
    chunk_overlap: int = Field(..., description="Character overlap between consecutive chunks on the same page")
    chunks: List[TextChunk] = Field(default_factory=list, description="Ordered list of text chunks")


# ============================================================================
# Chunking Engine
# ============================================================================

def validate_chunking_config(chunk_size: int, chunk_overlap: int) -> None:
    """Validates chunk size and overlap parameters.

    Raises:
        ValueError: If chunk_size <= 0, chunk_overlap < 0, or chunk_overlap >= chunk_size.
    """
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be a positive integer (> 0), got {chunk_size}")
    if chunk_overlap < 0:
        raise ValueError(f"chunk_overlap must be non-negative (>= 0), got {chunk_overlap}")
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap ({chunk_overlap}) must be strictly less than chunk_size ({chunk_size})"
        )


def chunk_extracted_document(
    document: ExtractedPDFDocument,
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> ChunkedDocument:
    """Splits an ExtractedPDFDocument into structured, overlapping text chunks.

    Each page's text is chunked independently to ensure chunks never span across
    multiple pages, guaranteeing 100% accurate page citations for study notes.

    Args:
        document: The ExtractedPDFDocument containing pages with 1-based indices.
        chunk_size: Maximum character length for each chunk (default: 800).
        chunk_overlap: Number of overlapping characters between consecutive chunks (default: 150).

    Returns:
        ChunkedDocument containing metadata and the list of TextChunk objects.

    Raises:
        ValueError: If chunk_size or chunk_overlap configurations are invalid.
    """
    validate_chunking_config(chunk_size, chunk_overlap)

    step = chunk_size - chunk_overlap
    all_chunks: List[TextChunk] = []

    for page in document.pages:
        page_text = page.text.strip()
        if not page_text:
            # Skip empty or whitespace-only pages
            continue

        text_length = len(page_text)

        # Case 1: Short page fits within a single chunk
        if text_length <= chunk_size:
            chunk_idx = len(all_chunks)
            all_chunks.append(
                TextChunk(
                    chunk_id=f"{document.filename}_p{page.page_number}_c{chunk_idx}",
                    chunk_index=chunk_idx,
                    filename=document.filename,
                    page_number=page.page_number,
                    text=page_text,
                    char_count=text_length
                )
            )
            continue

        # Case 2: Long page requiring sliding window chunking
        start = 0
        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk_content = page_text[start:end]

            if chunk_content.strip():
                chunk_idx = len(all_chunks)
                all_chunks.append(
                    TextChunk(
                        chunk_id=f"{document.filename}_p{page.page_number}_c{chunk_idx}",
                        chunk_index=chunk_idx,
                        filename=document.filename,
                        page_number=page.page_number,
                        text=chunk_content,
                        char_count=len(chunk_content)
                    )
                )

            # If we reached or exceeded the end of the page text, stop
            if end >= text_length:
                break

            start += step

    return ChunkedDocument(
        filename=document.filename,
        total_chunks=len(all_chunks),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunks=all_chunks
    )
