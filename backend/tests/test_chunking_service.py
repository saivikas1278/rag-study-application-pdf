"""Unit tests for the text chunking service."""

import pytest
from app.services.pdf_service import ExtractedPDFDocument, ExtractedPage
from app.services.chunking_service import (
    chunk_extracted_document,
    validate_chunking_config,
    TextChunk,
    ChunkedDocument,
)


def test_short_page_produces_single_chunk():
    """Verify that a page with text shorter than chunk_size produces exactly one chunk."""
    doc = ExtractedPDFDocument(
        filename="summary.pdf",
        total_pages=1,
        pages=[
            ExtractedPage(page_number=1, text="Short lecture summary on AI fundamentals.")
        ]
    )

    result = chunk_extracted_document(doc, chunk_size=800, chunk_overlap=150)

    assert isinstance(result, ChunkedDocument)
    assert result.total_chunks == 1
    assert len(result.chunks) == 1
    assert result.chunks[0].page_number == 1
    assert result.chunks[0].filename == "summary.pdf"
    assert result.chunks[0].text == "Short lecture summary on AI fundamentals."
    assert result.chunks[0].chunk_index == 0


def test_long_page_produces_multiple_chunks():
    """Verify that a long page is split into multiple chunks."""
    long_text = "A" * 1500  # 1500 characters
    doc = ExtractedPDFDocument(
        filename="long_doc.pdf",
        total_pages=1,
        pages=[ExtractedPage(page_number=1, text=long_text)]
    )

    # chunk_size = 500, overlap = 100 -> step = 400
    # Chunk 0: 0..500
    # Chunk 1: 400..900
    # Chunk 2: 800..1300
    # Chunk 3: 1200..1500 (length 300)
    result = chunk_extracted_document(doc, chunk_size=500, chunk_overlap=100)

    assert result.total_chunks == 4
    assert len(result.chunks) == 4
    for idx, chunk in enumerate(result.chunks):
        assert chunk.chunk_index == idx
        assert chunk.page_number == 1
        assert chunk.filename == "long_doc.pdf"


def test_correct_overlap_between_adjacent_chunks():
    """Verify that consecutive chunks on the same page have the exact expected character overlap."""
    # Create sample text with distinct character offsets
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" * 10  # 360 characters
    chunk_size = 100
    chunk_overlap = 30
    step = chunk_size - chunk_overlap  # 70

    doc = ExtractedPDFDocument(
        filename="overlap_test.pdf",
        total_pages=1,
        pages=[ExtractedPage(page_number=1, text=alphabet)]
    )

    result = chunk_extracted_document(doc, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    assert result.total_chunks > 1

    for i in range(len(result.chunks) - 1):
        current_chunk = result.chunks[i]
        next_chunk = result.chunks[i + 1]

        # The trailing `chunk_overlap` chars of current_chunk must match
        # the leading `chunk_overlap` chars of next_chunk
        overlap_from_current = current_chunk.text[-chunk_overlap:]
        overlap_from_next = next_chunk.text[:chunk_overlap]

        assert overlap_from_current == overlap_from_next, (
            f"Overlap mismatch between chunk {i} and {i + 1}: "
            f"'{overlap_from_current}' != '{overlap_from_next}'"
        )


def test_correct_filename_and_page_metadata():
    """Verify that chunk metadata accurately reflects the source document and 1-based page numbers."""
    doc = ExtractedPDFDocument(
        filename="machine_learning_notes.pdf",
        total_pages=2,
        pages=[
            ExtractedPage(page_number=1, text="Page 1: Supervised learning algorithms."),
            ExtractedPage(page_number=2, text="Page 2: Unsupervised clustering techniques.")
        ]
    )

    result = chunk_extracted_document(doc, chunk_size=800, chunk_overlap=150)

    assert result.total_chunks == 2
    assert result.filename == "machine_learning_notes.pdf"

    # Chunk 0 from Page 1
    assert result.chunks[0].filename == "machine_learning_notes.pdf"
    assert result.chunks[0].page_number == 1
    assert "Supervised learning" in result.chunks[0].text
    assert result.chunks[0].chunk_id == "machine_learning_notes.pdf_p1_c0"

    # Chunk 1 from Page 2
    assert result.chunks[1].filename == "machine_learning_notes.pdf"
    assert result.chunks[1].page_number == 2
    assert "Unsupervised clustering" in result.chunks[1].text
    assert result.chunks[1].chunk_id == "machine_learning_notes.pdf_p2_c1"


def test_different_pages_remain_separate():
    """Verify that text from different pages is never blended into a single chunk."""
    page1_text = "Page One Content " * 5  # ~85 chars
    page2_text = "Page Two Content " * 5  # ~85 chars

    doc = ExtractedPDFDocument(
        filename="separation.pdf",
        total_pages=2,
        pages=[
            ExtractedPage(page_number=1, text=page1_text),
            ExtractedPage(page_number=2, text=page2_text)
        ]
    )

    # Use a large chunk size (2000) that could theoretically hold both pages
    result = chunk_extracted_document(doc, chunk_size=2000, chunk_overlap=100)

    # Must produce 2 distinct chunks, NOT 1 merged chunk
    assert result.total_chunks == 2
    assert result.chunks[0].page_number == 1
    assert "Page Two" not in result.chunks[0].text

    assert result.chunks[1].page_number == 2
    assert "Page One" not in result.chunks[1].text


def test_empty_or_whitespace_pages_produce_no_chunks():
    """Verify that empty or whitespace-only pages are safely skipped."""
    doc = ExtractedPDFDocument(
        filename="empty_pages.pdf",
        total_pages=3,
        pages=[
            ExtractedPage(page_number=1, text="   "),
            ExtractedPage(page_number=2, text="\n\t\n  "),
            ExtractedPage(page_number=3, text="Valid content on page 3.")
        ]
    )

    result = chunk_extracted_document(doc, chunk_size=800, chunk_overlap=150)

    assert result.total_chunks == 1
    assert result.chunks[0].page_number == 3
    assert result.chunks[0].text == "Valid content on page 3."


def test_invalid_chunk_sizes_and_overlap_settings():
    """Verify that invalid configurations raise clear ValueError exceptions."""
    doc = ExtractedPDFDocument(
        filename="test.pdf",
        total_pages=1,
        pages=[ExtractedPage(page_number=1, text="Some text")]
    )

    # 1. chunk_size <= 0
    with pytest.raises(ValueError, match="chunk_size must be a positive integer"):
        chunk_extracted_document(doc, chunk_size=0, chunk_overlap=0)

    with pytest.raises(ValueError, match="chunk_size must be a positive integer"):
        chunk_extracted_document(doc, chunk_size=-100, chunk_overlap=0)

    # 2. chunk_overlap < 0
    with pytest.raises(ValueError, match="chunk_overlap must be non-negative"):
        chunk_extracted_document(doc, chunk_size=500, chunk_overlap=-10)

    # 3. chunk_overlap >= chunk_size
    with pytest.raises(ValueError, match="must be strictly less than chunk_size"):
        chunk_extracted_document(doc, chunk_size=500, chunk_overlap=500)

    with pytest.raises(ValueError, match="must be strictly less than chunk_size"):
        chunk_extracted_document(doc, chunk_size=500, chunk_overlap=600)


def test_determinism_and_repeatability():
    """Verify that multiple runs with identical input yield identical chunk output."""
    sample_text = (
        "Retrieval-Augmented Generation (RAG) is a technique that combines an information "
        "retrieval component with a text generator model. It allows large language models to "
        "retrieve up-to-date and domain-specific knowledge from external databases."
    )
    doc = ExtractedPDFDocument(
        filename="rag_paper.pdf",
        total_pages=1,
        pages=[ExtractedPage(page_number=1, text=sample_text)]
    )

    run_1 = chunk_extracted_document(doc, chunk_size=100, chunk_overlap=30)
    run_2 = chunk_extracted_document(doc, chunk_size=100, chunk_overlap=30)

    assert run_1.total_chunks == run_2.total_chunks
    for c1, c2 in zip(run_1.chunks, run_2.chunks):
        assert c1.chunk_id == c2.chunk_id
        assert c1.chunk_index == c2.chunk_index
        assert c1.page_number == c2.page_number
        assert c1.text == c2.text
        assert c1.char_count == c2.char_count
