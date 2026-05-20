"""Pluggable vector store backends for rekipedia RAG.

Supported backends:
    - faiss  (default, built-in)
    - qdrant (optional, requires qdrant-client>=1.9)
    - chroma (optional, requires chromadb>=0.5)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False
    np = None  # type: ignore[assignment]


class VectorStore(ABC):
    """Abstract base class for vector store backends."""

    @abstractmethod
    def add(self, vecs: "np.ndarray", chunks: list[dict]) -> None:
        """Add/upsert vectors with associated chunk metadata."""
        ...

    @abstractmethod
    def search(self, q_vec: "np.ndarray", top_k: int) -> list[tuple[int, float]]:
        """Search for top_k nearest vectors. Returns list of (chunk_idx, score)."""
        ...

    @abstractmethod
    def save(self) -> None:
        """Persist the index to disk."""
        ...

    @classmethod
    @abstractmethod
    def load(cls, out_dir: Path, **kwargs: Any) -> "VectorStore":
        """Load a persisted store from out_dir."""
        ...

    @abstractmethod
    def is_built(self) -> bool:
        """Return True if the index exists and has vectors."""
        ...

    @abstractmethod
    def reconstruct_all(self) -> "np.ndarray | None":
        """Return all vectors as numpy array, or None if unsupported (e.g. for MMR)."""
        ...


# ---------------------------------------------------------------------------
# FaissStore
# ---------------------------------------------------------------------------

class FaissStore(VectorStore):
    """FAISS-backed vector store (default backend)."""

    _INDEX_FILE = "index.faiss"
    _NPY_FILE = "index.faiss.npy"

    def __init__(self, out_dir: Path) -> None:
        self._out_dir = out_dir
        self._index: Any = None  # faiss index or None
        self._matrix: "np.ndarray | None" = None  # numpy fallback
        self._use_faiss = False
        self._dim: int = 0

    def add(self, vecs: "np.ndarray", chunks: list[dict]) -> None:  # noqa: ARG002
        try:
            import faiss as _faiss  # noqa: PLC0415
            self._use_faiss = True
        except ImportError:
            _faiss = None
            self._use_faiss = False

        mat = vecs.astype("float32")
        self._dim = mat.shape[1]

        if self._use_faiss:
            import faiss as _faiss  # noqa: PLC0415, F811
            _faiss.normalize_L2(mat)
            idx = _faiss.IndexFlatL2(self._dim)
            idx.add(mat)
            self._index = idx
        else:
            norms = np.linalg.norm(mat, axis=1, keepdims=True)
            mat /= np.where(norms == 0, 1, norms)
            self._matrix = mat

    def search(self, q_vec: "np.ndarray", top_k: int) -> list[tuple[int, float]]:
        q = q_vec.astype("float32")
        if self._use_faiss and self._index is not None:
            import faiss as _faiss  # noqa: PLC0415
            _faiss.normalize_L2(q)
            distances, indices = self._index.search(q, top_k)
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0:
                    continue
                results.append((int(idx), float(1.0 - dist / 2.0)))
            return results
        elif self._matrix is not None:
            qv = q[0] / max(float(np.linalg.norm(q[0])), 1e-9)
            scores = self._matrix @ qv
            top_idx = np.argsort(scores)[::-1][:top_k]
            return [(int(i), float(scores[i])) for i in top_idx]
        # Try loading from disk
        loaded = self._try_load_index()
        if loaded:
            return self.search(q_vec, top_k)
        return []

    def _try_load_index(self) -> bool:
        index_path = self._out_dir / self._INDEX_FILE
        npy_path = self._out_dir / self._NPY_FILE
        try:
            import faiss as _faiss  # noqa: PLC0415
            if index_path.exists():
                self._index = _faiss.read_index(str(index_path))
                self._use_faiss = True
                return True
        except ImportError:
            pass
        if npy_path.exists():
            self._matrix = np.load(str(npy_path))
            self._use_faiss = False
            return True
        return False

    def save(self) -> None:
        self._out_dir.mkdir(parents=True, exist_ok=True)
        if self._use_faiss and self._index is not None:
            import faiss as _faiss  # noqa: PLC0415
            _faiss.write_index(self._index, str(self._out_dir / self._INDEX_FILE))
        elif self._matrix is not None:
            np.save(str(self._out_dir / self._NPY_FILE), self._matrix)

    @classmethod
    def load(cls, out_dir: Path, **kwargs: Any) -> "FaissStore":  # noqa: ARG003
        store = cls(out_dir)
        store._try_load_index()
        return store

    def is_built(self) -> bool:
        return (
            (self._out_dir / self._INDEX_FILE).exists()
            or (self._out_dir / self._NPY_FILE).exists()
        )

    def reconstruct_all(self) -> "np.ndarray | None":
        if self._matrix is not None:
            return self._matrix
        # Try numpy fallback on disk
        npy_path = self._out_dir / self._NPY_FILE
        if npy_path.exists():
            return np.load(str(npy_path))
        # FAISS IndexFlatL2 supports reconstruct
        if self._index is None:
            self._try_load_index()
        if self._index is not None:
            try:
                n = self._index.ntotal
                vecs = np.array(
                    [self._index.reconstruct(i) for i in range(n)], dtype="float32"
                )
                return vecs
            except Exception:
                return None
        return None


# ---------------------------------------------------------------------------
# QdrantStore
# ---------------------------------------------------------------------------

class QdrantStore(VectorStore):
    """Qdrant-backed vector store (optional, requires qdrant-client>=1.9)."""

    def __init__(self, url: str = "http://localhost:6333", collection: str = "rekipedia") -> None:
        self._url = url
        self._collection = collection
        self._dim: int = 0
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "qdrant-client is not installed. Install it with: pip install 'rekipedia[qdrant]'"
            ) from exc
        self._client = QdrantClient(url=self._url)
        return self._client

    def add(self, vecs: "np.ndarray", chunks: list[dict]) -> None:  # noqa: ARG002
        try:
            from qdrant_client.models import Distance, PointStruct, VectorParams  # noqa: PLC0415
        except (ImportError, ModuleNotFoundError) as exc:
            raise ImportError(
                "qdrant-client is not installed. Install it with: pip install 'rekipedia[qdrant]'"
            ) from exc

        client = self._get_client()
        dim = vecs.shape[1]
        self._dim = dim

        # Ensure collection exists
        existing = [c.name for c in client.get_collections().collections]
        if self._collection not in existing:
            client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

        points = [
            PointStruct(id=i, vector=vecs[i].tolist(), payload={"chunk_idx": i})
            for i in range(len(vecs))
        ]
        client.upsert(collection_name=self._collection, points=points)

    def search(self, q_vec: "np.ndarray", top_k: int) -> list[tuple[int, float]]:
        client = self._get_client()
        results = client.search(
            collection_name=self._collection,
            query_vector=q_vec[0].tolist(),
            limit=top_k,
        )
        return [(int(r.payload["chunk_idx"]), float(r.score)) for r in results]

    def save(self) -> None:
        pass  # Qdrant persists automatically

    @classmethod
    def load(cls, out_dir: Path, **kwargs: Any) -> "QdrantStore":  # noqa: ARG003
        url = kwargs.get("url", "http://localhost:6333")
        collection = kwargs.get("collection", "rekipedia")
        return cls(url=url, collection=collection)

    def is_built(self) -> bool:
        try:
            client = self._get_client()
            info = client.get_collection(self._collection)
            return info.points_count > 0
        except Exception:
            return False

    def reconstruct_all(self) -> "np.ndarray | None":
        return None  # Not supported


# ---------------------------------------------------------------------------
# ChromaStore
# ---------------------------------------------------------------------------

class ChromaStore(VectorStore):
    """Chroma-backed vector store (optional, requires chromadb>=0.5)."""

    def __init__(self, path: str = ".rekipedia/chroma", collection: str = "rekipedia") -> None:
        self._path = path
        self._collection_name = collection
        self._client: Any = None
        self._collection: Any = None

    def _get_collection(self) -> Any:
        if self._collection is not None:
            return self._collection
        try:
            import chromadb  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "chromadb is not installed. Install it with: pip install 'rekipedia[chroma]'"
            ) from exc
        self._client = chromadb.PersistentClient(path=self._path)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def add(self, vecs: "np.ndarray", chunks: list[dict]) -> None:  # noqa: ARG002
        col = self._get_collection()
        ids = [str(i) for i in range(len(vecs))]
        embeddings = [vecs[i].tolist() for i in range(len(vecs))]
        metadatas = [{"chunk_idx": i} for i in range(len(vecs))]
        col.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)

    def search(self, q_vec: "np.ndarray", top_k: int) -> list[tuple[int, float]]:
        col = self._get_collection()
        results = col.query(
            query_embeddings=[q_vec[0].tolist()],
            n_results=top_k,
            include=["metadatas", "distances"],
        )
        out = []
        for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
            chunk_idx = int(meta["chunk_idx"])
            # Chroma cosine distance: 0=identical, 2=opposite. Convert to similarity.
            score = float(1.0 - dist)
            out.append((chunk_idx, score))
        return out

    def save(self) -> None:
        pass  # Chroma PersistentClient persists automatically

    @classmethod
    def load(cls, out_dir: Path, **kwargs: Any) -> "ChromaStore":  # noqa: ARG003
        path = kwargs.get("path", ".rekipedia/chroma")
        collection = kwargs.get("collection", "rekipedia")
        return cls(path=path, collection=collection)

    def is_built(self) -> bool:
        try:
            col = self._get_collection()
            return col.count() > 0
        except Exception:
            return False

    def reconstruct_all(self) -> "np.ndarray | None":
        return None  # Not supported


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_vector_store(
    output_dir: Path,
    cfg_dict: dict | None = None,
    llm_config: Any = None,  # noqa: ARG001
) -> VectorStore:
    """Return the configured VectorStore backend.

    Reads ``rag.backend`` from cfg_dict (or defaults to 'faiss').
    """
    rag_cfg: dict = {}
    if cfg_dict:
        rag_cfg = cfg_dict.get("rag", {}) or {}

    backend = rag_cfg.get("backend", "faiss") or "faiss"

    if backend == "qdrant":
        url = rag_cfg.get("qdrant_url", "http://localhost:6333")
        collection = rag_cfg.get("qdrant_collection", "rekipedia")
        return QdrantStore(url=url, collection=collection)
    elif backend == "chroma":
        chroma_path = rag_cfg.get("chroma_path", ".rekipedia/chroma")
        return ChromaStore(path=chroma_path, collection="rekipedia")
    else:
        # Default: faiss
        rag_dir = output_dir / "rag"
        return FaissStore(out_dir=rag_dir)
