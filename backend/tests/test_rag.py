from core.rag import load_corpus, retrieve


def test_corpus_loads_chunks() -> None:
    corpus = load_corpus()
    assert len(corpus) > 0
    assert all(chunk.document_name.endswith(".md") for chunk in corpus)
    assert all("#" in chunk.chunk_id for chunk in corpus)


def test_retrieve_returns_cited_evidence() -> None:
    evidence = retrieve("Can you guarantee 99.9% uptime?", top_k=4)
    assert evidence, "expected at least one evidence hit for an SLA question"
    assert len(evidence) <= 4
    top = evidence[0]
    assert top.document_name
    assert top.quote
    assert 0.0 < top.confidence <= 1.0


def test_retrieve_is_ranked_by_confidence() -> None:
    evidence = retrieve("Do you maintain SOC 2 Type II certification?", top_k=4)
    confidences = [e.confidence for e in evidence]
    assert confidences == sorted(confidences, reverse=True)


def test_empty_query_returns_no_evidence() -> None:
    assert retrieve("   ", top_k=4) == []
