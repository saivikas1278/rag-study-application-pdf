"""Unit tests for the ChromaDB vector store service."""

import pytest
import math
from pathlib import Path
from app.services.chunking_service import TextChunk
from app.services.vector_store_service import (
    VectorStoreService,
    SearchResultItem,
)


def create_test_chunk(chunk_id: str, text: str, filename: str = "notes.pdf", page: int = 1, idx: int = 0) -> TextChunk:
    """Helper to generate a TextChunk instance."""
    return TextChunk(
        chunk_id=chunk_id,
        chunk_index=idx,
        filename=filename,
        page_number=page,
        text=text,
        char_count=len(text)
    )


def test_add_and_retrieve_chunk_similarity_search(tmp_path: Path):
    """Verify adding chunks and retrieving the most semantically relevant chunk."""
    store = VectorStoreService(persist_directory=tmp_path, collection_name="test_search")

    # Create 2 distinct 4-dimensional synthetic chunks
    chunk_ai = create_test_chunk("c_ai", "Deep learning and neural networks.", filename="cs101.pdf", page=1, idx=0)
    chunk_bio = create_test_chunk("c_bio", "Cellular respiration and genetics.", filename="bio101.pdf", page=2, idx=1)

    # Orthogonal embeddings: vec_ai along dim 0, vec_bio along dim 1
    emb_ai = [1.0, 0.0, 0.0, 0.0]
    emb_bio = [0.0, 1.0, 0.0, 0.0]

    added = store.add_chunks([chunk_ai, chunk_bio], [emb_ai, emb_bio])
    assert added == 2
    assert store.count() == 2

    # Query with a vector aligned with AI: [0.9, 0.0, 0.0, 0.0]
    results = store.search(query_embedding=[0.9, 0.0, 0.0, 0.0], n_results=2)

    assert len(results) == 2
    assert isinstance(results[0], SearchResultItem)
    # The first result must be AI
    assert results[0].chunk_id == "c_ai"
    assert results[0].filename == "cs101.pdf"
    assert results[0].page_number == 1
    assert results[0].chunk_index == 0
    assert "neural networks" in results[0].text
    assert math.isclose(results[0].distance, 0.0, abs_tol=1e-4)

    # The second result must be Bio (with higher cosine distance)
    assert results[1].chunk_id == "c_bio"
    assert results[1].distance > results[0].distance


def test_persistence_across_reopening(tmp_path: Path):
    """Verify that indexed chunks survive vector store reload from the same directory."""
    # Instance 1: write data
    store1 = VectorStoreService(persist_directory=tmp_path, collection_name="persistent_col")
    chunk = create_test_chunk("c_pers", "Persistent storage in ChromaDB.", filename="db_lecture.pdf", page=5)
    store1.add_chunks([chunk], [[0.5, 0.5, 0.5, 0.5]])
    assert store1.count() == 1

    # Instance 2: reopen same directory
    store2 = VectorStoreService(persist_directory=tmp_path, collection_name="persistent_col")
    assert store2.count() == 1

    results = store2.search(query_embedding=[0.5, 0.5, 0.5, 0.5], n_results=1)
    assert len(results) == 1
    assert results[0].chunk_id == "c_pers"
    assert results[0].filename == "db_lecture.pdf"
    assert results[0].page_number == 5


def test_document_level_deletion(tmp_path: Path):
    """Verify deleting one document's chunks leaves other documents untouched."""
    store = VectorStoreService(persist_directory=tmp_path, collection_name="test_del")

    chunks = [
        create_test_chunk("doc1_c1", "Chemistry notes part 1", filename="chem.pdf", page=1),
        create_test_chunk("doc1_c2", "Chemistry notes part 2", filename="chem.pdf", page=2),
        create_test_chunk("doc2_c1", "History notes part 1", filename="history.pdf", page=1),
    ]
    embeddings = [
        [1.0, 0.0, 0.0, 0.0],
        [0.8, 0.2, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0]
    ]

    store.add_chunks(chunks, embeddings)
    assert store.count() == 3
    assert store.get_all_filenames() == ["chem.pdf", "history.pdf"]

    # Delete chem.pdf only
    store.delete_document("chem.pdf")

    assert store.count() == 1
    assert store.get_all_filenames() == ["history.pdf"]

    # Search to confirm only history chunk remains
    results = store.search(query_embedding=[1.0, 0.0, 0.0, 0.0], n_results=5)
    assert len(results) == 1
    assert results[0].chunk_id == "doc2_c1"
    assert results[0].filename == "history.pdf"


def test_empty_collection_behavior(tmp_path: Path):
    """Verify searching an empty collection returns [] gracefully without error."""
    store = VectorStoreService(persist_directory=tmp_path, collection_name="empty_col")
    assert store.count() == 0

    results = store.search(query_embedding=[1.0, 0.0, 0.0, 0.0], n_results=3)
    assert results == []
    assert store.get_all_filenames() == []


def test_filter_by_filename(tmp_path: Path):
    """Verify search filter limits results strictly to the specified filename."""
    store = VectorStoreService(persist_directory=tmp_path, collection_name="test_filter")

    chunks = [
        create_test_chunk("c_math", "Calculus and derivatives", filename="math.pdf", page=1),
        create_test_chunk("c_phys", "Physics kinematics equations", filename="physics.pdf", page=1),
    ]
    embeddings = [
        [0.7, 0.7, 0.0, 0.0],
        [0.7, 0.7, 0.0, 0.0],
    ]
    store.add_chunks(chunks, embeddings)

    # Search filtered by math.pdf
    math_results = store.search(query_embedding=[0.7, 0.7, 0.0, 0.0], n_results=5, filter_filename="math.pdf")
    assert len(math_results) == 1
    assert math_results[0].filename == "math.pdf"


def test_invalid_inputs_raise_errors(tmp_path: Path):
    """Verify robust validation for mismatched lengths, duplicate IDs, non-finite values, and limits."""
    store = VectorStoreService(persist_directory=tmp_path, collection_name="test_val")

    chunk = create_test_chunk("c1", "Sample text")

    # 1. Count mismatch
    with pytest.raises(ValueError, match="Count mismatch"):
        store.add_chunks([chunk], [])

    # 2. Duplicate chunk IDs
    with pytest.raises(ValueError, match="Duplicate chunk IDs"):
        store.add_chunks([chunk, chunk], [[1.0, 0.0], [1.0, 0.0]])

    # 3. Non-finite values in embedding
    with pytest.raises(ValueError, match="non-finite values"):
        store.add_chunks([chunk], [[float("nan"), 1.0, 0.0, 0.0]])

    # 4. Inconsistent dimensions
    chunk2 = create_test_chunk("c2", "Sample text 2")
    with pytest.raises(ValueError, match="Inconsistent embedding dimension"):
        store.add_chunks([chunk, chunk2], [[1.0, 0.0], [1.0, 0.0, 0.0]])

    # 5. Invalid n_results (<= 0)
    with pytest.raises(ValueError, match="n_results must be a positive integer"):
        store.search(query_embedding=[1.0, 0.0], n_results=0)

    # 6. Invalid query_embedding (empty or non-finite)
    with pytest.raises(ValueError, match="query_embedding must be a non-empty vector"):
        store.search(query_embedding=[], n_results=2)

    with pytest.raises(ValueError, match="query_embedding must be a non-empty vector"):
        store.search(query_embedding=[float("inf"), 1.0], n_results=2)

    # 7. Empty filename in delete
    with pytest.raises(ValueError, match="filename must be a non-empty string"):
        store.delete_document("")
