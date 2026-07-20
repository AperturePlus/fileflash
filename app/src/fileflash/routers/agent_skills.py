from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from ..core.deps import get_agent_skill_service, get_current_user, require_admin
from ..core.errors import api_success
from ..models.tables_identity import User
from ..schemas.agent_skill import (
    CreateAgentSkillRequest,
    ImportAgentSkillsRequest,
    ListAgentSkillsQuery,
    UpdateAgentSkillRequest,
)
from ..services.agent.skill_service import SkillService

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/skills")
async def list_agent_skills(
    query: ListAgentSkillsQuery = Depends(),
    current_user: User = Depends(get_current_user),
    skill_service: SkillService = Depends(get_agent_skill_service),
):
    data = await skill_service.list_skills(user_id=current_user.user_id, query=query)
    return api_success(data=data.model_dump(by_alias=True), message="Skills fetched successfully")


@router.get("/skills/{skill_key}")
async def get_agent_skill(
    skill_key: str,
    current_user: User = Depends(get_current_user),
    skill_service: SkillService = Depends(get_agent_skill_service),
):
    item = await skill_service.get_skill(user_id=current_user.user_id, skill_key=skill_key)
    return api_success(data=item.model_dump(by_alias=True), message="Skill fetched successfully")


@router.post("/skills")
async def create_custom_skill(
    payload: CreateAgentSkillRequest,
    current_user: User = Depends(get_current_user),
    skill_service: SkillService = Depends(get_agent_skill_service),
):
    item = await skill_service.create_custom_skill(user_id=current_user.user_id, payload=payload)
    return api_success(
        data=item.model_dump(by_alias=True),
        message="Skill created successfully",
        code=201,
        status_code=201,
    )


@router.patch("/skills/{skill_key}")
async def update_custom_skill(
    skill_key: str,
    payload: UpdateAgentSkillRequest,
    current_user: User = Depends(get_current_user),
    skill_service: SkillService = Depends(get_agent_skill_service),
):
    item = await skill_service.update_custom_skill(user_id=current_user.user_id, skill_key=skill_key, payload=payload)
    return api_success(data=item.model_dump(by_alias=True), message="Skill updated successfully")


@router.delete("/skills/{skill_key}")
async def delete_custom_skill(
    skill_key: str,
    current_user: User = Depends(get_current_user),
    skill_service: SkillService = Depends(get_agent_skill_service),
):
    await skill_service.delete_custom_skill(user_id=current_user.user_id, skill_key=skill_key)
    return api_success(
        data={
            "skillKey": skill_key,
            "deletedAt": datetime.now(UTC).isoformat(),
        },
        message="Skill deleted successfully",
    )


@router.post("/skills/import")
async def import_global_skills(
    payload: ImportAgentSkillsRequest,
    _: User = Depends(require_admin),
    skill_service: SkillService = Depends(get_agent_skill_service),
):
    data = await skill_service.import_global_skills(payload=payload)
    return api_success(data=data.model_dump(by_alias=True), message="Skills imported successfully")


__all__ = ["router"]

