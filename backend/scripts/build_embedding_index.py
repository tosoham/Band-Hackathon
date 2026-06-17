"""Build the embedding-backed RAG index from the knowledge base.

Usage (from repo root):
    PYTHONPATH=backend python backend/scripts/build_embedding_index.py

Inside Docker:
    docker compose run --rm backend python scripts/build_embedding_index.py

The script is idempotent and safe to run repeatedly. It overwrites
``output/embedding_index.json`` with the latest vectors.
"""

from __future__ import annotations

import sys
import time

from core.embeddings import DEFAULT_INDEX_PATH, build_index, reset_cache
from core.model_clients import aiml_available
from core.provider_config import load_provider_config


def main(argv: list[str] | None = None) -> int:
    config = load_provider_config()
    print(f"[build-index] aiml_enabled={config.aiml_enabled} aiml_mode={config.aiml_mode} "
          f"model={config.aiml_embedding_model}")
    if not aiml_available():
        print("[build-index] AI/ML not available — index will be built empty; "
              "RAG will fall back to keyword search.")

    start = time.time()
    index = build_index()
    if not index.chunks:
        print("[build-index] no chunks found in knowledge_base/. Nothing to index.")
        return 1

    if not index.vectors:
        print(f"[build-index] indexed {len(index.chunks)} chunks WITHOUT vectors "
              "(embeddings failed or AI/ML disabled).")
    else:
        print(f"[build-index] embedded {len(index.chunks)} chunks "
              f"in {time.time() - start:.1f}s using {index.embedding_model}.")

    target = index.save(DEFAULT_INDEX_PATH)
    reset_cache()
    print(f"[build-index] wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
