from pathlib import Path

from agents.intake import build_initial_state


def main() -> None:
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    state = build_initial_state()
    (output_dir / "state.json").write_text(state.model_dump_json(indent=2), encoding="utf-8")
    print(f"Wrote {len(state.questions)} questions to output/state.json")


if __name__ == "__main__":
    main()
