from agents.orchestrator import build_demo_state
from core.embeddings import build_index, reset_cache
from core.export import write_outputs


def main() -> None:
    # Build the RAG embedding index before deliberation so security/compliance
    # answers retrieve over fresh evidence. With a live AI/ML key this burns one
    # embedding call per knowledge-base chunk; deterministic mode is free.
    reset_cache()
    build_index().save()
    state = build_demo_state()
    write_outputs(state)
    finalized = sum(1 for question in state.questions.values() if question.status == "finalized")
    print(f"Wrote {len(state.questions)} questions, {finalized} finalized demo answers, and {len(state.promise_ledger)} ledger entries.")


if __name__ == "__main__":
    main()
