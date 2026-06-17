"""AI/ML-backed embedding index for the BandGate knowledge base.

The index is built once from the markdown corpus (existing
``knowledge_base/`` plus the new ``knowledge_base/external/`` real-world
compliance subset) and persisted to ``output/embedding_index.json`` so the
backend can boot fast.

At query time, callers embed the question, take cosine top-N candidates,
and ask AI/ML to rerank. If embedding or rerank fall through, callers fall
back to keyword retrieval. The deterministic demo path always survives.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

from core.model_clients import aiml_available, aiml_embed
from core.paths import find_resource, project_root

DEFAULT_INDEX_PATH = "output/embedding_index.json"
DEFAULT_KB_ROOTS = ("knowledge_base",)
_EMBED_BATCH = 16


@dataclass(frozen=True)
class IndexedChunk:
    document_name: str
    chunk_id: str
    heading: str
    text: str


@dataclass(frozen=True)
class RankedChunk:
    chunk: IndexedChunk
    score: float


class EmbeddingIndex:
    """In-memory cosine index with on-disk persistence.

    The index is provider-aware: if AI/ML embeddings fail at build time we
    leave the vectors empty, and ``search`` returns no candidates so callers
    fall back to keyword search. If they succeed at build time but fail at
    query time we still degrade gracefully.
    """

    def __init__(
        self,
        chunks: list[IndexedChunk],
        vectors: list[list[float]],
        embedding_model: str,
    ) -> None:
        # Allow an empty vector list with non-empty chunks so callers can build a
        # "degraded" index when AI/ML embeddings are unavailable; RAG then falls
        # back to keyword search via core.rag.retrieve.
        if vectors and len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must be the same length")
        self.chunks = chunks
        self.vectors = vectors
        self.embedding_model = embedding_model

    @property
    def ready(self) -> bool:
        return bool(self.chunks and self.vectors)

    def search(self, query: str, top_k: int = 20) -> list[RankedChunk]:
        if not self.ready:
            return []
        query_vec = aiml_embed([query])
        if not query_vec:
            return []
        qv = query_vec[0]
        scored: list[RankedChunk] = []
        for chunk, vec in zip(self.chunks, self.vectors):
            score = _cosine(qv, vec)
            if score > 0:
                scored.append(RankedChunk(chunk=chunk, score=score))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def save(self, path: str = DEFAULT_INDEX_PATH) -> Path:
        target = _resolve_output_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "embedding_model": self.embedding_model,
            "chunks": [
                {
                    "document_name": c.document_name,
                    "chunk_id": c.chunk_id,
                    "heading": c.heading,
                    "text": c.text,
                    "vector": v,
                }
                for c, v in zip(self.chunks, self.vectors)
            ],
        }
        target.write_text(json.dumps(payload), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str = DEFAULT_INDEX_PATH) -> "EmbeddingIndex | None":
        target = _resolve_output_path(path)
        if not target.exists():
            return None
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        chunks: list[IndexedChunk] = []
        vectors: list[list[float]] = []
        for raw in payload.get("chunks", []):
            try:
                chunks.append(
                    IndexedChunk(
                        document_name=str(raw["document_name"]),
                        chunk_id=str(raw["chunk_id"]),
                        heading=str(raw.get("heading", "")),
                        text=str(raw.get("text", "")),
                    )
                )
                vectors.append([float(v) for v in raw["vector"]])
            except (KeyError, TypeError, ValueError):
                continue
        if not chunks:
            return None
        return cls(chunks=chunks, vectors=vectors, embedding_model=str(payload.get("embedding_model", "")))


_INDEX_CACHE: EmbeddingIndex | None = None
_INDEX_CACHE_TIMESTAMP: float | None = None


def get_index(path: str = DEFAULT_INDEX_PATH) -> EmbeddingIndex | None:
    """Return the cached index, loading from disk on first call."""
    global _INDEX_CACHE, _INDEX_CACHE_TIMESTAMP
    if _INDEX_CACHE is not None:
        return _INDEX_CACHE
    target = _resolve_output_path(path)
    if not target.exists():
        return None
    _INDEX_CACHE = EmbeddingIndex.load(path)
    _INDEX_CACHE_TIMESTAMP = time.time()
    return _INDEX_CACHE


def reset_cache() -> None:
    """Test helper to drop the cached index between runs."""
    global _INDEX_CACHE, _INDEX_CACHE_TIMESTAMP
    _INDEX_CACHE = None
    _INDEX_CACHE_TIMESTAMP = None


def build_index(
    kb_roots: tuple[str, ...] = DEFAULT_KB_ROOTS,
    *,
    embedding_model: str | None = None,
) -> EmbeddingIndex:
    """Walk knowledge-base markdown, embed each heading chunk, return an index.

    If AI/ML embeddings are not available, returns an empty index — callers
    fall back to keyword search in ``rag.retrieve``.
    """
    chunks = _collect_chunks(kb_roots)
    if not chunks:
        return EmbeddingIndex(chunks=[], vectors=[], embedding_model=embedding_model or "")
    if not aiml_available():
        # No live AI/ML — store chunks without vectors so the keyword fallback
        # is the only useful path.
        return EmbeddingIndex(chunks=chunks, vectors=[], embedding_model=embedding_model or "")

    vectors: list[list[float]] = []
    for batch_start in range(0, len(chunks), _EMBED_BATCH):
        batch = chunks[batch_start : batch_start + _EMBED_BATCH]
        texts = [_chunk_payload(c) for c in batch]
        embedded = aiml_embed(texts)
        if embedded is None or len(embedded) != len(texts):
            # Partial failure: we can't trust the rest. Bail out empty.
            return EmbeddingIndex(chunks=chunks, vectors=[], embedding_model=embedding_model or "")
        vectors.extend(embedded)

    from core.provider_config import load_provider_config

    model = embedding_model or load_provider_config().aiml_embedding_model
    return EmbeddingIndex(chunks=chunks, vectors=vectors, embedding_model=model)


def _collect_chunks(kb_roots: tuple[str, ...]) -> list[IndexedChunk]:
    seen_ids: set[str] = set()
    chunks: list[IndexedChunk] = []
    for kb_root in kb_roots:
        root = find_resource(kb_root)
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            for chunk in _chunk_markdown(path, root):
                if chunk.chunk_id in seen_ids:
                    continue
                seen_ids.add(chunk.chunk_id)
                chunks.append(chunk)
    return chunks


def _chunk_markdown(path: Path, kb_root: Path) -> list[IndexedChunk]:
    document_name = str(path.relative_to(kb_root))
    chunks: list[IndexedChunk] = []
    heading = "overview"
    body: list[str] = []

    def flush() -> None:
        text = "\n".join(body).strip()
        if text:
            chunks.append(
                IndexedChunk(
                    document_name=document_name,
                    chunk_id=f"{document_name}#{_slugify(heading) or 'section'}",
                    heading=heading,
                    text=text,
                )
            )

    for line in _strip_yaml_frontmatter(path.read_text(encoding="utf-8").splitlines()):
        if line.startswith("#"):
            flush()
            heading = line.lstrip("#").strip()
            body = []
        else:
            body.append(line)
    flush()
    return chunks


def _strip_yaml_frontmatter(lines: list[str]) -> list[str]:
    if not lines or lines[0].strip() != "---":
        return lines
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[i + 1 :]
    return lines


def _slugify(heading: str) -> str:
    return "-".join("".join(c for c in heading.lower() if c.isalnum() or c == " ").split())


def _chunk_payload(chunk: IndexedChunk) -> str:
    return f"{chunk.heading}\n{chunk.text}"[:2000]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def _resolve_output_path(path: str) -> Path:
    direct = Path(path)
    if direct.is_absolute():
        return direct
    return project_root() / path
