from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import anthropic
from anthropic import AsyncAnthropic

from ...core.errors import ApiError
from ...core.settings import Settings

ToolExecutor = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]
logger = logging.getLogger(__name__)


class PlannerClient(Protocol):
    async def create_plan(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        reasoning_effort: str = "adaptive",
        tools: list[dict[str, Any]] | None = None,
        tool_executor: ToolExecutor | None = None,
        max_tool_roundtrips: int = 4,
    ) -> dict[str, Any]: ...


class AnswerClient(Protocol):
    async def create_answer(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        reasoning_effort: str = "adaptive",
    ) -> str: ...


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
        tools: list[dict[str, Any]] | None = None,
        tool_executor: ToolExecutor | None = None,
        max_tool_roundtrips: int = 4,
    ) -> dict[str, Any]:
        api_key = (self.settings.agent_llm_api_key or "").strip()
        if not api_key:
            raise ApiError(status_code=503, code=503, message="Agent LLM API key is not configured")
        plan_token_cap = _safe_plan_token_cap(self.settings)

        request_kwargs: dict[str, Any] = {
            "model": self.settings.agent_llm_model,
            "max_tokens": min(max_tokens, plan_token_cap),
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "timeout": 60.0,
        }
        tool_name_map = _tool_name_map(tools or [])
        if tools:
            request_kwargs["tools"] = _anthropic_tools_payload(tools)
            request_kwargs["tool_choice"] = {"type": "auto"}
        request_kwargs.update(_reasoning_params(reasoning_effort))

        try:
            parsed, usage = await self._request_and_parse_plan(
                api_key=api_key,
                request_kwargs=request_kwargs,
                tool_name_map=tool_name_map,
                tool_executor=tool_executor,
                max_tool_roundtrips=max_tool_roundtrips,
            )
        except ApiError as first_error:
            if not _is_retryable_output_error(first_error):
                raise
            logger.warning(
                "Planner LLM retrying attempt=%s reason=%s degraded=%s jsonOnly=%s",
                2,
                first_error.message,
                True,
                False,
            )
            degraded_kwargs = _degraded_plan_request_kwargs(request_kwargs)
            try:
                parsed, usage = await self._request_and_parse_plan(
                    api_key=api_key,
                    request_kwargs=degraded_kwargs,
                    tool_name_map=tool_name_map,
                    tool_executor=tool_executor,
                    max_tool_roundtrips=max_tool_roundtrips,
                )
            except ApiError as second_error:
                if not _is_retryable_output_error(second_error):
                    raise
                logger.warning(
                    "Planner LLM retrying attempt=%s reason=%s degraded=%s jsonOnly=%s",
                    3,
                    second_error.message,
                    True,
                    True,
                )
                strict_kwargs = _strict_json_retry_kwargs(
                    degraded_kwargs,
                    max_tokens_cap=plan_token_cap,
                )
                parsed, usage = await self._request_and_parse_plan(
                    api_key=api_key,
                    request_kwargs=strict_kwargs,
                    tool_name_map=tool_name_map,
                    tool_executor=tool_executor,
                    max_tool_roundtrips=max_tool_roundtrips,
                )
        if isinstance(usage, dict):
            parsed["_usage"] = usage
        return parsed

    async def create_answer(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        reasoning_effort: str = "adaptive",
    ) -> str:
        api_key = (self.settings.agent_llm_api_key or "").strip()
        if not api_key:
            raise ApiError(status_code=503, code=503, message="Agent LLM API key is not configured")
        request_kwargs: dict[str, Any] = {
            "model": self.settings.agent_llm_model,
            "max_tokens": min(max_tokens, 1024),
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "timeout": 60.0,
        }
        request_kwargs.update(_reasoning_params(reasoning_effort))
        message = await self._request_plan(api_key=api_key, request_kwargs=request_kwargs)
        try:
            return _extract_text(message)
        except ApiError as exc:
            if not _is_retryable_output_error(exc):
                raise
            degraded_kwargs = dict(request_kwargs)
            degraded_kwargs.pop("thinking", None)
            degraded_kwargs.pop("output_config", None)
            message = await self._request_plan(api_key=api_key, request_kwargs=degraded_kwargs)
            return _extract_text(message)

    async def _request_plan(self, *, api_key: str, request_kwargs: dict[str, Any]) -> Any:
        try:
            return await self._get_client(api_key).messages.create(**request_kwargs)
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

    async def _parse_plan_response(
        self,
        *,
        api_key: str,
        request_kwargs: dict[str, Any],
        message: Any,
        tool_name_map: dict[str, str],
        tool_executor: ToolExecutor | None,
        max_tool_roundtrips: int,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        if tool_executor is None:
            return _parse_plan_message(message, tool_name_map=tool_name_map)
        tool_calls = _extract_tool_use_calls(message=message, tool_name_map=tool_name_map)
        if not tool_calls:
            return _parse_plan_message(message, tool_name_map=tool_name_map)
        return await self._run_tool_loop(
            api_key=api_key,
            request_kwargs=request_kwargs,
            initial_message=message,
            tool_name_map=tool_name_map,
            tool_executor=tool_executor,
            max_tool_roundtrips=max_tool_roundtrips,
        )

    async def _request_and_parse_plan(
        self,
        *,
        api_key: str,
        request_kwargs: dict[str, Any],
        tool_name_map: dict[str, str],
        tool_executor: ToolExecutor | None,
        max_tool_roundtrips: int,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        message = await self._request_plan(api_key=api_key, request_kwargs=request_kwargs)
        return await self._parse_plan_response(
            api_key=api_key,
            request_kwargs=request_kwargs,
            message=message,
            tool_name_map=tool_name_map,
            tool_executor=tool_executor,
            max_tool_roundtrips=max_tool_roundtrips,
        )

    async def _run_tool_loop(
        self,
        *,
        api_key: str,
        request_kwargs: dict[str, Any],
        initial_message: Any,
        tool_name_map: dict[str, str],
        tool_executor: ToolExecutor,
        max_tool_roundtrips: int,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        max_rounds = max(1, min(int(max_tool_roundtrips or 0), 12))
        base_messages = request_kwargs.get("messages")
        if not isinstance(base_messages, list):
            raise ApiError(status_code=502, code=502, message="Agent LLM returned an invalid response")
        messages: list[dict[str, Any]] = list(base_messages)
        usage_total: dict[str, int] = {}
        current_message = initial_message

        for _ in range(max_rounds):
            usage_total = _merge_usage_totals(usage_total, _usage_payload(current_message))
            tool_calls = _extract_tool_use_calls(message=current_message, tool_name_map=tool_name_map)
            if not tool_calls:
                parsed, _ = _parse_plan_message(current_message, tool_name_map=tool_name_map)
                return parsed, usage_total or None

            assistant_content = _content_block_mappings(current_message)
            if assistant_content:
                messages.append({"role": "assistant", "content": assistant_content})
            tool_results: list[dict[str, Any]] = []
            for call in tool_calls:
                tool_output = await tool_executor(call["tool"], call["input"])
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call["id"],
                        "content": _tool_result_content(tool_output),
                    }
                )
            messages.append({"role": "user", "content": tool_results})
            loop_kwargs = dict(request_kwargs)
            loop_kwargs["messages"] = messages
            current_message = await self._request_plan(api_key=api_key, request_kwargs=loop_kwargs)

        raise ApiError(
            status_code=502,
            code=502,
            message="Agent LLM exceeded planning tool rounds",
        )


def _extract_text(message: Any) -> str:
    chunks = getattr(message, "content", None)
    if isinstance(chunks, str):
        text = chunks.strip()
        if text:
            return text
        raise ApiError(status_code=502, code=502, message="Agent LLM returned an empty response")
    if not isinstance(chunks, list):
        raise ApiError(status_code=502, code=502, message="Agent LLM returned an invalid response")
    parts: list[str] = []
    for chunk in chunks:
        parts.extend(_extract_text_parts(chunk))
    text = "\n".join(part for part in parts if part).strip()
    if not text:
        raise ApiError(status_code=502, code=502, message="Agent LLM returned an empty response")
    return text


def _content_block_mappings(message: Any) -> list[dict[str, Any]]:
    chunks = getattr(message, "content", None)
    if isinstance(chunks, str):
        return [{"type": "text", "text": chunks}]
    if not isinstance(chunks, list):
        return []
    blocks: list[dict[str, Any]] = []
    for chunk in chunks:
        if isinstance(chunk, dict):
            blocks.append(chunk)
            continue
        if hasattr(chunk, "model_dump"):
            dumped = chunk.model_dump()
            if isinstance(dumped, dict):
                blocks.append(dumped)
                continue
        blocks.append(
            {
                "type": getattr(chunk, "type", None),
                "text": getattr(chunk, "text", None),
                "name": getattr(chunk, "name", None),
                "input": getattr(chunk, "input", None),
                "id": getattr(chunk, "id", None),
            }
        )
    return blocks


def _extract_tool_use_payload(
    message: Any,
    *,
    tool_name_map: dict[str, str],
) -> tuple[list[dict[str, Any]], str | None]:
    actions: list[dict[str, Any]] = []
    text_parts: list[str] = []
    for block in _content_block_mappings(message):
        block_type = str(block.get("type") or "")
        if block_type == "tool_use":
            provider_name = str(block.get("name") or "").strip()
            action_input = _coerce_mapping(block.get("input"))
            actions.append(
                {
                    "step": len(actions) + 1,
                    "tool": tool_name_map.get(provider_name, provider_name),
                    "input": action_input,
                }
            )
            continue
        text_parts.extend(_extract_text_parts_from_mapping(block))
    summary = "\n".join(part for part in text_parts if part).strip()
    return actions, summary or None


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        if isinstance(dumped, dict):
            return dumped
    return {}


def _extract_text_parts(chunk: Any) -> list[str]:
    if chunk is None:
        return []
    if isinstance(chunk, str):
        candidate = chunk.strip()
        return [candidate] if candidate else []
    if isinstance(chunk, dict):
        return _extract_text_parts_from_mapping(chunk)
    if hasattr(chunk, "model_dump"):
        dumped = chunk.model_dump()
        if isinstance(dumped, dict):
            return _extract_text_parts_from_mapping(dumped)
    return _extract_text_parts_from_mapping(
        {
            "type": getattr(chunk, "type", None),
            "text": getattr(chunk, "text", None),
            "output_text": getattr(chunk, "output_text", None),
            "content": getattr(chunk, "content", None),
        }
    )


def _extract_text_parts_from_mapping(payload: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if payload.get("type") == "text":
        out.extend(_flatten_text_value(payload.get("text")))
    for key in ("text", "output_text", "content"):
        out.extend(_flatten_text_value(payload.get(key)))
    deduped: list[str] = []
    seen: set[str] = set()
    for item in out:
        if not item or item in seen:
            continue
        deduped.append(item)
        seen.add(item)
    return deduped


def _flatten_text_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidate = value.strip()
        return [candidate] if candidate else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_flatten_text_value(item))
        return out
    if isinstance(value, dict):
        if value.get("type") == "text":
            return _flatten_text_value(value.get("text"))
        if "text" in value:
            return _flatten_text_value(value.get("text"))
        return []
    return []


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


def _merge_usage_totals(base: dict[str, int], extra: dict[str, Any] | None) -> dict[str, int]:
    merged = dict(base)
    if not isinstance(extra, dict):
        return merged
    for key in (
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    ):
        value = extra.get(key)
        if value is None:
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        merged[key] = int(merged.get(key) or 0) + parsed
    return merged


def _tool_result_content(payload: dict[str, Any]) -> list[dict[str, str]]:
    text = json.dumps(payload, ensure_ascii=False)
    if len(text) > 12_000:
        text = text[:12_000] + "…"
    return [{"type": "text", "text": text}]


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


def _parse_plan_message(
    message: Any,
    *,
    tool_name_map: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    tool_actions, summary = _extract_tool_use_payload(
        message,
        tool_name_map=tool_name_map or {},
    )
    usage = _usage_payload(message)
    if tool_actions:
        return {
            "summary": summary or f"Prepared {len(tool_actions)} file action(s).",
            "proposedActions": tool_actions,
        }, usage
    text = _extract_text(message)
    parsed = _parse_json_text(text)
    return parsed, usage


def _extract_tool_use_calls(
    message: Any,
    *,
    tool_name_map: dict[str, str],
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for block in _content_block_mappings(message):
        if str(block.get("type") or "") != "tool_use":
            continue
        provider_name = str(block.get("name") or "").strip()
        if not provider_name:
            continue
        tool_use_id = str(block.get("id") or "").strip()
        if not tool_use_id:
            tool_use_id = f"tool_use_{len(calls) + 1}"
        calls.append(
            {
                "id": tool_use_id,
                "tool": tool_name_map.get(provider_name, provider_name),
                "input": _coerce_mapping(block.get("input")),
            }
        )
    return calls


def _tool_name_map(tools: list[dict[str, Any]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for tool in tools:
        provider_name = str(tool.get("name") or "").strip()
        if not provider_name:
            continue
        internal_name = str(
            tool.get("internalName")
            or tool.get("internal_name")
            or tool.get("tool")
            or provider_name
        ).strip()
        mapping[provider_name] = internal_name or provider_name
    return mapping


def _anthropic_tools_payload(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for tool in tools:
        name = str(tool.get("name") or "").strip()
        if not name:
            continue
        payload.append(
            {
                "name": name,
                "description": str(tool.get("description") or ""),
                "input_schema": dict(tool.get("input_schema") or {"type": "object"}),
            }
        )
    return payload


def _is_retryable_output_error(error: ApiError) -> bool:
    if error.status_code != 502:
        return False
    return error.message in {
        "Agent LLM returned an invalid response",
        "Agent LLM returned an empty response",
        "Agent LLM did not return valid JSON",
        "Agent LLM JSON must be an object",
    }


def _safe_plan_token_cap(settings: Settings) -> int:
    raw_value = getattr(settings, "agent_llm_plan_max_tokens", 8192)
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return 8192
    return max(1, parsed)


def _degraded_plan_request_kwargs(request_kwargs: dict[str, Any]) -> dict[str, Any]:
    degraded_kwargs = dict(request_kwargs)
    degraded_kwargs.pop("thinking", None)
    degraded_kwargs.pop("output_config", None)
    return degraded_kwargs


def _strict_json_retry_kwargs(
    request_kwargs: dict[str, Any],
    *,
    max_tokens_cap: int,
) -> dict[str, Any]:
    strict_kwargs = dict(request_kwargs)
    strict_kwargs["max_tokens"] = max(1, int(max_tokens_cap))
    messages = request_kwargs.get("messages")
    strict_kwargs["messages"] = _append_json_only_retry_instruction(messages)
    return strict_kwargs


def _append_json_only_retry_instruction(messages: Any) -> list[dict[str, Any]]:
    instruction = (
        "Return ONLY one valid JSON object that matches outputSchema. "
        "Do not include markdown fences, prose, or extra text."
    )
    if not isinstance(messages, list):
        return [{"role": "user", "content": instruction}]
    cloned: list[dict[str, Any]] = []
    for item in messages:
        if isinstance(item, dict):
            cloned.append(dict(item))
    for idx in range(len(cloned) - 1, -1, -1):
        if cloned[idx].get("role") != "user":
            continue
        content = cloned[idx].get("content")
        if isinstance(content, str):
            merged = content.rstrip()
            if merged:
                merged = f"{merged}\n\n{instruction}"
            else:
                merged = instruction
            cloned[idx]["content"] = merged
            return cloned
    cloned.append({"role": "user", "content": instruction})
    return cloned


def _parse_json_text(text: str) -> dict[str, Any]:
    candidate = _strip_code_fences(text)
    try:
        return _decode_json_object(candidate)
    except ApiError:
        raise
    except json.JSONDecodeError as decode_error:
        extracted = _extract_balanced_json_object(candidate)
        if extracted is not None:
            try:
                return _decode_json_object(extracted)
            except ApiError:
                raise
            except json.JSONDecodeError:
                pass
        raise ApiError(
            status_code=502,
            code=502,
            message="Agent LLM did not return valid JSON",
        ) from decode_error


def _decode_json_object(candidate: str) -> dict[str, Any]:
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ApiError(status_code=502, code=502, message="Agent LLM JSON must be an object")
    return parsed


def _strip_code_fences(text: str) -> str:
    candidate = text.strip()
    if not candidate.startswith("```"):
        return candidate
    lines = candidate.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_balanced_json_object(text: str) -> str | None:
    start = -1
    depth = 0
    in_string = False
    escaped = False
    for idx, ch in enumerate(text):
        if start < 0:
            if ch == "{":
                start = idx
                depth = 1
                in_string = False
                escaped = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
            continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
            if depth < 0:
                start = -1
                depth = 0
    return None


__all__ = ["AnswerClient", "AnthropicPlannerClient", "PlannerClient", "ToolExecutor"]
