from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from .common import CamelModel


class CreateUserGroupRequest(CamelModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class UserGroup(CamelModel):
    group_id: str
    name: str
    description: str | None = None
    member_count: int = Field(ge=0)
    created_at: datetime


class AddGroupMemberRequest(CamelModel):
    user_id: str
    role: Literal["member", "admin"]


class GroupMemberResult(CamelModel):
    user_id: str
    username: str
    role: Literal["member", "admin"]


class AddGroupMemberResponse(CamelModel):
    group_id: str
    group_name: str
    added_user: GroupMemberResult
    total_members: int = Field(ge=0)


class RemoveGroupMemberResponse(CamelModel):
    group_id: str
    group_name: str
    removed_user: GroupMemberResult
    remaining_members: int = Field(ge=0)
