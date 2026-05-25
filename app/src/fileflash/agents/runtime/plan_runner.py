from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...core.mime import resolve_file_mime_type
from ...core.settings import Settings, get_settings
from ...models import AgentPlan, AgentSkill, BackgroundJob, File, Folder
from ...models.enums import AgentExecutionPolicy as DbAgentExecutionPolicy
from ...models.enums import FileStatus, FolderStatus, FolderType
from ...repositories import AgentSkillRepository
from ...repositories.agent.contracts import AgentSkillCatalogEntry
from ...schemas.agent import (
    AgentChosenSkill,
    AgentCostEstimate,
    AgentPlanResult,
    AgentProposedAction,
    PlanAgentRequest,
)
from ..harness.policy import classify_tool_side_effect, normalize_action_risk
from .llm import AnthropicPlannerClient, PlannerClient
from .reference_rules import is_symbolic_id_placeholder, parse_step_reference

DEFAULT_AGENT_TOOLS = (
    "drive.listFolder",
    "drive.createFolder",
    "drive.moveFile",
    "drive.moveFolder",
    "drive.renameFile",
    "drive.renameFolder",
    "drive.deleteFile",
    "drive.deleteFolder",
)


class PlanRunner:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        planner_client: PlannerClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.planner_client = planner_client or AnthropicPlannerClient(settings=self.settings)

    async def run(self, *, db: AsyncSession, job: BackgroundJob) -> AgentPlanResult:
        if job.requested_by is None:
            raise ApiError(status_code=400, code=400, message="Agent job is missing requestedBy")

        request = PlanAgentRequest.model_validate(dict(job.payload or {}))
        user_id = int(job.requested_by)
        skill = await _choose_skill(
            db,
            user_id=user_id,
            task_input=request.input,
            prefer_skill_id=request.hints.prefer_skill_id,
        )
        metadata = await _collect_context_metadata(db, user_id=user_id, request=request)
        allowed_tools = _skill_tool_whitelist(skill)
        llm_payload = await self.planner_client.create_plan(
            system_prompt=_system_prompt(),
            user_prompt=_user_prompt(
                request=request,
                skill=skill,
                allowed_tools=allowed_tools,
                metadata=metadata,
            ),
            max_tokens=request.hints.budget_tokens,
            reasoning_effort=request.hints.reasoning_effort,
        )

        actions = _normalize_actions(
            llm_payload=llm_payload,
            allowed_tools=allowed_tools,
            max_steps=min(request.hints.max_steps, self.settings.agent_job_max_tool_calls),
        )
        chosen_skill = _chosen_skill(skill)
        summary = str(
            llm_payload.get("summary") or f"Prepared {len(actions)} file action(s)."
        ).strip()
        if not summary:
            summary = f"Prepared {len(actions)} file action(s)."

        requires_confirmation = (
            request.execution_policy != "autopilot"
            or any(action.requires_confirmation for action in actions)
        )
        cost_estimate = _cost_estimate(llm_payload=llm_payload, actions=actions, metadata=metadata)
        plan_hash = _plan_hash(
            chosen_skill=chosen_skill,
            actions=actions,
            summary=summary,
        )
        result = AgentPlanResult(
            plan_job_id=str(job.job_id),
            plan_hash=plan_hash,
            chosen_skill=chosen_skill,
            proposed_actions=actions,
            summary=summary,
            requires_confirmation=requires_confirmation,
            cost_estimate=cost_estimate,
        )
        await _upsert_agent_plan(
            db,
            job=job,
            request=request,
            result=result,
        )
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        return result


async def _choose_skill(
    db: AsyncSession,
    *,
    user_id: int,
    task_input: str,
    prefer_skill_id: str | None,
) -> AgentSkill | AgentSkillCatalogEntry | None:
    repo = AgentSkillRepository(db)
    if prefer_skill_id:
        skill = await repo.get_by_key(skill_key=prefer_skill_id, user_id=user_id)
        if skill is None:
            raise ApiError(status_code=404, code=404, message="Preferred skill not found")
        return skill

    candidates = await repo.list_visible(user_id=user_id, limit=50)
    if not candidates:
        return None

    normalized_input = task_input.lower()
    best: tuple[int, AgentSkillCatalogEntry] | None = None
    for candidate in candidates:
        haystack = (
            f"{candidate.skill_key} {candidate.name} {candidate.description} "
            f"{candidate.triggers_text or ''} {candidate.search_text}"
        ).lower()
        score = 0
        for token in _tokens(normalized_input):
            if token in haystack:
                score += 2 if token in {"organize", "整理", "classify", "分类"} else 1
        if "整理" in normalized_input and "organize" in haystack:
            score += 4
        if best is None or score > best[0]:
            best = (score, candidate)

    if best is not None and best[0] > 0:
        return best[1]
    return candidates[0]


def _tokens(text: str) -> list[str]:
    return [token.strip(" ,.;:!?，。；：！？") for token in text.split() if token.strip()]


def _skill_key(skill: AgentSkill | AgentSkillCatalogEntry | None) -> str | None:
    if skill is None:
        return None
    return str(skill.skill_key)


def _skill_name(skill: AgentSkill | AgentSkillCatalogEntry | None) -> str | None:
    if skill is None:
        return None
    return str(skill.name)


def _skill_tool_whitelist(skill: AgentSkill | AgentSkillCatalogEntry | None) -> tuple[str, ...]:
    raw: Any = None
    if isinstance(skill, AgentSkill):
        raw = skill.tool_whitelist_json
    elif skill is not None:
        raw = skill.tool_whitelist_json
    if isinstance(raw, list) and raw:
        return tuple(str(item) for item in raw if str(item).strip())
    return DEFAULT_AGENT_TOOLS


def _chosen_skill(skill: AgentSkill | AgentSkillCatalogEntry | None) -> AgentChosenSkill | None:
    key = _skill_key(skill)
    name = _skill_name(skill)
    if not key or not name:
        return None
    return AgentChosenSkill(id=key, name=name)


async def _collect_context_metadata(
    db: AsyncSession,
    *,
    user_id: int,
    request: PlanAgentRequest,
) -> dict[str, Any]:
    context = request.context
    selected_file_ids = _parse_ids(context.selected_file_ids, "fileId")
    selected_folder_ids = _parse_ids(context.selected_folder_ids, "folderId")

    files: list[File] = []
    folders: list[Folder] = []
    if selected_file_ids:
        files = list(
            await db.scalars(
                select(File).where(
                    and_(
                        File.owner_id == user_id,
                        File.file_id.in_(selected_file_ids),
                        File.status == FileStatus.ACTIVE,
                        File.is_latest.is_(True),
                    )
                )
            )
        )
    if selected_folder_ids:
        folders = list(
            await db.scalars(
                select(Folder).where(
                    and_(
                        Folder.owner_id == user_id,
                        Folder.folder_id.in_(selected_folder_ids),
                        Folder.status == FolderStatus.ACTIVE,
                    )
                )
            )
        )

    scope = "selected" if selected_file_ids or selected_folder_ids else "currentFolder"
    folder_id = await _resolve_folder_id(db, user_id=user_id, folder_id=context.root_folder_id)
    if scope == "currentFolder":
        folders = list(
            await db.scalars(
                select(Folder)
                .where(
                    and_(
                        Folder.owner_id == user_id,
                        Folder.parent_folder_id == folder_id,
                        Folder.status == FolderStatus.ACTIVE,
                    )
                )
                .order_by(Folder.folder_name.asc())
                .limit(200)
            )
        )
        files = list(
            await db.scalars(
                select(File)
                .where(
                    and_(
                        File.owner_id == user_id,
                        File.folder_id == folder_id,
                        File.status == FileStatus.ACTIVE,
                        File.is_latest.is_(True),
                    )
                )
                .order_by(File.file_name.asc())
                .limit(200)
            )
        )

    return {
        "scope": scope,
        "currentPath": context.current_path,
        "rootFolderId": str(folder_id),
        "files": [_file_metadata(row) for row in files],
        "folders": [_folder_metadata(row) for row in folders],
    }


async def _resolve_folder_id(db: AsyncSession, *, user_id: int, folder_id: str | None) -> int:
    if not folder_id or folder_id == "root":
        root = await db.scalar(
            select(Folder).where(
                and_(
                    Folder.owner_id == user_id,
                    Folder.parent_folder_id.is_(None),
                    Folder.folder_type == FolderType.ROOT,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if root is None:
            raise ApiError(status_code=404, code=404, message="Root folder not found")
        return int(root.folder_id)
    try:
        parsed = int(folder_id)
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message="Invalid rootFolderId") from exc
    exists = await db.scalar(
        select(Folder.folder_id).where(
            and_(
                Folder.folder_id == parsed,
                Folder.owner_id == user_id,
                Folder.status == FolderStatus.ACTIVE,
            )
        )
    )
    if exists is None:
        raise ApiError(status_code=404, code=404, message="Folder not found")
    return parsed


def _parse_ids(raw_ids: list[str], field_name: str) -> list[int]:
    parsed: list[int] = []
    seen: set[int] = set()
    for raw in raw_ids:
        if raw == "root":
            continue
        try:
            value = int(raw)
        except ValueError as exc:
            raise ApiError(status_code=400, code=400, message=f"Invalid {field_name}") from exc
        if value <= 0 or value in seen:
            continue
        parsed.append(value)
        seen.add(value)
    return parsed


def _file_metadata(row: File) -> dict[str, Any]:
    return {
        "itemType": "file",
        "id": str(row.file_id),
        "name": row.file_name,
        "size": int(row.file_size or 0),
        "mimeType": resolve_file_mime_type(
            mime_type=row.mime_type,
            file_ext=row.file_ext,
            file_name=row.file_name,
        ),
        "folderId": str(row.folder_id),
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def _folder_metadata(row: Folder) -> dict[str, Any]:
    return {
        "itemType": "folder",
        "id": str(row.folder_id),
        "name": row.folder_name,
        "size": int(row.cached_size or 0),
        "parentFolderId": str(row.parent_folder_id) if row.parent_folder_id else None,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def _system_prompt() -> str:
    return (
        "You are FileFlash Agent Planner. Return only JSON. "
        "Plan file-organization actions using the provided tools and metadata. "
        "Do not read or infer file contents. Deletions are high risk and must be explicit. "
        "Cross-step dependencies must use '$stepN.field' references only and never symbolic placeholders "
        "like 'newFolderId'."
    )


def _user_prompt(
    *,
    request: PlanAgentRequest,
    skill: AgentSkill | AgentSkillCatalogEntry | None,
    allowed_tools: tuple[str, ...],
    metadata: dict[str, Any],
) -> str:
    payload = {
        "task": request.input,
        "executionPolicy": request.execution_policy,
        "reasoningEffort": request.hints.reasoning_effort,
        "dataPolicy": request.data_policy.model_dump(by_alias=True),
        "skill": _skill_payload(skill),
        "allowedTools": list(allowed_tools),
        "toolSchemas": _tool_schemas(allowed_tools),
        "referenceContract": {
            "syntax": "$stepN.field",
            "rules": [
                "If an action needs data from a previous action, use only '$stepN.field'.",
                "N must refer to an existing previous step number.",
                "Never invent symbolic placeholders such as 'newFolderId'.",
            ],
            "requiredExample": [
                {
                    "step": 1,
                    "tool": "drive.createFolder",
                    "input": {"parentFolderId": "root", "name": "Movies"},
                },
                {
                    "step": 2,
                    "tool": "drive.moveFile",
                    "input": {"fileId": "13", "targetFolderId": "$step1.folderId"},
                },
            ],
        },
        "fileMetadata": metadata,
        "outputSchema": {
            "summary": "string",
            "proposedActions": [
                {
                    "step": "integer starting at 1",
                    "tool": "one of allowedTools",
                    "input": "object",
                    "sideEffect": "read or write",
                }
            ],
        },
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _skill_payload(skill: AgentSkill | AgentSkillCatalogEntry | None) -> dict[str, Any] | None:
    if skill is None:
        return None
    if isinstance(skill, AgentSkill):
        return {
            "skillKey": skill.skill_key,
            "name": skill.name,
            "description": skill.description,
            "triggersText": skill.triggers_text,
            "planTemplate": skill.plan_template_json or {},
        }
    return {
        "skillKey": skill.skill_key,
        "name": skill.name,
        "description": skill.description,
        "triggersText": skill.triggers_text,
        "planTemplate": skill.plan_template_json or {},
    }


def _tool_schemas(allowed_tools: tuple[str, ...]) -> list[dict[str, Any]]:
    descriptions = {
        "drive.listFolder": "List direct folder contents by folderId.",
        "drive.createFolder": "Create a folder under parentFolderId with name.",
        "drive.moveFile": "Move fileId into targetFolderId.",
        "drive.moveFolder": "Move folderId into targetParentId.",
        "drive.renameFile": "Rename fileId to fileName.",
        "drive.renameFolder": "Rename folderId to folderName.",
        "drive.deleteFile": "Soft-delete fileId into recycle bin. High risk.",
        "drive.deleteFolder": "Soft-delete folderId into recycle bin. High risk.",
    }
    return [{"tool": tool, "description": descriptions.get(tool, "")} for tool in allowed_tools]


def _normalize_actions(
    *,
    llm_payload: dict[str, Any],
    allowed_tools: tuple[str, ...],
    max_steps: int,
) -> list[AgentProposedAction]:
    raw_actions = llm_payload.get("proposedActions", llm_payload.get("proposed_actions"))
    if raw_actions is None:
        raw_actions = llm_payload.get("actions")
    if not isinstance(raw_actions, list):
        raise ApiError(status_code=502, code=502, message="Agent plan JSON missing proposedActions")
    if len(raw_actions) > max_steps:
        raise ApiError(status_code=400, code=400, message="Agent plan exceeds maxSteps")

    allowed = set(allowed_tools)
    normalized: list[AgentProposedAction] = []
    seen_steps: set[int] = set()
    for index, raw_action in enumerate(raw_actions, start=1):
        if not isinstance(raw_action, dict):
            raise ApiError(status_code=502, code=502, message="Agent action must be an object")
        tool = str(raw_action.get("tool") or raw_action.get("toolName") or "").strip()
        if tool not in allowed:
            raise ApiError(
                status_code=400,
                code=400,
                message=f"Tool is not allowed by selected skill: {tool}",
            )
        action_input = raw_action.get("input", raw_action.get("arguments", {}))
        if not isinstance(action_input, dict):
            raise ApiError(
                status_code=502,
                code=502,
                message="Agent action input must be an object",
            )
        try:
            step = int(raw_action.get("step") or index)
        except (TypeError, ValueError) as exc:
            raise ApiError(
                status_code=502,
                code=502,
                message="Agent action step is invalid",
            ) from exc
        if step < 1 or step in seen_steps:
            raise ApiError(status_code=502, code=502, message="Agent action step is invalid")
        seen_steps.add(step)
        action = AgentProposedAction(
            step=step,
            tool=tool,
            input=action_input,
            side_effect=raw_action.get("sideEffect") or classify_tool_side_effect(tool),  # type: ignore[arg-type]
            risk_level=raw_action.get("riskLevel") or "low",  # type: ignore[arg-type]
            requires_confirmation=bool(raw_action.get("requiresConfirmation") or False),
            confirmation_reason=raw_action.get("confirmationReason"),
        )
        normalized.append(normalize_action_risk(action))
    sorted_actions = sorted(normalized, key=lambda action: action.step)
    _validate_action_inputs(sorted_actions)
    return sorted_actions


def _validate_action_inputs(actions: list[AgentProposedAction]) -> None:
    steps = {action.step for action in actions}
    for action in actions:
        _validate_action_input_value(
            value=action.input,
            action_step=action.step,
            known_steps=steps,
            field_name=None,
            field_path="input",
        )


def _validate_action_input_value(
    *,
    value: Any,
    action_step: int,
    known_steps: set[int],
    field_name: str | None,
    field_path: str,
) -> None:
    if isinstance(value, str):
        reference = parse_step_reference(value)
        if reference is not None:
            ref_step, _ = reference
            if ref_step not in known_steps:
                raise ApiError(
                    status_code=400,
                    code=400,
                    message=(
                        f"Invalid plan action at step {action_step}: field '{field_path}' references "
                        f"missing step {ref_step} via '{value}'."
                    ),
                )
            if ref_step >= action_step:
                raise ApiError(
                    status_code=400,
                    code=400,
                    message=(
                        f"Invalid plan action at step {action_step}: field '{field_path}' references "
                        f"future step {ref_step} via '{value}'. Use only previous-step references."
                    ),
                )
            return
        if is_symbolic_id_placeholder(value=value, field_name=field_name):
            raise ApiError(
                status_code=400,
                code=400,
                message=(
                    f"Invalid plan action at step {action_step}: field '{field_path}' uses "
                    f"unresolved placeholder '{value}'. Use '$stepN.field' references."
                ),
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_action_input_value(
                value=item,
                action_step=action_step,
                known_steps=known_steps,
                field_name=field_name,
                field_path=f"{field_path}[{index}]",
            )
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_action_input_value(
                value=item,
                action_step=action_step,
                known_steps=known_steps,
                field_name=key,
                field_path=f"{field_path}.{key}",
            )


def _cost_estimate(
    *,
    llm_payload: dict[str, Any],
    actions: list[AgentProposedAction],
    metadata: dict[str, Any],
) -> AgentCostEstimate:
    usage = llm_payload.get("_usage")
    if isinstance(usage, dict):
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        tokens = input_tokens + output_tokens
    else:
        tokens = max(1000, len(json.dumps(metadata, ensure_ascii=False)) // 3 + len(actions) * 180)
    return AgentCostEstimate(
        tokens=tokens,
        tool_calls=len(actions),
        duration_sec_estimate=max(1, len(actions) * 3),
    )


def _plan_hash(
    *,
    chosen_skill: AgentChosenSkill | None,
    actions: list[AgentProposedAction],
    summary: str,
) -> str:
    payload = {
        "chosenSkill": chosen_skill.model_dump(by_alias=True) if chosen_skill else None,
        "proposedActions": [action.model_dump(by_alias=True) for action in actions],
        "summary": summary,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def _upsert_agent_plan(
    db: AsyncSession,
    *,
    job: BackgroundJob,
    request: PlanAgentRequest,
    result: AgentPlanResult,
) -> None:
    existing = await db.scalar(select(AgentPlan).where(AgentPlan.job_id == job.job_id))
    values = {
        "job_id": int(job.job_id),
        "user_id": int(job.requested_by or 0),
        "input_text": request.input,
        "context_json": request.context.model_dump(by_alias=True),
        "execution_policy": DbAgentExecutionPolicy(request.execution_policy),
        "data_policy_json": request.data_policy.model_dump(by_alias=True),
        "chosen_skill_id": result.chosen_skill.id if result.chosen_skill else None,
        "proposed_actions_json": [
            action.model_dump(by_alias=True) for action in result.proposed_actions
        ],
        "plan_hash": result.plan_hash,
        "summary": result.summary,
        "cost_estimate_json": result.cost_estimate.model_dump(by_alias=True),
        "created_at": datetime.now(UTC),
    }
    if existing is None:
        db.add(AgentPlan(**values))
    else:
        for key, value in values.items():
            if key not in {"job_id", "created_at"}:
                setattr(existing, key, value)
    await db.flush()
