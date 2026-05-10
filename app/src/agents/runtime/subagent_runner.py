from __future__ import annotations


class SubagentRunner:
    async def dispatch(self, *args, **kwargs):
        raise NotImplementedError("SubagentRunner is scaffolded only in this stage")
