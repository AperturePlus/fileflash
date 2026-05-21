from __future__ import annotations

from ...repositories import AgentMemoryRepository


class MemoryService:
    def __init__(self, *, memory: AgentMemoryRepository) -> None:
        self.memory = memory

    async def list_memory(self, *args, **kwargs):
        raise NotImplementedError("Agent memory service is scaffolded only in this stage")

    async def search_memory(self, *args, **kwargs):
        raise NotImplementedError("Agent memory service is scaffolded only in this stage")
