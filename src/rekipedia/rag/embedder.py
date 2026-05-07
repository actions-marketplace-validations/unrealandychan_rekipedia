"""RAG embedder — chunk source files, embed via litellm, persist FAISS index.

Layout inside .rekipedia/:
    rag/
        index.faiss      — FAISS flat L2 index
        chunks.json      — parallel list of chunk metadata
        embed_meta.json  — embedding model + dimension + timestamp

Usage::

    from rekipedia.rag.embedder import EmbedPipeline
    pipe = EmbedPipeline(output_dir, llm_config)
    pipe.build(repo_root)           # full build
    results = pipe.search("how does auth work?", top_k=8)
"""
from __future__ import annotations

import bisect
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Iterator

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False
    np = None  # type: ignore[assignment]

try:
    import faiss  # noqa: F401
    _RAG_AVAILABLE = _NUMPY_AVAILABLE
except ImportError:
    _RAG_AVAILABLE = False

from rekipedia.models.contracts import LLMConfig

logger = logging.getLogger("rekipedia.rag.embedder")


def _mmr(
    query_vec: "np.ndarray",
    candidate_vecs: "np.ndarray",
    top_k: int,
    lambda_: float = 0.5,
) -> list[int]:
    """Maximal Marginal Relevance — diversify top-K results.

    Iteratively picks the candidate that maximises:
        lambda * sim(query, c) - (1-lambda) * max(sim(c, selected))
    """
    if len(candidate_vecs) <= top_k:
        return list(range(len(candidate_vecs)))

    # Normalise for cosine similarity
    def _norm(v):
        n = np.linalg.norm(v, axis=-1, keepdims=True)
        return v / np.where(n == 0, 1, n)

    q = _norm(query_vec.reshape(1, -1))[0]
    cands = _norm(candidate_vecs)

    query_sims = cands @ q  # shape: (N,)
    selected_indices: list[int] = []

    for _ in range(min(top_k, len(cands))):
        if not selected_indices:
            # First pick: highest query similarity
            idx = int(np.argmax(query_sims))
        else:
            selected_vecs = cands[selected_indices]  # (S, D)
            redundancy = (cands @ selected_vecs.T).max(axis=1)  # (N,)
            mmr_score = lambda_ * query_sims - (1 - lambda_) * redundancy
            # Mask already selected
            for si in selected_indices:
                mmr_score[si] = -np.inf
            idx = int(np.argmax(mmr_score))
        selected_indices.append(idx)

    return selected_indices

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default embedding model (OpenAI-compatible, cheap + fast)
_DEFAULT_EMBED_MODEL = os.environ.get(
    "REKIPEDIA_EMBED_MODEL", "text-embedding-3-small"
)

# Max chars per chunk (~512 tokens @ 4 chars/token)
_CHUNK_CHARS = 2_000
# Overlap between adjacent chunks
_OVERLAP_CHARS = 200
# Max file size to embed — configurable via env vars (skip giant files to avoid bad chunks)
# Defaults: ~80K tokens for code, ~8K tokens for docs (same heuristic as deepwiki-open)
_MAX_CODE_CHARS = int(os.environ.get("REKIPEDIA_MAX_CODE_CHARS", "320000"))   # ~80K tokens
_MAX_DOC_CHARS  = int(os.environ.get("REKIPEDIA_MAX_DOC_CHARS",  "32000"))    # ~8K tokens

# Batch size for embedding API calls
_EMBED_BATCH = 100

# File extensions to embed
_CODE_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs",
    ".java", ".kt", ".rb", ".swift", ".cs", ".cpp", ".c", ".h",
    ".html", ".css", ".scss",
}
_DOC_EXTS = {".md", ".txt", ".rst", ".yaml", ".yml", ".toml", ".json"}

# Dirs/files to skip
_SKIP_DIRS = {
    ".git", ".rekipedia", "__pycache__", "node_modules",
    "dist", "build", ".venv", "venv", ".mypy_cache", ".pytest_cache",
    "*.egg-info",
}

_RAG_DIR = "rag"
_INDEX_FILE = "index.faiss"
_CHUNKS_FILE = "chunks.json"
_EMBED_META_FILE = "embed_meta.json"


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------

def _is_implementation(path: str) -> bool:
    """Heuristic: True for core logic files, False for tests/configs.
    Borrowed from deepwiki-open's data_pipeline.py.
    """
    p = path.lower()
    parts = Path(p).parts
    return not any(
        part.startswith("test") or part in ("tests", "spec", "specs", "__tests__")
        for part in parts
    )


def _iter_repo_files(repo_root: Path) -> Iterator[Path]:
    """Walk repo, yielding files eligible for embedding."""
    skip = _SKIP_DIRS

    for f in sorted(repo_root.rglob("*")):
        if not f.is_file():
            continue
        # Skip if any ancestor dir matches skip set
        if any(part in skip or part.endswith(".egg-info") for part in f.parts):
            continue
        ext = f.suffix.lower()
        if ext not in _CODE_EXTS and ext not in _DOC_EXTS:
            continue
        yield f


def _chunk_file(path: Path, repo_root: Path) -> list[dict]:
    """Split file into overlapping text chunks with metadata including line provenance."""
    ext = path.suffix.lower()
    is_doc = ext in _DOC_EXTS
    max_chars = _MAX_DOC_CHARS if is_doc else _MAX_CODE_CHARS

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    if len(text) > max_chars:
        logger.debug("Skipping %s — too large (%d chars)", path, len(text))
        return []

    rel = str(path.relative_to(repo_root))
    impl = _is_implementation(rel)

    # Build a char→line lookup: cumulative line-start offsets for O(log N) lookup.
    line_starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            line_starts.append(i + 1)

    def char_to_line(char_offset: int) -> int:
        """Return 1-based line number for a character offset."""
        return bisect.bisect_right(line_starts, char_offset)

    chunks = []
    start = 0
    idx = 0

    while start < len(text):
        end = min(start + _CHUNK_CHARS, len(text))
        chunk_text = text[start:end]
        if chunk_text.strip():
            start_line = char_to_line(start)
            end_line = char_to_line(end - 1)
            text_hash = hashlib.sha256(chunk_text.encode("utf-8", errors="replace")).hexdigest()
            chunks.append({
                "file": rel,
                "chunk_idx": idx,
                "start_char": start,
                "end_char": end,
                "start_line": start_line,
                "end_line": end_line,
                "text_hash": text_hash,
                "text": chunk_text,
                "is_code": not is_doc,
                "is_implementation": impl,
                "ext": ext,
            })
        start += _CHUNK_CHARS - _OVERLAP_CHARS
        idx += 1

    return chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def _embed_batch(texts: list[str], model: str, llm_config: LLMConfig) -> np.ndarray:
    """Call embedding API and return (N, D) float32 array.

    Always uses litellm.embedding().  When a custom base_url is configured
    (e.g. a LiteLLM proxy), it is passed as ``api_base`` so litellm routes
    directly to that endpoint without overriding the model prefix.
    """
    import litellm  # noqa: PLC0415

    api_key = getattr(llm_config, "embed_api_key", None) or llm_config.api_key
    base_url = getattr(llm_config, "embed_base_url", None) or llm_config.base_url

    kwargs: dict = {"model": model, "input": texts}
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["api_base"] = base_url

    resp = litellm.embedding(**kwargs)
    vecs = [item["embedding"] for item in resp.data]
    return np.array(vecs, dtype=np.float32)


# ---------------------------------------------------------------------------
# EmbedPipeline
# ---------------------------------------------------------------------------

class EmbedPipeline:
    """Build and query a FAISS index over a repository's source files."""

    def __init__(self, output_dir: Path, llm_config: LLMConfig, store=None, run_id: str | None = None) -> None:
        self._out = output_dir / _RAG_DIR
        self._cfg = llm_config
        self._store = store      # optional SqliteStore for provenance
        self._run_id = run_id    # run_id to associate chunks with
        # Resolve embed model: CLI flag → config field → env var → default
        raw_model = (
            os.environ.get("REKIPEDIA_EMBED_MODEL")
            or getattr(llm_config, "embed_model", None)
            or _DEFAULT_EMBED_MODEL
        )
        # If user specified a provider, build the litellm model string: "provider/model"
        provider = (
            os.environ.get("REKIPEDIA_EMBED_PROVIDER")
            or getattr(llm_config, "embed_provider", "")
        )
        # When a custom base_url is set (e.g. LiteLLM proxy), skip the provider
        # prefix — the proxy is OpenAI-compatible and handles routing itself.
        # Only add "provider/model" when hitting the provider directly.
        has_custom_base = bool(
            getattr(llm_config, "embed_base_url", None) or llm_config.base_url
        )
        if provider and "/" not in raw_model and not has_custom_base:
            self._model = f"{provider}/{raw_model}"
        else:
            self._model = raw_model

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(
        self,
        repo_root: Path,
        progress_cb=None,
    ) -> int:
        """Chunk all eligible files, embed, save FAISS index + chunks.json.

        Returns number of chunks embedded.
        """
        try:
            import faiss as _faiss  # noqa: PLC0415
            _HAS_FAISS = True
        except ImportError:
            _faiss = None
            _HAS_FAISS = False

        self._out.mkdir(parents=True, exist_ok=True)

        # 1. Collect chunks — track skipped files
        if progress_cb:
            progress_cb("📂 Collecting source files for embedding…")
        all_chunks: list[dict] = []
        files = list(_iter_repo_files(repo_root))
        skipped_too_large = 0
        for f in files:
            ext = f.suffix.lower()
            is_doc = ext in _DOC_EXTS
            max_chars = _MAX_DOC_CHARS if is_doc else _MAX_CODE_CHARS
            try:
                size = f.stat().st_size
            except OSError:
                size = 0
            if size > max_chars:
                skipped_too_large += 1
                logger.debug("Skipping %s — too large (%d chars > %d limit)", f, size, max_chars)
                continue
            all_chunks.extend(_chunk_file(f, repo_root))

        n = len(all_chunks)
        if n == 0:
            logger.warning("No chunks to embed in %s", repo_root)
            return 0

        if progress_cb:
            skip_msg = f" ({skipped_too_large} files skipped — too large)" if skipped_too_large else ""
            progress_cb(f"🔢 Embedding {n} chunks from {len(files) - skipped_too_large} files{skip_msg}…")

        # 2. Embed in batches
        all_vecs: list[np.ndarray] = []
        texts = [c["text"] for c in all_chunks]

        for i in range(0, n, _EMBED_BATCH):
            batch = texts[i : i + _EMBED_BATCH]
            if progress_cb:
                progress_cb(
                    f"🔢 Embedding chunks {i+1}–{min(i+len(batch), n)} / {n}…"
                )
            try:
                vecs = _embed_batch(batch, self._model, self._cfg)
                all_vecs.append(vecs)
            except Exception as exc:
                logger.error("Embedding batch %d failed: %s", i // _EMBED_BATCH, exc)
                # Fill with zeros so index stays aligned — marked invalid
                dim = all_vecs[-1].shape[1] if all_vecs else 1536
                all_vecs.append(np.zeros((len(batch), dim), dtype=np.float32))
            # Respect rate limits
            time.sleep(0.1)

        if not all_vecs:
            logger.warning("No embeddings produced — nothing to index.")
            return 0
        matrix = np.vstack(all_vecs)  # (N, D)
        dim = matrix.shape[1]

        # 3. Build index
        if progress_cb:
            progress_cb(f"🗄  Building index (dim={dim}, n={n})…")
        if _HAS_FAISS:
            index = _faiss.IndexFlatL2(dim)
            _faiss.normalize_L2(matrix)
            index.add(matrix)
            _faiss.write_index(index, str(self._out / _INDEX_FILE))
        else:
            # numpy fallback — normalise + save raw matrix
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            matrix /= np.where(norms == 0, 1, norms)
            np.save(str(self._out / _INDEX_FILE) + ".npy", matrix)
        (self._out / _CHUNKS_FILE).write_text(
            json.dumps(all_chunks, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        (self._out / _EMBED_META_FILE).write_text(
            json.dumps(
                {
                    "model": self._model,
                    "dim": dim,
                    "n_chunks": n,
                    "built_at": _ts(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        logger.info("EmbedPipeline: indexed %d chunks (dim=%d)", n, dim)

        # Persist chunk provenance to store.db if a store is wired in
        if self._store is not None and self._run_id is not None:
            provenance = [
                {
                    "file_path": c["file"],
                    "chunk_idx": c["chunk_idx"],
                    "start_line": c.get("start_line", 0),
                    "end_line": c.get("end_line", 0),
                    "start_char": c.get("start_char", 0),
                    "end_char": c.get("end_char", len(c["text"])),
                    "text_hash": c.get("text_hash", ""),
                    "is_code": c.get("is_code", True),
                    "is_implementation": c.get("is_implementation", True),
                }
                for c in all_chunks
            ]
            self._store.upsert_rag_chunks(self._run_id, provenance)
            logger.info("EmbedPipeline: persisted %d chunk provenance records", len(provenance))

        if progress_cb:
            progress_cb(f"✅ FAISS index ready — {n} chunks, dim={dim}")
        return n

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 8, mmr: bool = True) -> list[dict]:
        """Return top-k most relevant chunks for *query*.

        Each result dict has: file, chunk_idx, text, score, is_implementation.
        Returns [] if no index exists.

        Args:
            query: The search query.
            top_k: Number of results to return.
            mmr: If True (default), apply Maximal Marginal Relevance to diversify results.
                 Respects REKIPEDIA_RAG_MMR=0 env var to disable.
        """
        try:
            import faiss as _faiss  # noqa: PLC0415
            _HAS_FAISS = True
        except ImportError:
            _faiss = None
            _HAS_FAISS = False

        index_path = self._out / _INDEX_FILE
        npy_path = Path(str(index_path) + ".npy")
        chunks_path = self._out / _CHUNKS_FILE

        if not chunks_path.exists():
            return []
        if not index_path.exists() and not npy_path.exists():
            return []

        try:
            chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load chunks: %s", exc)
            return []

        try:
            q_vec = _embed_batch([query], self._model, self._cfg)  # (1, D)
            if _HAS_FAISS and index_path.exists():
                index = _faiss.read_index(str(index_path))
                _faiss.normalize_L2(q_vec)
                distances, indices = index.search(q_vec, top_k)
                results = []
                for dist, idx in zip(distances[0], indices[0]):
                    if idx < 0 or idx >= len(chunks):
                        continue
                    chunk = dict(chunks[idx])
                    chunk["score"] = float(1.0 - dist / 2.0)
                    results.append(chunk)
            elif npy_path.exists():
                # numpy brute-force cosine
                matrix = np.load(str(npy_path))
                q = q_vec[0]
                q /= max(np.linalg.norm(q), 1e-9)
                scores = matrix @ q
                top_idx = np.argsort(scores)[::-1][:top_k]
                results = []
                for idx in top_idx:
                    chunk = dict(chunks[int(idx)])
                    chunk["score"] = float(scores[idx])
                    results.append(chunk)
            else:
                return []
        except Exception as exc:
            logger.warning("Search failed: %s", exc)
            return []

        # Prioritise implementation files over tests/docs
        results.sort(key=lambda c: (not c.get("is_implementation", True), -c["score"]))

        # Apply MMR deduplication if enabled
        use_mmr = mmr and os.environ.get("REKIPEDIA_RAG_MMR", "1") != "0"
        if use_mmr and _NUMPY_AVAILABLE and len(results) > 1:
            try:
                # Re-embed query to get the query vector for MMR
                q_vec_for_mmr = _embed_batch([query], self._model, self._cfg)[0]
                # Build candidate vectors from stored index
                if _HAS_FAISS and index_path.exists():
                    index_mmr = _faiss.read_index(str(index_path))
                    # Reconstruct vectors using the original result indices
                    # We need to find what indices were used
                    cand_vecs = np.array([
                        index_mmr.reconstruct(int(chunks.index(dict(
                            (k, v) for k, v in c.items() if k != "score"
                        )))) if hasattr(index_mmr, 'reconstruct') else np.zeros(q_vec_for_mmr.shape, dtype=np.float32)
                        for c in results
                    ], dtype=np.float32)
                elif npy_path.exists():
                    full_matrix = np.load(str(npy_path))
                    # Find chunk indices in original chunks list
                    cand_indices = []
                    for r in results:
                        for i, c in enumerate(chunks):
                            if c.get("file") == r.get("file") and c.get("chunk_idx") == r.get("chunk_idx"):
                                cand_indices.append(i)
                                break
                    if len(cand_indices) == len(results):
                        cand_vecs = full_matrix[cand_indices]
                        mmr_order = _mmr(q_vec_for_mmr, cand_vecs, top_k)
                        results = [results[i] for i in mmr_order]
            except Exception as exc:
                logger.debug("MMR failed (non-fatal): %s", exc)

        return results

    # ------------------------------------------------------------------
    # Introspect
    # ------------------------------------------------------------------

    def meta(self) -> dict | None:
        p = self._out / _EMBED_META_FILE
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def is_built(self) -> bool:
        return (self._out / _INDEX_FILE).exists() or (self._out / (_INDEX_FILE + ".npy")).exists()

    # ------------------------------------------------------------------
    # Incremental update
    # ------------------------------------------------------------------

    def update(
        self,
        repo_root: Path,
        changed_files: list[str],
        last_run_id: int | str | None,
        new_run_id: int | str | None,
        progress_cb=None,
    ) -> int:
        """Incrementally update the RAG index — only re-embed chunks from changed files.

        Returns number of chunks re-embedded (not total chunks).
        Falls back to full build() if no existing index found.
        """
        chunks_path = self._out / _CHUNKS_FILE
        index_path = self._out / _INDEX_FILE
        npy_path = Path(str(index_path) + ".npy")

        if not chunks_path.exists() or (not index_path.exists() and not npy_path.exists()):
            if progress_cb:
                progress_cb("No existing index found — falling back to full build…")
            return self.build(repo_root, progress_cb)

        try:
            import faiss as _faiss  # noqa: PLC0415
            _HAS_FAISS = True
        except ImportError:
            _faiss = None
            _HAS_FAISS = False

        # Load existing chunks + vectors
        existing_chunks: list[dict] = json.loads(chunks_path.read_text(encoding="utf-8"))
        if _HAS_FAISS and index_path.exists():
            old_index = _faiss.read_index(str(index_path))
            old_vecs = np.array([old_index.reconstruct(i) for i in range(len(existing_chunks))], dtype=np.float32)
        elif npy_path.exists():
            old_vecs = np.load(str(npy_path))
        else:
            return self.build(repo_root, progress_cb)

        changed_set = set(changed_files)

        # Separate kept vs stale
        kept_chunks: list[dict] = []
        kept_vecs: list[np.ndarray] = []
        # Build a hash→vec map for stale chunks (for reuse if hash unchanged)
        stale_hash_to_vec: dict[str, np.ndarray] = {}

        for i, chunk in enumerate(existing_chunks):
            if chunk["file"] not in changed_set:
                kept_chunks.append(chunk)
                kept_vecs.append(old_vecs[i])
            else:
                stale_hash_to_vec[chunk["text_hash"]] = old_vecs[i]

        # Re-chunk changed files that still exist
        reused_chunks: list[dict] = []
        reused_vecs: list[np.ndarray] = []
        to_embed_chunks: list[dict] = []

        for rel_path in changed_files:
            abs_path = repo_root / rel_path
            if not abs_path.exists():
                continue  # deleted — skip
            new_chunks = _chunk_file(abs_path, repo_root)
            for chunk in new_chunks:
                h = chunk["text_hash"]
                if h in stale_hash_to_vec:
                    reused_chunks.append(chunk)
                    reused_vecs.append(stale_hash_to_vec[h])
                else:
                    to_embed_chunks.append(chunk)

        n_to_embed = len(to_embed_chunks)
        if progress_cb:
            progress_cb(f"🔢 Re-embedding {n_to_embed} new/modified chunks ({len(reused_chunks)} reused, {len(kept_chunks)} unchanged)…")

        # Embed new chunks
        new_vecs_list: list[np.ndarray] = []
        if n_to_embed > 0:
            texts = [c["text"] for c in to_embed_chunks]
            for i in range(0, n_to_embed, _EMBED_BATCH):
                batch = texts[i: i + _EMBED_BATCH]
                if progress_cb:
                    progress_cb(f"🔢 Embedding chunks {i+1}–{min(i+len(batch), n_to_embed)} / {n_to_embed}…")
                try:
                    vecs = _embed_batch(batch, self._model, self._cfg)
                    new_vecs_list.append(vecs)
                except Exception as exc:
                    logger.error("Embedding batch %d failed: %s", i // _EMBED_BATCH, exc)
                    dim = old_vecs.shape[1]
                    new_vecs_list.append(np.zeros((len(batch), dim), dtype=np.float32))
                import time as _time  # noqa: PLC0415
                _time.sleep(0.1)

        # Combine all chunks + vecs
        all_chunks = kept_chunks + reused_chunks + to_embed_chunks
        all_vecs_parts: list[np.ndarray] = []
        if kept_vecs:
            all_vecs_parts.append(np.array(kept_vecs, dtype=np.float32))
        if reused_vecs:
            all_vecs_parts.append(np.array(reused_vecs, dtype=np.float32))
        if new_vecs_list:
            all_vecs_parts.append(np.vstack(new_vecs_list))

        if not all_chunks or not all_vecs_parts:
            logger.warning("No chunks after update — index not modified.")
            return n_to_embed

        matrix = np.vstack(all_vecs_parts)
        dim = matrix.shape[1]

        self._out.mkdir(parents=True, exist_ok=True)

        if _HAS_FAISS:
            index = _faiss.IndexFlatL2(dim)
            _faiss.normalize_L2(matrix)
            index.add(matrix)
            _faiss.write_index(index, str(index_path))
        else:
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            matrix /= np.where(norms == 0, 1, norms)
            np.save(str(npy_path), matrix)

        chunks_path.write_text(json.dumps(all_chunks, ensure_ascii=False, indent=1), encoding="utf-8")

        # Update embed_meta
        (self._out / _EMBED_META_FILE).write_text(
            json.dumps({"model": self._model, "dim": dim, "n_chunks": len(all_chunks), "built_at": _ts()}, indent=2),
            encoding="utf-8",
        )

        logger.info("EmbedPipeline.update: %d re-embedded, %d reused, %d kept", n_to_embed, len(reused_chunks), len(kept_chunks))

        # Store provenance
        if self._store is not None and new_run_id is not None:
            # Carry forward unchanged file provenance from last run
            if last_run_id is not None:
                unchanged_paths = list({c["file"] for c in kept_chunks})
                self._store.carry_forward_rag_chunks(last_run_id, new_run_id, unchanged_paths)
            # Upsert provenance for changed/new chunks
            provenance = [
                {
                    "file_path": c["file"],
                    "chunk_idx": c["chunk_idx"],
                    "start_line": c.get("start_line", 0),
                    "end_line": c.get("end_line", 0),
                    "start_char": c.get("start_char", 0),
                    "end_char": c.get("end_char", len(c["text"])),
                    "text_hash": c.get("text_hash", ""),
                    "is_code": c.get("is_code", True),
                    "is_implementation": c.get("is_implementation", True),
                }
                for c in reused_chunks + to_embed_chunks
            ]
            if provenance:
                self._store.upsert_rag_chunks(new_run_id, provenance)

        if progress_cb:
            progress_cb(f"✅ RAG index updated — {len(all_chunks)} total chunks, {n_to_embed} re-embedded")
        return n_to_embed


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ts() -> str:
    from datetime import datetime, timezone  # noqa: PLC0415
    return datetime.now(timezone.utc).isoformat()
