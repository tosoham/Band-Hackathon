import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.model_clients import aiml_chat_json, featherless_chat_json, reset_provider_call_counts
from core.provider_config import load_provider_config


def _load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _probe_aiml() -> None:
    result = aiml_chat_json(
        system="Return only JSON: {\"ok\": boolean, \"provider\": \"aiml\"}.",
        user="Provider smoke test for BandGate. No customer data.",
        max_tokens=60,
        timeout=20,
        task="aiml_probe",
    )
    print(f"aiml_probe: {'ok' if result and result.get('ok') is True else 'fallback'}")


def _probe_featherless() -> None:
    result = featherless_chat_json(
        system="Return only JSON: {\"ok\": boolean, \"provider\": \"featherless\"}.",
        user="Provider smoke test for BandGate. No customer data.",
        max_tokens=60,
        timeout=25,
        task="featherless_probe",
    )
    print(f"featherless_probe: {'ok' if result and result.get('ok') is True else 'fallback'}")


def main() -> None:
    _load_dotenv()
    reset_provider_call_counts()
    config = load_provider_config()
    print(
        "provider_config: "
        f"aiml_mode={config.aiml_mode}, aiml_enabled={config.aiml_enabled}, "
        f"aiml_model={config.aiml_model}, "
        f"featherless_mode={config.featherless_mode}, featherless_model={config.featherless_model}"
    )
    _probe_aiml()
    _probe_featherless()


if __name__ == "__main__":
    main()
