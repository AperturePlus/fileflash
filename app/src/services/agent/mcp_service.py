from __future__ import annotations

from ...repositories import AgentMcpRepository


class McpService:
    def __init__(self, *, mcp: AgentMcpRepository) -> None:
        self.mcp = mcp

    async def list_mcp_servers(self, *args, **kwargs):
        raise NotImplementedError("Agent MCP service is scaffolded only in this stage")
