"""PDF text extraction service using PyMuPDF (fitz).

This service is responsible for extracting text from PDF documents page-by-page
while preserving 1-based page indices and validating file integrity.
"""

import os
from pathlib import Path
from typing import List, Union, Optional
import pymupdf as fitz
from pydantic import BaseModel, Field


# ============================================================================
# Domain Schemas & Data Models
# ============================================================================

class ExtractedPage(BaseModel):
    """Represents text extracted from a single PDF page."""
    page_number: int = Field(..., description="1-based index of the PDF page (1, 2, ...)")
    text: str = Field(..., description="Raw text content extracted from the page")


class ExtractedPDFDocument(BaseModel):
    """Structured representation of a parsed PDF document."""
    filename: str = Field(..., description="Name of the parsed PDF file")
    total_pages: int = Field(..., description="Total number of pages present in the document")
    pages: List[ExtractedPage] = Field(default_factory=list, description="Extracted pages with 1-based indices")


# ============================================================================
# Custom Exception Hierarchy
# ============================================================================

class PDFExtractionError(Exception):
    """Base exception for all PDF extraction failures."""
    pass


class PDFPasswordProtectedError(PDFExtractionError):
    """Raised when a PDF requires a password to open or extract text."""
    pass


class PDFEmptyOrCorruptedError(PDFExtractionError):
    """Raised when the PDF data is empty, truncated, or invalid."""
    pass


class PDFNoTextError(PDFExtractionError):
    """Raised when the document contains pages but no extractable text (e.g. scanned images)."""
    pass


# ============================================================================
# PDF Extraction Engine
# ============================================================================

def extract_text_from_pdf(
    file_source: Union[bytes, str, Path],
    filename: Optional[str] = None
) -> ExtractedPDFDocument:
    """Extracts text page-by-page from a PDF document with 1-based page numbers.

    Args:
        file_source: The PDF document as raw bytes or a local file path.
        filename: Optional human-readable filename for identification and metadata.

    Returns:
        ExtractedPDFDocument containing the filename, total pages, and a list of
        ExtractedPage instances (each having 1-based page_number and text).

    Raises:
        PDFEmptyOrCorruptedError: If file is empty, missing, or not a valid PDF.
        PDFPasswordProtectedError: If the PDF is encrypted/password-locked.
        PDFNoTextError: If the document contains 0 extractable text characters.
    """
    doc: Optional[fitz.Document] = None

    # Resolve filename
    resolved_filename = filename or "document.pdf"

    try:
        # 1. Validate and open source
        if isinstance(file_source, bytes):
            if len(file_source) == 0:
                raise PDFEmptyOrCorruptedError(
                    f"PDF file '{resolved_filename}' is empty (0 bytes received)."
                )
            try:
                doc = fitz.open(stream=file_source, filetype="pdf")
            except Exception as e:
                raise PDFEmptyOrCorruptedError(
                    f"Corrupted or invalid PDF structure in '{resolved_filename}': {str(e)}"
                )

        elif isinstance(file_source, (str, Path)):
            path = Path(file_source)
            if not resolved_filename or resolved_filename == "document.pdf":
                resolved_filename = path.name

            if not path.exists():
                raise PDFEmptyOrCorruptedError(
                    f"PDF file not found at path: {path}"
                )
            if path.stat().st_size == 0:
                raise PDFEmptyOrCorruptedError(
                    f"PDF file '{resolved_filename}' is empty (0 bytes)."
                )
            try:
                doc = fitz.open(str(path))
            except Exception as e:
                raise PDFEmptyOrCorruptedError(
                    f"Corrupted or invalid PDF structure in '{resolved_filename}': {str(e)}"
                )
        else:
            raise PDFEmptyOrCorruptedError(
                f"Unsupported file source type: {type(file_source).__name__}"
            )

        # 2. Check for password protection / encryption
        if doc.is_encrypted:
            # Check if it requires a password to read
            # If doc.authenticate('') returns 0, it is locked
            if not doc.authenticate(""):
                raise PDFPasswordProtectedError(
                    f"The PDF document '{resolved_filename}' is password-protected and cannot be processed."
                )

        # 3. Check for 0-page document
        total_pages = len(doc)
        if total_pages == 0:
            raise PDFEmptyOrCorruptedError(
                f"The PDF document '{resolved_filename}' contains 0 pages."
            )

        # 4. Extract page-by-page text preserving 1-based page indices
        pages: List[ExtractedPage] = []
        total_text_length = 0

        for page_idx in range(total_pages):
            page = doc.load_page(page_idx)
            page_text = page.get_text("text").strip()
            page_number = page_idx + 1  # 1-based indexing for student-facing citations

            pages.append(
                ExtractedPage(
                    page_number=page_number,
                    text=page_text
                )
            )
            total_text_length += len(page_text)

        # 5. Check if the entire document is scanned / image-only (0 extractable text)
        if total_text_length == 0:
            raise PDFNoTextError(
                f"The PDF document '{resolved_filename}' contains no extractable text. "
                "The file may be a scanned document or image-only without selectable text."
            )

        return ExtractedPDFDocument(
            filename=resolved_filename,
            total_pages=total_pages,
            pages=pages
        )

    finally:
        # Guarantee resource release
        if doc is not None:
            doc.close()
