import subprocess
import sys


COMMANDS: list[tuple[str, list[str]]] = [
    ("docker build", ["docker", "compose", "build", "backend", "frontend"]),
    (
        "backend tests",
        [
            "docker",
            "compose",
            "run",
            "--rm",
            "-e",
            "AIML_ENABLED=false",
            "-e",
            "FEATHERLESS_MODE=mock",
            "backend",
            "pytest",
        ],
    ),
    (
        "demo export",
        [
            "docker",
            "compose",
            "run",
            "--rm",
            "-e",
            "AIML_MODE=mock",
            "-e",
            "FEATHERLESS_MODE=mock",
            "backend",
            "python",
            "run_demo.py",
        ],
    ),
    (
        "six-agent collaboration report",
        [
            "docker",
            "compose",
            "run",
            "--rm",
            "-e",
            "BAND_COLLAB_SALES_LIMIT=0",
            "-e",
            "BAND_COLLAB_INTAKE_RISK_LIMIT=0",
            "-e",
            "BAND_COLLAB_REPORT_LIMIT=0",
            "-e",
            "AIML_MODE=mock",
            "-e",
            "FEATHERLESS_MODE=mock",
            "backend",
            "python",
            "scripts/run_band_collaboration.py",
        ],
    ),
    (
        "hardening report",
        [
            "docker",
            "compose",
            "run",
            "--rm",
            "-e",
            "AIML_MODE=mock",
            "-e",
            "FEATHERLESS_MODE=mock",
            "backend",
            "python",
            "scripts/run_hardening_suite.py",
        ],
    ),
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
