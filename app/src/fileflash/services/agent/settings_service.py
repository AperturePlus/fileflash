from __future__ import annotations

from ...repositories import AgentSettingsRepository


class SettingsService:
    def __init__(self, *, settings_repo: AgentSettingsRepository) -> None:
        self.settings_repo = settings_repo

    async def get_settings(self, *args, **kwargs):
        raise NotImplementedError("Agent settings service is scaffolded only in this stage")

    async def upsert_settings(self, *args, **kwargs):
        raise NotImplementedError("Agent settings service is scaffolded only in this stage")
