from scripts.final_demo_check import COMMANDS


def test_final_demo_check_command_order() -> None:
    labels = [label for label, _command in COMMANDS]

    assert labels == [
        "docker build",
        "backend tests",
        "demo export",
        "six-agent collaboration report",
        "hardening report",
        "frontend build",
    ]
