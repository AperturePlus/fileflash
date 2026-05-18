from __future__ import annotations

import hashlib
import secrets

from ..schemas.agent import (
    AgentChosenSkill,
    AgentCostEstimate,
    AgentPlanResult,
    AgentProposedAction,
    PlanAgentRequest,
)


def should_simulate_failure(user_input: str) -> bool:
    normalized = user_input.lower()
    return "fail" in normalized or "错误" in normalized or "失败" in normalized


def pick_proposed_actions(user_input: str) -> list[AgentProposedAction]:
    normalized = user_input.lower()
    if "整理" in user_input or "organize" in normalized:
        return [
            AgentProposedAction(
                step=1,
                tool="drive.listFolder",
                side_effect="read",
                input={"folderId": "root"},
            ),
            AgentProposedAction(
                step=2,
                tool="drive.createFolder",
                side_effect="write",
                input={"parentFolderId": "root", "name": "Organized"},
            ),
            AgentProposedAction(
                step=3,
                tool="drive.moveFile",
                side_effect="write",
                input={"fileId": "1", "targetFolderId": "$step2.folderId"},
            ),
        ]
    return [
        AgentProposedAction(
            step=1,
            tool="drive.resolvePath",
            side_effect="read",
            input={"path": "/My Files"},
        ),
        AgentProposedAction(
            step=2,
            tool="drive.listFolder",
            side_effect="read",
            input={"folderId": "$step1.folderId"},
        ),
        AgentProposedAction(
            step=3,
            tool="drive.renameFile",
            side_effect="write",
            input={"fileId": "2", "fileName": "renamed-by-agent.txt"},
        ),
    ]


def build_mock_plan_result(*, job_id: int, request: PlanAgentRequest) -> AgentPlanResult:
    proposed = pick_proposed_actions(request.input)
    requires_confirmation = request.execution_policy != "autopilot"
    plan_hash = f"sha256:{hashlib.sha256(secrets.token_bytes(16)).hexdigest()}"
    skill_id = request.hints.prefer_skill_id or "builtin:organizeByType"
    skill_name = "Preferred Skill" if request.hints.prefer_skill_id else "Organize By Type"
    return AgentPlanResult(
        plan_job_id=str(job_id),
        plan_hash=plan_hash,
        chosen_skill=AgentChosenSkill(id=skill_id, name=skill_name),
        proposed_actions=proposed,
        summary=f"Cloud Agent generated {len(proposed)} actions for: {request.input}",
        requires_confirmation=requires_confirmation,
        cost_estimate=AgentCostEstimate(
            tokens=max(1600, int(request.hints.budget_tokens * 0.18)),
            tool_calls=len(proposed),
            duration_sec_estimate=len(proposed) * 4,
        ),
    )
