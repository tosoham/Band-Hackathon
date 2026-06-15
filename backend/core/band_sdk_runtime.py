from dataclasses import dataclass
from pathlib import Path

import yaml

EXPECTED_BAND_AGENTS = [
    "intake_agent",
    "sales_engineer",
    "security_compliance",
    "product_capability",
    "legal_commitment_guard",
    "adversarial_reviewer",
]


@dataclass(frozen=True)
class BandAgentCredentialStatus:
    name: str
    agent_id_set: bool
    api_key_set: bool


def load_agent_config_shape(path: str = "agent_config.yaml") -> dict[str, dict[str, str]]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError("agent_config.yaml is missing. Copy agent_config.yaml.example and fill Band credentials.")
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def validate_band_agent_config(path: str = "agent_config.yaml") -> list[BandAgentCredentialStatus]:
    data = load_agent_config_shape(path)
    missing = [name for name in EXPECTED_BAND_AGENTS if name not in data]
    if missing:
        raise ValueError(f"Missing Band agents: {', '.join(missing)}")

    statuses: list[BandAgentCredentialStatus] = []
    for name in EXPECTED_BAND_AGENTS:
        agent_id = str(data[name].get("agent_id", ""))
        api_key = str(data[name].get("api_key", ""))
        if len(agent_id) < 32 or len(api_key) < 20:
            raise ValueError(f"{name} has incomplete Band credentials.")
        statuses.append(BandAgentCredentialStatus(name=name, agent_id_set=True, api_key_set=True))
    return statuses
