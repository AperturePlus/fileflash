from __future__ import annotations

from ...repositories import AgentActionLogRepository, AgentWorkSessionRepository


class SessionService:
    def __init__(
        self,
        *,
        action_logs: AgentActionLogRepository,
        work_sessions: AgentWorkSessionRepository,
    ) -> None:
        self.action_logs = action_logs
        self.work_sessions = work_sessions

    async def get_work_session(self, *args, **kwargs):
        raise NotImplementedError("Agent session service is scaffolded only in this stage")

    async def update_checkpoint(self, *args, **kwargs):
        raise NotImplementedError("Agent session service is scaffolded only in this stage")
