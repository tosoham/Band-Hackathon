from typing import Any

import yaml

from core.paths import find_resource


def load_commitment_policy(path: str = "knowledge_base/policies/commitment_policy.yaml") -> dict[str, Any]:
    return yaml.safe_load(find_resource(path).read_text(encoding="utf-8"))
