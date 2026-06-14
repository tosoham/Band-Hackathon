from pathlib import Path
from typing import Any

import yaml


def load_commitment_policy(path: str = "knowledge_base/policies/commitment_policy.yaml") -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
