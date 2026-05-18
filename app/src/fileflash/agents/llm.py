from __future__ import annotations

from typing import Any

from ..core.settings import Settings


def build_chat_model(settings: Settings) -> Any | None:
    """Return a LangChain chat model when configured; otherwise None (use mock planner)."""
    api_key = (settings.agent_llm_api_key or "").strip()
    if not api_key:
        return None

    provider = (settings.agent_llm_provider or "deepseek").strip().lower()
    model = settings.agent_llm_model

    try:
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(model=model, api_key=api_key, temperature=0.2)
        if provider in {"openai", "azure_openai"}:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(model=model, api_key=api_key, temperature=0.2)
        if provider == "deepseek":
            from langchain_openai import ChatOpenAI

            base_url = (settings.agent_llm_base_url or "https://api.deepseek.com").rstrip("/")
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            return ChatOpenAI(
                model=model or "deepseek-chat",
                api_key=api_key,
                base_url=base_url,
                temperature=0.2,
            )
    except Exception:
        return None
    return None
