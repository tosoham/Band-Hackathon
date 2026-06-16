import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from core.band_sdk_runtime import EXPECTED_BAND_AGENTS, validate_band_agent_config


def validate_config_shape() -> None:
    try:
        statuses = validate_band_agent_config()
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    for status in statuses:
        print(f"{status.name}: configured")


async def verify_live_connection(agent_name: str) -> None:
    try:
        from band import Agent
        from band.adapters.langgraph import LangGraphAdapter
        from band.config import load_agent_config
        from langchain_openai import ChatOpenAI
        from langgraph.checkpoint.memory import InMemorySaver
    except ImportError as exc:
        raise SystemExit(
            "Live Band verification requires SDK extras: install `band-sdk[langgraph]`, "
            "`langchain-openai`, and provider dependencies."
        ) from exc

    agent_id, api_key = load_agent_config(agent_name)
    featherless_base_url = os.getenv("FEATHERLESS_BASE_URL")
    featherless_model = os.getenv("BAND_VERIFY_MODEL") or os.getenv("FEATHERLESS_MODEL")
    featherless_api_key = os.getenv("FEATHERLESS_API_KEY")
    if not (featherless_base_url and featherless_model and featherless_api_key):
        raise SystemExit(
            "Live Band verification needs a live LLM adapter. AI/ML is disabled for this demo; "
            "set FEATHERLESS_BASE_URL, FEATHERLESS_MODEL, and FEATHERLESS_API_KEY to use Featherless."
        )

    adapter = LangGraphAdapter(
        llm=ChatOpenAI(
            model=featherless_model,
            api_key=featherless_api_key,
            base_url=featherless_base_url,
        ),
        checkpointer=InMemorySaver(),
        custom_section=f"You are the BandGate {agent_name.replace('_', ' ')}.",
    )
    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=os.getenv("THENVOI_WS_URL"),
        rest_url=os.getenv("THENVOI_REST_URL"),
    )
    await agent.start()
    print(f"{agent_name}: connected as {getattr(agent, 'agent_name', 'remote-agent')}")
    await agent.stop()


async def main() -> None:
    validate_config_shape()
    if os.getenv("BAND_VERIFY_LIVE", "false").lower() == "true":
        for agent_name in EXPECTED_BAND_AGENTS:
            await verify_live_connection(agent_name)


if __name__ == "__main__":
    asyncio.run(main())
