"""Tests for pluggable vector store backends (issue #131)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from rekipedia.rag.vector_store import (
    ChromaStore,
    FaissStore,
    QdrantStore,
    VectorStore,
    get_vector_store,
)


def _random_vecs(n: int = 10, dim: int = 16) -> np.ndarray:
    rng = np.random.default_rng(42)
    return rng.random((n, dim)).astype("float32")


def _dummy_chunks(n: int = 10) -> list[dict]:
    return [{"file": "foo.py", "chunk_idx": i, "text": f"chunk {i}"} for i in range(n)]


# ---------------------------------------------------------------------------
# FaissStore tests
# ---------------------------------------------------------------------------

def test_faiss_store_add_search(tmp_path: Path) -> None:
    store = FaissStore(out_dir=tmp_path)
    vecs = _random_vecs(10, 16)
    store.add(vecs, _dummy_chunks(10))

    q = _random_vecs(1, 16)
    results = store.search(q, top_k=3)
    assert len(results) == 3
    for idx, score in results:
        assert 0 <= idx < 10
        assert isinstance(score, float)


def test_faiss_store_is_built(tmp_path: Path) -> None:
    store = FaissStore(out_dir=tmp_path)
    assert not store.is_built()
    vecs = _random_vecs(5, 16)
    store.add(vecs, _dummy_chunks(5))
    store.save()
    assert store.is_built()


def test_faiss_store_reconstruct_all(tmp_path: Path) -> None:
    store = FaissStore(out_dir=tmp_path)
    vecs = _random_vecs(8, 16)
    store.add(vecs, _dummy_chunks(8))
    arr = store.reconstruct_all()
    assert arr is not None
    assert arr.shape[0] == 8
    assert arr.shape[1] == 16


# ---------------------------------------------------------------------------
# get_vector_store factory tests
# ---------------------------------------------------------------------------

def test_get_vector_store_default(tmp_path: Path) -> None:
    store = get_vector_store(tmp_path, cfg_dict=None)
    assert isinstance(store, FaissStore)


def test_get_vector_store_faiss_explicit(tmp_path: Path) -> None:
    store = get_vector_store(tmp_path, cfg_dict={"rag": {"backend": "faiss"}})
    assert isinstance(store, FaissStore)


# ---------------------------------------------------------------------------
# QdrantStore ImportError test
# ---------------------------------------------------------------------------

def test_qdrant_store_import_error() -> None:
    """If qdrant-client is not installed, add() should raise ImportError with install hint."""
    store = QdrantStore(url="http://localhost:6333", collection="rekipedia")
    # Force qdrant_client to be missing
    with patch.dict(sys.modules, {"qdrant_client": None, "qdrant_client.models": None}):
        with pytest.raises(ImportError, match="qdrant-client"):
            store._client = None  # reset cached client
            store.add(_random_vecs(3, 8), _dummy_chunks(3))


# ---------------------------------------------------------------------------
# ChromaStore ImportError test
# ---------------------------------------------------------------------------

def test_chroma_store_import_error() -> None:
    """If chromadb is not installed, add() should raise ImportError with install hint."""
    store = ChromaStore(path="/tmp/nonexistent_chroma", collection="rekipedia")
    with patch.dict(sys.modules, {"chromadb": None}):
        with pytest.raises(ImportError, match="chromadb"):
            store._client = None
            store._collection = None
            store.add(_random_vecs(3, 8), _dummy_chunks(3))


# ---------------------------------------------------------------------------
# Interface test
# ---------------------------------------------------------------------------

def test_vector_store_interface(tmp_path: Path) -> None:
    """FaissStore satisfies the VectorStore ABC."""
    store = FaissStore(out_dir=tmp_path)
    assert isinstance(store, VectorStore)
    # All abstract methods are implemented
    assert hasattr(store, "add")
    assert hasattr(store, "search")
    assert hasattr(store, "save")
    assert hasattr(store, "load")
    assert hasattr(store, "is_built")
    assert hasattr(store, "reconstruct_all")
