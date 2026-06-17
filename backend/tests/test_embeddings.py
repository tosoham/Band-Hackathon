from pathlib import Path

import pytest

from core import embeddings


@pytest.fixture
def fake_kb(tmp_path: Path) -> Path:
    root = tmp_path / "kb"
    root.mkdir()
    (root / "a.md").write_text(
        "# Encryption\nApproved Wording: data is encrypted with AES-256-GCM at rest.\n"
        "# Logging\nApproved Wording: audit logs retained 365 days.\n",
        encoding="utf-8",
    )
    return root


def test_index_saves_and_loads_round_trip(tmp_path: Path) -> None:
    chunks = [
        embeddings.IndexedChunk(
            document_name="security.md",
            chunk_id="security.md#encryption",
            heading="Encryption",
            text="AES-256-GCM at rest.",
        )
    ]
    index = embeddings.EmbeddingIndex(chunks=chunks, vectors=[[0.1, 0.2, 0.3]], embedding_model="test")
    out = index.save(str(tmp_path / "index.json"))
    assert out.exists()

    loaded = embeddings.EmbeddingIndex.load(str(tmp_path / "index.json"))
    assert loaded is not None
    assert loaded.chunks[0].chunk_id == "security.md#encryption"
    assert loaded.vectors[0] == [0.1, 0.2, 0.3]


def test_search_returns_empty_when_query_embed_fails(monkeypatch) -> None:
    chunks = [
        embeddings.IndexedChunk(
            document_name="d.md", chunk_id="d.md#a", heading="A", text="x"
        )
    ]
    index = embeddings.EmbeddingIndex(chunks=chunks, vectors=[[1.0, 0.0]], embedding_model="test")
    monkeypatch.setattr(embeddings, "aiml_embed", lambda texts: None)
    assert index.search("anything") == []


def test_build_index_without_aiml_returns_chunks_without_vectors(monkeypatch, fake_kb: Path) -> None:
    monkeypatch.setattr(embeddings, "aiml_available", lambda: False)
    monkeypatch.setattr(embeddings, "find_resource", lambda _: fake_kb)
    index = embeddings.build_index(kb_roots=("kb",))
    assert len(index.chunks) == 2
    assert index.vectors == []


def test_build_index_uses_embeddings_when_available(monkeypatch, fake_kb: Path) -> None:
    captured: list[list[str]] = []

    def fake_embed(texts: list[str]) -> list[list[float]]:
        captured.append(list(texts))
        return [[float(i + 1)] * 4 for i, _ in enumerate(texts)]

    monkeypatch.setattr(embeddings, "aiml_available", lambda: True)
    monkeypatch.setattr(embeddings, "aiml_embed", fake_embed)
    monkeypatch.setattr(embeddings, "find_resource", lambda _: fake_kb)
    index = embeddings.build_index(kb_roots=("kb",))
    assert len(index.chunks) == 2
    assert len(index.vectors) == 2
    assert all(len(v) == 4 for v in index.vectors)
    assert captured  # at least one call made
