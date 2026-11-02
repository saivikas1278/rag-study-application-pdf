"""ChromaDB Vector Store Service for AI PDF Study Assistant.

Provides persistent local storage, indexing, and semantic similarity search
for document chunks and their corresponding embeddings.
"""

import math
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from pydantic import BaseModel, Field

from app.services.chunking_service import TextChunk
from app.config import settings


# ============================================================================
# Domain Schemas & Data Models
# ============================================================================

class SearchResultItem(BaseModel):
    """Structured representation of a retrieved document chunk."""
    chunk_id: str = Field(..., description="Unique ID of the matched chunk")
    text: str = Field(..., description="Text content of the retrieved chunk")
    filename: str = Field(..., description="Sanitized filename of the source document")
    page_number: int = Field(..., description="1-based page number where the chunk appears")
    chunk_index: int = Field(..., description="0-based sequential index of the chunk")
    distance: float = Field(..., description="Cosine/Euclidean distance from query embedding (lower = more similar)")


# ============================================================================
# Vector Store Engine
# ============================================================================

class VectorStoreService:
    """Manages persistent ChromaDB vector storage and semantic retrieval."""

    def __init__(
        self,
        persist_directory: Optional[Union[str, Path]] = None,
        collection_name: str = "pdf_study_chunks"
    ):
        """Initializes the ChromaDB persistent client and collection.

        Args:
            persist_directory: Path to local folder where vectors are persisted.
                               Defaults to settings.chroma_persist_directory.
            collection_name: Name of the ChromaDB collection to store study chunks.
        """
        # Resolve persistence directory
        raw_dir = persist_directory or settings.chroma_persist_directory
        self.persist_directory = Path(raw_dir).resolve()
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.collection_name = collection_name

        # Initialize persistent Chroma client (telemetry disabled for privacy and speed)
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # Retrieve or create collection without built-in embedding function
        # (embeddings are pre-computed by our Sentence Transformers service)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=None,
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(
        self,
        chunks: List[TextChunk],
        embeddings: List[List[float]]
    ) -> int:
        """Stores TextChunk objects and their corresponding pre-computed embeddings.

        Args:
            chunks: List of TextChunk objects to be indexed.
            embeddings: List of numerical float vectors corresponding 1-to-1 with chunks.

        Returns:
            The number of chunks stored.

        Raises:
            ValueError: If lengths mismatch, IDs are duplicated, or vectors are invalid.
        """
        if not chunks and not embeddings:
            return 0

        # 1. Validate length match
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Count mismatch: received {len(chunks)} chunks but {len(embeddings)} embeddings."
            )

        # 2. Validate unique IDs within the batch
        chunk_ids = [c.chunk_id for c in chunks]
        if len(set(chunk_ids)) != len(chunk_ids):
            raise ValueError("Duplicate chunk IDs detected within the input batch.")

        # 3. Validate embeddings (finite values and consistent dimensions)
        expected_dim = len(embeddings[0]) if embeddings else 0
        if expected_dim == 0:
            raise ValueError("Embedding vectors cannot be empty.")

        for idx, vec in enumerate(embeddings):
            if len(vec) != expected_dim:
                raise ValueError(
                    f"Inconsistent embedding dimension at index {idx}: "
                    f"expected {expected_dim}, got {len(vec)}."
                )
            if not all(math.isfinite(val) for val in vec):
                raise ValueError(
                    f"Embedding vector at index {idx} contains non-finite values (NaN or Inf)."
                )

        # 4. Prepare metadata and documents
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for chunk in chunks:
            # Ensure filename is strictly the basename to avoid leaking absolute system paths
            clean_filename = Path(chunk.filename).name

            documents.append(chunk.text)
            metadatas.append({
                "filename": clean_filename,
                "page_number": int(chunk.page_number),
                "chunk_index": int(chunk.chunk_index),
                "char_count": int(chunk.char_count)
            })

        # 5. Store in ChromaDB using upsert (idempotent addition)
        self.collection.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        return len(chunks)

    def search(
        self,
        query_embedding: List[float],
        n_results: int = 4,
        filter_filename: Optional[str] = None
    ) -> List[SearchResultItem]:
        """Performs semantic similarity search for a query embedding.

        Args:
            query_embedding: The pre-computed vector representation of the query.
            n_results: Maximum number of closest chunks to retrieve. Must be > 0.
            filter_filename: Optional filename to constrain search to a specific document.

        Returns:
            List of SearchResultItem objects ordered by semantic proximity.

        Raises:
            ValueError: If n_results <= 0 or query_embedding is empty/non-finite.
        """
        # 1. Validate parameters
        if n_results <= 0:
            raise ValueError(f"n_results must be a positive integer, got {n_results}")

        if not query_embedding or not all(math.isfinite(val) for val in query_embedding):
            raise ValueError("query_embedding must be a non-empty vector of finite float values.")

        # 2. Check if collection is empty
        total_items = self.collection.count()
        if total_items == 0:
            return []

        # 3. Constrain n_results to collection size
        limit = min(n_results, total_items)

        # 4. Prepare query filters
        where_filter: Optional[Dict[str, Any]] = None
        if filter_filename:
            where_filter = {"filename": Path(filter_filename).name}

        # 5. Execute similarity query
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception:
            # If where filter matches 0 documents, ChromaDB may return empty or error
            return []

        # 6. Parse and format search results safely
        search_items: List[SearchResultItem] = []

        ids_list = results.get("ids", [[]])[0]
        docs_list = results.get("documents", [[]])[0]
        metas_list = results.get("metadatas", [[]])[0]
        dists_list = results.get("distances", [[]])[0]

        for chunk_id, doc_text, meta, dist in zip(ids_list, docs_list, metas_list, dists_list):
            clean_filename = Path(str(meta.get("filename", "unknown.pdf"))).name
            search_items.append(
                SearchResultItem(
                    chunk_id=str(chunk_id),
                    text=str(doc_text),
                    filename=clean_filename,
                    page_number=int(meta.get("page_number", 1)),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    distance=float(dist)
                )
            )

        return search_items

    def delete_document(self, filename: str) -> None:
        """Deletes all chunks associated with a specific document filename.

        Args:
            filename: Name of the file whose indexed chunks should be removed.

        Raises:
            ValueError: If filename is empty.
        """
        if not filename or not filename.strip():
            raise ValueError("filename must be a non-empty string.")

        clean_filename = Path(filename).name
        self.collection.delete(where={"filename": clean_filename})

    def count(self) -> int:
        """Returns the total number of document chunks currently indexed."""
        return self.collection.count()

    def get_all_filenames(self) -> List[str]:
        """Returns a sorted list of unique document filenames present in the store."""
        if self.count() == 0:
            return []

        data = self.collection.get(include=["metadatas"])
        metadatas = data.get("metadatas", [])
        filenames = {meta["filename"] for meta in metadatas if "filename" in meta}
        return sorted(list(filenames))


# Global default vector store service singleton
vector_store_service = VectorStoreService()
