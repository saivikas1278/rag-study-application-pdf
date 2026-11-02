"""Unit tests for the PDF text extraction service."""

import pytest
import pymupdf as fitz
from pathlib import Path
from app.services.pdf_service import (
    extract_text_from_pdf,
    ExtractedPDFDocument,
    ExtractedPage,
    PDFEmptyOrCorruptedError,
    PDFPasswordProtectedError,
    PDFNoTextError,
)


def create_sample_pdf_bytes(pages_text: list[str]) -> bytes:
    """Helper to generate an in-memory PDF with specified text per page."""
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        if text.strip():
            page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_extract_text_two_page_pdf(tmp_path: Path):
    """Verify 1-based page numbers and text extraction on a two-page document."""
    page1_content = "Lecture 1: Introduction to Retrieval-Augmented Generation."
    page2_content = "Lecture 2: Vector Embeddings and ChromaDB Indexing."
    pdf_bytes = create_sample_pdf_bytes([page1_content, page2_content])

    # 1. Test in-memory bytes extraction
    result = extract_text_from_pdf(pdf_bytes, filename="biology_lecture.pdf")

    assert isinstance(result, ExtractedPDFDocument)
    assert result.filename == "biology_lecture.pdf"
    assert result.total_pages == 2
    assert len(result.pages) == 2

    # Check 1-based page numbers
    assert result.pages[0].page_number == 1
    assert page1_content in result.pages[0].text

    assert result.pages[1].page_number == 2
    assert page2_content in result.pages[1].text

    # 2. Test extraction from a physical file path
    temp_file = tmp_path / "saved_lecture.pdf"
    temp_file.write_bytes(pdf_bytes)

    result_from_file = extract_text_from_pdf(temp_file)
    assert result_from_file.filename == "saved_lecture.pdf"
    assert result_from_file.total_pages == 2
    assert result_from_file.pages[0].page_number == 1
    assert page1_content in result_from_file.pages[0].text


def test_empty_bytes_raises_error():
    """Verify that empty bytes trigger PDFEmptyOrCorruptedError."""
    with pytest.raises(PDFEmptyOrCorruptedError) as exc_info:
        extract_text_from_pdf(b"", filename="empty.pdf")
    assert "empty (0 bytes" in str(exc_info.value)


def test_corrupted_pdf_bytes_raises_error():
    """Verify that corrupt or invalid PDF bytes trigger PDFEmptyOrCorruptedError."""
    corrupted_data = b"NOT_A_VALID_PDF_HEADER_OR_CONTENT_123456"
    with pytest.raises(PDFEmptyOrCorruptedError) as exc_info:
        extract_text_from_pdf(corrupted_data, filename="corrupt.pdf")
    assert "Corrupted or invalid PDF structure" in str(exc_info.value)


def test_nonexistent_file_path_raises_error():
    """Verify that a missing file path triggers PDFEmptyOrCorruptedError."""
    missing_path = Path("non_existent_document_file.pdf")
    with pytest.raises(PDFEmptyOrCorruptedError) as exc_info:
        extract_text_from_pdf(missing_path)
    assert "not found at path" in str(exc_info.value)


def test_empty_page_scanned_pdf_raises_error():
    """Verify that PDFs with 0 extractable text raise PDFNoTextError."""
    # Create a 2-page PDF with no text (representing scanned images without OCR)
    blank_pdf_bytes = create_sample_pdf_bytes(["", ""])
    with pytest.raises(PDFNoTextError) as exc_info:
        extract_text_from_pdf(blank_pdf_bytes, filename="scanned_notes.pdf")
    assert "no extractable text" in str(exc_info.value)
    assert "scanned document or image-only" in str(exc_info.value)


def test_password_protected_pdf_raises_error():
    """Verify that encrypted/password-locked PDFs trigger PDFPasswordProtectedError."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Confidential Research Notes")
    encrypted_bytes = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw="secure_password_123",
        owner_pw="master_password_456"
    )
    doc.close()

    with pytest.raises(PDFPasswordProtectedError) as exc_info:
        extract_text_from_pdf(encrypted_bytes, filename="confidential.pdf")
    assert "password-protected" in str(exc_info.value)
