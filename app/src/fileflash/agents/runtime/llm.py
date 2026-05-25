from __future__ import annotations

import json
from typing import Any, Protocol

import anthropic
from anthropic import AsyncAnthropic

from ...core.errors import ApiError
from ...core.settings import Settings


class PlannerClient(Protocol):
    async def create_plan(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        reasoning_effort: str = "adaptive",
    ) -> dict[str, Any]: ...


class AnthropicPlannerClient:
    def __init__(self, *, settings: Settings, client: AsyncAnthropic | None = None) -> None:
        self.settings = settings
        self._client = client

    async def create_plan(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        reasoning_effort: str = "adaptive",
    ) -> dict[str, Any]:
        api_key = (self.settings.agent_llm_api_key or "").strip()
        if not api_key:
            raise ApiError(status_code=503, code=503, message="Agent LLM API key is not configured")

        request_kwargs: dict[str, Any] = {
            "model": self.settings.agent_llm_model,
            "max_tokens": min(max_tokens, 4096),
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "timeout": 60.0,
        }
        request_kwargs.update(_reasoning_params(reasoning_effort))
        try:
            message = await self._get_client(api_key).messages.create(**request_kwargs)
        except anthropic.APIStatusError as exc:
            raise ApiError(
                status_code=503,
                code=503,
                message="Agent LLM request failed",
                data={"status": exc.status_code, "details": _response_details(exc)},
            ) from exc
        except (
            anthropic.APIConnectionError,
            anthropic.APITimeoutError,
            anthropic.APIError,
        ) as exc:
            raise ApiError(
                status_code=503,
                code=503,
                message=f"Agent LLM request failed: {type(exc).__name__}",
            ) from exc

        text = _extract_text(message)
        parsed = _parse_json_text(text)
        usage = _usage_payload(message)
        if isinstance(usage, dict):
            parsed["_usage"] = usage
        return parsed

    def _get_client(self, api_key: str) -> AsyncAnthropic:
        if self._client is None:
            base_url = (self.settings.agent_llm_base_url or "").strip() or None
            self._client = AsyncAnthropic(
                api_key=api_key,
                base_url=base_url,
                timeout=60.0,
                max_retries=0,
            )
        return self._client


def _extract_text(message: Any) -> str:
    chunks = getattr(message, "content", None)
    if not isinstance(chunks, list):
        raise ApiError(status_code=502, code=502, message="Agent LLM returned an invalid response")
    parts: list[str] = []
    for chunk in chunks:
        if isinstance(chunk, dict):
            if chunk.get("type") == "text":
                parts.append(str(chunk.get("text") or ""))
            continue
        if getattr(chunk, "type", None) == "text":
            parts.append(str(getattr(chunk, "text", "") or ""))
    text = "\n".join(part for part in parts if part).strip()
    if not text:
        raise ApiError(status_code=502, code=502, message="Agent LLM returned an empty response")
    return text


def _usage_payload(message: Any) -> dict[str, Any] | None:
    usage = getattr(message, "usage", None)
    if usage is None:
        return None
    if isinstance(usage, dict):
        return usage
    if hasattr(usage, "model_dump"):
        dumped = usage.model_dump()
        return dumped if isinstance(dumped, dict) else None
    payload: dict[str, Any] = {}
    usage_token_fields = (
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    )
    for key in usage_token_fields:
        value = getattr(usage, key, None)
        if value is not None:
            payload[key] = value
    return payload or None


def _reasoning_params(reasoning_effort: str) -> dict[str, Any]:
    effort = (reasoning_effort or "adaptive").strip().lower()
    if effort == "adaptive":
        return {"thinking": {"type": "adaptive"}}
    if effort not in {"low", "medium", "high", "xhigh", "max"}:
        effort = "high"
    return {
        "thinking": {"type": "enabled"},
        "output_config": {"effort": effort},
    }


def _response_details(error: anthropic.APIStatusError) -> str:
    response = getattr(error, "response", None)
    text = getattr(response, "text", "") if response is not None else ""
    return str(text or "")[:800]


def _parse_json_text(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ApiError(
            status_code=502,
            code=502,
            message="Agent LLM did not return valid JSON",
        ) from exc
    if not isinstance(parsed, dict):
        raise ApiError(status_code=502, code=502, message="Agent LLM JSON must be an object")
    return parsed


__all__ = ["AnthropicPlannerClient", "PlannerClient"]
