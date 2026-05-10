from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import AgentUserSetting


class AgentSettingsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_user_id(self, user_id: int) -> AgentUserSetting | None:
        return await self.db.scalar(select(AgentUserSetting).where(AgentUserSetting.user_id == user_id))

    async def upsert_for_user(self, *, user_id: int, values: dict[str, Any]) -> AgentUserSetting:
        setting = await self.get_by_user_id(user_id)
        if setting is None:
            setting = AgentUserSetting(user_id=user_id, **values)
            self.db.add(setting)
        else:
            for key, value in values.items():
                setattr(setting, key, value)
        await self.db.flush()
        return setting
