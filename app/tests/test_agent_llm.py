from __future__ import annotations

from fileflash.core.settings import Settings


def test_settings_deepseek_defaults() -> None:
    settings = Settings(
        agent_llm_provider="deepseek",
        agent_llm_model="deepseek-chat",
        agent_llm_api_key="test-key",
        agent_llm_base_url="https://api.deepseek.com",
    )
    assert settings.agent_llm_provider == "deepseek"
    assert settings.agent_llm_model == "deepseek-chat"
    assert settings.agent_llm_base_url.startswith("https://api.deepseek.com")
