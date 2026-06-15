from agents.orchestrator import build_demo_state
from core.export import write_outputs


def main() -> None:
    state = build_demo_state()
    write_outputs(state)
    finalized = sum(1 for question in state.questions.values() if question.status == "finalized")
    print(f"Wrote {len(state.questions)} questions, {finalized} finalized demo answers, and {len(state.promise_ledger)} ledger entries.")


if __name__ == "__main__":
    main()
