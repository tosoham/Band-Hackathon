"""Retrieval over the BandGate knowledge base.

The primary path is embedding-backed: AI/ML API embeds the query, the
in-memory ``EmbeddingIndex`` returns cosine top-N, and AI/ML reranks down to
``top_k``. If embeddings, the index, or the reranker fail for any reason
(quota exhaustion, network blip, missing index file, AI/ML disabled), this
module falls back to the original deterministic keyword overlap so the demo
never breaks.

The Day-2 keyword search is preserved here verbatim for that fallback.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from core.embeddings import get_index, IndexedChunk
from core.model_clients import aiml_rerank
from core.paths import find_resource
from core.schemas import Evidence

DEFAULT_KB_ROOT = "knowledge_base"

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "do", "does", "you", "your", "we", "our", "can", "will",
    "all", "any", "how", "what", "who", "be", "as", "at", "it", "this",
    "that", "have", "has", "not", "provide", "describe", "currently",
}


@dataclass(frozen=True)
class Chunk:
    document_name: str
    chunk_id: str
    heading: str
    text: str


def _tokenize(text: str) -> set[str]:
    cleaned = "".join(c.lower() if c.isalnum() or c == "." else " " for c in text)
    return {tok for tok in cleaned.split() if tok and tok not in _STOPWORDS}


def _slugify(heading: str) -> str:
    return "-".join("".join(c for c in heading.lower() if c.isalnum() or c == " ").split())


def _chunk_markdown(path: Path, kb_root: Path) -> list[Chunk]:
    document_name = str(path.relative_to(kb_root))
    chunks: list[Chunk] = []
    heading = "overview"
    body: list[str] = []

    def flush() -> None:
        text = "\n".join(body).strip()
        if text:
            chunks.append(
                Chunk(
                    document_name=document_name,
                    chunk_id=f"{document_name}#{_slugify(heading) or 'section'}",
                    heading=heading,
                    text=text,
                )
            )

    raw_lines = path.read_text(encoding="utf-8").splitlines()
    for line in _strip_yaml_frontmatter(raw_lines):
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


@lru_cache(maxsize=8)
def load_corpus(kb_root: str = DEFAULT_KB_ROOT) -> tuple[Chunk, ...]:
    root = find_resource(kb_root)
    if not root.is_dir():
        print(f"[rag] knowledge base not found at '{kb_root}'; retrieval will be empty")
        return ()
    chunks: list[Chunk] = []
    for path in sorted(root.rglob("*.md")):
        chunks.extend(_chunk_markdown(path, root))
    if not chunks:
        print(f"[rag] knowledge base '{kb_root}' contains no markdown chunks")
    return tuple(chunks)


def retrieve(query: str, top_k: int = 4, kb_root: str = DEFAULT_KB_ROOT) -> list[Evidence]:
    """Return the top_k knowledge-base chunks most relevant to ``query``.

    Embedding-first; keyword-overlap fallback when AI/ML is unavailable.
    """
    if not query or not query.strip():
        return []
    embedding_hits = _retrieve_via_embeddings(query, top_k=top_k)
    if embedding_hits:
        return embedding_hits
    return _retrieve_via_keywords(query, top_k=top_k, kb_root=kb_root)


def _retrieve_via_embeddings(query: str, *, top_k: int) -> list[Evidence]:
    index = get_index()
    if index is None or not index.ready:
        return []
    candidates = index.search(query, top_k=max(top_k * 5, 20))
    if not candidates:
        return []
    rerank_inputs = [f"{c.chunk.heading}\n{c.chunk.text}" for c in candidates]
    order = aiml_rerank(query, rerank_inputs, top_k=top_k)
    if order is None:
        # Cosine ranking is still meaningful; just take top_k as-is.
        order = list(range(min(top_k, len(candidates))))
    evidence: list[Evidence] = []
    for rank, idx in enumerate(order):
        candidate = candidates[idx]
        evidence.append(
            Evidence(
                source_id=f"kb-{rank + 1}",
                document_name=candidate.chunk.document_name,
                chunk_id=candidate.chunk.chunk_id,
                quote=_best_quote_from_indexed(candidate.chunk),
                confidence=round(min(1.0, max(0.0, candidate.score)), 2),
            )
        )
    return evidence


def _retrieve_via_keywords(query: str, *, top_k: int, kb_root: str) -> list[Evidence]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scored: list[tuple[float, Chunk]] = []
    for chunk in load_corpus(kb_root):
        overlap = query_tokens & _tokenize(f"{chunk.heading} {chunk.text}")
        if overlap:
            scored.append((len(overlap) / len(query_tokens), chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    evidence: list[Evidence] = []
    for rank, (score, chunk) in enumerate(scored[:top_k]):
        evidence.append(
            Evidence(
                source_id=f"kb-{rank + 1}",
                document_name=chunk.document_name,
                chunk_id=chunk.chunk_id,
                quote=_best_quote(chunk),
                confidence=round(min(1.0, score), 2),
            )
        )
    return evidence


def _best_quote(chunk: Chunk) -> str:
    """Prefer the approved-wording line when present; otherwise the first sentence."""
    lines = [line.strip() for line in chunk.text.splitlines() if line.strip()]
    if chunk.heading.lower().startswith("approved") and lines:
        return lines[0]
    body = " ".join(lines)
    return body[:240].strip()


def _best_quote_from_indexed(chunk: IndexedChunk) -> str:
    lines = [line.strip() for line in chunk.text.splitlines() if line.strip()]
    if chunk.heading.lower().startswith("approved") and lines:
        return lines[0]
    body = " ".join(lines)
    return body[:240].strip()
