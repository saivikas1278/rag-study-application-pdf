"""Document Ingestion Service for AI PDF Study Assistant.

Orchestrates the complete ingestion pipeline:
1. Streaming file upload and size validation (max 15 MB)
2. Filename sanitization and PDF magic signature verification (%PDF-)
3. Text extraction preserving 1-based page numbers (pdf_service)
4. Sliding-window text chunking (chunking_service)
5. Dense vector embedding generation (embedding_service)
6. Atomic, idempotent storage in persistent ChromaDB (vector_store_service)
"""

import re
import logging
from pathlib import Path
from typing import Optional, Any, Tuple

from fastapi import UploadFile, HTTPException, status

from app.config import settings
from app.models.document import DocumentUploadResponse
from app.services.pdf_service import (
    extract_text_from_pdf,
    PDFEmptyOrCorruptedError,
    PDFPasswordProtectedError,
    PDFNoTextError,
    PDFExtractionError,
)
from app.services.chunking_service import chunk_extracted_document
from app.services.embedding_service import (
    generate_chunk_embeddings,
    EmbeddingGenerationError,
)
from app.services.vector_store_service import (
    VectorStoreService,
    vector_store_service as default_vector_store,
)

logger = logging.getLogger("rag-backend.ingestion")

# PDF magic bytes signature header
PDF_MAGIC_SIGNATURE = b"%PDF-"
STREAM_CHUNK_SIZE = 65536  # 64 KB read buffer


def sanitize_filename(raw_filename: Optional[str]) -> str:
    """Sanitizes an untrusted filename to prevent path traversal and shell injection.

    Extracts the basename, strips path separators and control characters,
    normalizes whitespace, strips trailing separators from the stem,
    and guarantees a safe lowercase '.pdf' extension.

    Args:
        raw_filename: The raw filename string received from the client upload.

    Returns:
        A sanitized filename string guaranteed to be safe for local storage and indexing.
    """
    if not raw_filename or not raw_filename.strip():
        return "document.pdf"

    # 1. Strip directory paths and path traversal components
    base_name = Path(raw_filename).name.strip()

    # 2. Separate extension if .pdf is present
    if base_name.lower().endswith(".pdf"):
        stem = base_name[:-4]
    else:
        stem = base_name

    # 3. Remove control characters and path separators
    clean_stem = re.sub(r'[\x00-\x1f\x7f/\\]', '', stem)

    # 4. Replace non-alphanumeric (excluding hyphens/dots) with underscore
    clean_stem = re.sub(r'[^\w\s.-]', '_', clean_stem)

    # 5. Collapse consecutive spaces and underscores into a single underscore
    clean_stem = re.sub(r'[\s_]+', '_', clean_stem)

    # 6. Strip leading and trailing punctuation/whitespace from the stem
    clean_stem = clean_stem.strip('._- ')

    if not clean_stem:
        return "document.pdf"

    return f"{clean_stem}.pdf"



async def read_and_validate_pdf_upload(
    file: UploadFile,
    max_size_mb: Optional[int] = None
) -> Tuple[bytes, str]:
    """Streams and validates an uploaded file with size and signature enforcement.

    Reads file content in bounded chunks to avoid memory exhaustion from oversized files.
    Validates file extension, MIME type, size limit, and PDF magic signature header (%PDF-).

    Args:
        file: The FastAPI UploadFile instance.
        max_size_mb: Maximum allowed file size in MB. Defaults to settings.max_upload_size_mb.

    Returns:
        A tuple of (pdf_bytes, sanitized_filename).

    Raises:
        HTTPException:
            - 400 Bad Request: Invalid extension, MIME type, empty file, or missing signature.
            - 413 Payload Too Large: Uploaded file exceeds size limit.
    """
    effective_max_mb = max_size_mb if max_size_mb is not None else settings.max_upload_size_mb
    max_bytes = effective_max_mb * 1024 * 1024

    # 1. Check filename extension
    raw_name = file.filename or ""
    if not raw_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF documents with a .pdf extension are accepted."
        )

    # 2. Check content-type if provided
    if file.content_type:
        allowed_types = {"application/pdf", "application/x-pdf", "application/octet-stream"}
        if file.content_type.lower() not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid content type '{file.content_type}'. Expected 'application/pdf'."
            )

    # 3. Stream content in chunks to prevent unbounded memory allocation
    content = bytearray()
    while chunk := await file.read(STREAM_CHUNK_SIZE):
        content.extend(chunk)
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {effective_max_mb} MB."
            )


    # 4. Check for empty file (0 bytes)
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty (0 bytes received)."
        )

    # 5. Validate PDF signature magic bytes (%PDF-)
    if len(content) < len(PDF_MAGIC_SIGNATURE) or not bytes(content).startswith(PDF_MAGIC_SIGNATURE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PDF format: file does not contain a valid PDF signature header (%PDF-)."
        )

    sanitized_name = sanitize_filename(raw_name)
    return bytes(content), sanitized_name


def ingest_pdf_document(
    file_bytes: bytes,
    filename: str,
    vector_store: Optional[VectorStoreService] = None,
    embedding_model: Optional[Any] = None
) -> DocumentUploadResponse:
    """Executes the complete document ingestion pipeline in strict sequence.

    Pipeline sequence:
    1. Extract text page-by-page preserving 1-based indices (pdf_service)
    2. Chunk extracted text with sliding window and page boundaries (chunking_service)
    3. Generate 384-dim semantic embeddings for all chunks (embedding_service)
    4. Atomically replace existing document chunks in ChromaDB (vector_store_service)

    Nothing is written to the vector store until steps 1, 2, and 3 have all succeeded.

    Args:
        file_bytes: Raw bytes of the validated PDF document.
        filename: Sanitized document filename.
        vector_store: Optional VectorStoreService instance (allows injection for testing).
        embedding_model: Optional preloaded SentenceTransformer model or mock.

    Returns:
        DocumentUploadResponse with ingestion statistics and confirmation.

    Raises:
        HTTPException:
            - 400 Bad Request: Empty/corrupted PDF, password protected, or 0 chunks.
            - 500 Internal Server Error: Embedding generation or vector storage failure.
    """
    # 1. Extract text page-by-page
    try:
        extracted_doc = extract_text_from_pdf(file_bytes, filename=filename)
    except PDFPasswordProtectedError as e:
        logger.warning(f"Rejected password-protected PDF: {filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PDFNoTextError as e:
        logger.warning(f"Rejected image-only/no-text PDF: {filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PDFEmptyOrCorruptedError as e:
        logger.warning(f"Rejected corrupted PDF: {filename} - {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PDFExtractionError as e:
        logger.error(f"PDF extraction error for '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PDF extraction failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected extraction failure for '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read PDF document structure."
        )

    # 2. Chunk extracted document
    try:
        chunked_doc = chunk_extracted_document(extracted_doc)
    except ValueError as e:
        logger.error(f"Chunking configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Text chunking configuration error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected chunking error for '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to split document text into chunks."
        )

    # Check that chunks were produced
    if not chunked_doc.chunks or chunked_doc.total_chunks == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The document '{filename}' contains no processable text chunks."
        )

    # 3. Generate dense embeddings for chunks
    try:
        embeddings = generate_chunk_embeddings(
            chunks=chunked_doc.chunks,
            model=embedding_model,
            model_name=settings.embedding_model_name
        )
    except (ValueError, EmbeddingGenerationError) as e:
        logger.error(f"Embedding generation failure for '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate vector embeddings for document chunks."
        )
    except Exception as e:
        logger.error(f"Unexpected embedding failure for '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate vector embeddings for document chunks."
        )

    # 4. Atomic, idempotent vector storage
    # Notice: we only reach this step if extraction, chunking, and embeddings succeeded!
    # If the document was previously uploaded, delete previous chunks first to avoid stale data.
    active_store = vector_store or default_vector_store
    try:
        active_store.delete_document(filename)
        active_store.add_chunks(chunked_doc.chunks, embeddings)
    except Exception as e:
        logger.error(f"ChromaDB storage failure for '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to index document chunks into vector database."
        )

    logger.info(
        f"Successfully ingested '{filename}': {extracted_doc.total_pages} pages, "
        f"{chunked_doc.total_chunks} chunks stored."
    )

    return DocumentUploadResponse(
        status="success",
        filename=filename,
        total_pages=extracted_doc.total_pages,
        total_chunks=chunked_doc.total_chunks,
        embedding_model=settings.embedding_model_name,
        message=(
            f"Successfully processed and indexed '{filename}' "
            f"({extracted_doc.total_pages} pages, {chunked_doc.total_chunks} chunks)."
        )
    )
