"""FastAPI application entry point for AI PDF Study Assistant."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.models.document import DocumentUploadResponse
from app.models.search import SearchRequest, SearchResponse
from app.models.qa import QueryRequest, QueryResponse
from app.models.comparison import ComparisonRequest, ComparisonResponse
from app.services.ingestion_service import (
    read_and_validate_pdf_upload,
    ingest_pdf_document,
)
from app.services.search_service import search_documents
from app.services.query_service import process_study_query
from app.services.comparison_service import compare_study_documents
from app.services.embedding_service import is_gemini_embedding_model


# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("rag-backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to pre-warm models and check system readiness."""
    logger.info(f"Starting server in {settings.environment} mode...")
    logger.info(f"Active embedding model: {settings.embedding_model_name}")

    if not is_gemini_embedding_model():
        try:
            logger.info("Pre-warming local SentenceTransformer embedding model...")
            from app.services.embedding_service import get_embedding_model
            get_embedding_model()
            logger.info("Local SentenceTransformer model loaded successfully.")
        except Exception as e:
            logger.warning(f"Embedding model pre-warming deferred: {e}")
    else:
        logger.info("Using Gemini Cloud Embeddings (Zero PyTorch RAM footprint).")

    yield

    logger.info("Shutting down RAG backend.")


app = FastAPI(
    title="AI PDF Study Assistant API",
    description="Backend API powering PDF extraction, local embeddings, vector retrieval, Gemini QA, and multi-document comparisons.",
    version="0.1.0",
    lifespan=lifespan
)

# Enable Cross-Origin Resource Sharing (CORS) for React frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.api_route("/", methods=["GET", "HEAD"])
def root():
    """Root endpoint welcoming users to the RAG API."""
    return {
        "message": "AI PDF Study Assistant API is running.",
        "docs_url": "/docs",
        "health_check": "/api/health"
    }


@app.api_route("/api/health", methods=["GET", "HEAD"])
def health_check():
    """Health check endpoint to verify server status and active configurations."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.environment,
        "embedding_model": settings.embedding_model_name,
        "gemini_api_configured": bool(settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here")
    }


@app.post(
    "/api/documents/upload",
    response_model=DocumentUploadResponse,
    summary="Upload and ingest a PDF document",
    description="Validates, extracts, chunks, embeds, and indexes a PDF study document into persistent ChromaDB."
)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    """Handles PDF file upload and runs the ingestion pipeline."""
    pdf_bytes, sanitized_filename = await read_and_validate_pdf_upload(file)
    return ingest_pdf_document(file_bytes=pdf_bytes, filename=sanitized_filename)


@app.post(
    "/api/search",
    response_model=SearchResponse,
    summary="Semantic similarity search across indexed PDF chunks",
    description="Embeds a student question and retrieves the top-k most relevant document chunks from ChromaDB."
)
def search_documents_endpoint(payload: SearchRequest) -> SearchResponse:
    """Performs semantic similarity search against indexed PDF documents."""
    return search_documents(question=payload.question, top_k=payload.top_k)


@app.post(
    "/api/query",
    response_model=QueryResponse,
    summary="Ask a question and receive a grounded answer with citations",
    description="Retrieves relevant PDF excerpts from ChromaDB and uses Gemini to synthesize a grounded answer citing source filenames and page numbers."
)
def query_documents_endpoint(payload: QueryRequest) -> QueryResponse:
    """Answers a student question using retrieved study document passages and Gemini."""
    return process_study_query(question=payload.question, top_k=payload.top_k)


@app.post(
    "/api/documents/compare",
    response_model=ComparisonResponse,
    summary="Compare two indexed PDF documents side-by-side",
    description="Performs balanced semantic retrieval across two distinct documents in ChromaDB and uses Gemini to construct a structured 5-dimension Contrast Matrix."
)
def compare_documents_endpoint(payload: ComparisonRequest) -> ComparisonResponse:
    """Compares two indexed study documents and returns a structured contrast matrix."""
    return compare_study_documents(payload=payload)


# Serve built frontend static assets if available (Production / Docker single-service mode)
from pathlib import Path
from fastapi.staticfiles import StaticFiles

_frontend_dist_candidates = [
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
    Path("/app/frontend/dist"),
]

for _dist in _frontend_dist_candidates:
    if _dist.exists() and (_dist / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")
        break


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
