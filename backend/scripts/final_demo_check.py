import subprocess
import sys


COMMANDS: list[tuple[str, list[str]]] = [
    ("backend tests", ["docker", "compose", "run", "--rm", "backend", "pytest"]),
    ("demo export", ["docker", "compose", "run", "--rm", "backend", "python", "run_demo.py"]),
    ("frontend build", ["docker", "compose", "run", "--rm", "frontend", "npm", "run", "build"]),
]


def main() -> None:
    for label, command in COMMANDS:
        print(f"[final-demo-check] running {label}: {' '.join(command)}")
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            raise SystemExit(f"[final-demo-check] failed during {label}")
    print("[final-demo-check] all checks passed")


if __name__ == "__main__":
    main()
