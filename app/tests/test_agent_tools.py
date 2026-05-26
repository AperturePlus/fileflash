from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from fileflash.agents.harness.router import ToolCall, ToolRouter
from fileflash.agents.harness.tool_registry import REGISTRY, ToolRegistry, ToolSpec
from fileflash.models.enums import FileStatus


async def _noop_handler(_ctx, _args):  # noqa: ANN001
    return {"ok": True}


def test_tool_registry_registers_and_maps_provider_names():
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="drive.testTool",
            description="test",
            input_schema={"type": "object"},
            side_effect="read",
            risk_level="low",
            requires_confirmation=False,
            handler=_noop_handler,
        )
    )

    assert registry.all_names() == ("drive.testTool",)
    assert registry.get("drive.testTool").anthropic_name == "drive_test_tool"
    assert registry.get_by_provider_name("drive_test_tool").name == "drive.testTool"
    assert registry.anthropic_tools_for(["drive.testTool"])[0]["internalName"] == "drive.testTool"


def test_tool_registry_rejects_duplicate_names():
    registry = ToolRegistry()
    spec = ToolSpec(
        name="drive.testTool",
        description="test",
        input_schema={"type": "object"},
        side_effect="read",
        risk_level="low",
        requires_confirmation=False,
        handler=_noop_handler,
    )
    registry.register(spec)

    with pytest.raises(ValueError):
        registry.register(spec)


def test_builtin_registry_contains_new_query_tools():
    names = set(REGISTRY.all_names())

    assert {
        "drive.searchFiles",
        "drive.getFileInfo",
        "drive.listRecent",
        "drive.statsByCategory",
        "drive.findDuplicates",
    }.issubset(names)
    assert REGISTRY.get("drive.deleteFile").risk_level == "high"


class DummyDb:
    def __init__(self) -> None:
        self.scalar = AsyncMock(return_value=1)
        self.scalars = AsyncMock(return_value=[])
        self.execute = AsyncMock()
        self.get = AsyncMock()


@pytest.mark.asyncio
async def test_tool_router_dispatches_new_search_files_tool():
    db = DummyDb()
    db.scalar = AsyncMock(
        side_effect=[
            1,
            SimpleNamespace(folder_name="My Files", parent_folder_id=None),
        ]
    )
    db.scalars = AsyncMock(
        side_effect=[
            [1],
            [
                SimpleNamespace(
                    file_id=10,
                    file_name="movie.mp4",
                    file_size=100,
                    mime_type="video/mp4",
                    file_ext="mp4",
                    folder_id=1,
                    storage_object_id=20,
                    status=FileStatus.ACTIVE,
                    is_latest=True,
                    created_at=None,
                    updated_at=None,
                )
            ],
        ]
    )
    router = ToolRouter(db=db, user_id=7)  # type: ignore[arg-type]

    result = await router.dispatch(
        ToolCall(
            tool_name="drive.searchFiles",
            arguments={"folderId": "root", "query": "movie", "category": "video"},
        )
    )

    assert result["totalItems"] == 1
    assert result["items"][0]["name"] == "movie.mp4"


@pytest.mark.asyncio
async def test_tool_router_dispatches_stats_by_category_tool():
    db = DummyDb()
    db.scalars = AsyncMock(
        side_effect=[
            [1],
            [
                SimpleNamespace(
                    file_id=10,
                    file_name="movie.mp4",
                    file_size=100,
                    mime_type="video/mp4",
                    file_ext="mp4",
                    folder_id=1,
                    storage_object_id=20,
                    created_at=None,
                    updated_at=None,
                ),
                SimpleNamespace(
                    file_id=11,
                    file_name="notes.txt",
                    file_size=10,
                    mime_type="text/plain",
                    file_ext="txt",
                    folder_id=1,
                    storage_object_id=21,
                    created_at=None,
                    updated_at=None,
                ),
            ],
        ]
    )
    router = ToolRouter(db=db, user_id=7)  # type: ignore[arg-type]

    result = await router.dispatch(
        ToolCall(tool_name="drive.statsByCategory", arguments={"folderId": "root"})
    )

    assert result["video"] == 1
    assert result["document"] == 1
    assert result["totalSize"] == 110


@pytest.mark.asyncio
async def test_tool_router_count_files_accepts_anime_alias_and_returns_item_names():
    db = DummyDb()
    db.scalar = AsyncMock(return_value=1)
    db.scalars = AsyncMock(
        side_effect=[
            [1],
            [
                SimpleNamespace(
                    file_id=10,
                    file_name="银河动漫番剧.mp4",
                    file_size=100,
                    mime_type="video/mp4",
                    file_ext="mp4",
                    folder_id=1,
                    storage_object_id=20,
                    created_at=None,
                    updated_at=None,
                ),
                SimpleNamespace(
                    file_id=11,
                    file_name="notes.txt",
                    file_size=10,
                    mime_type="text/plain",
                    file_ext="txt",
                    folder_id=1,
                    storage_object_id=21,
                    created_at=None,
                    updated_at=None,
                ),
            ],
        ]
    )
    router = ToolRouter(db=db, user_id=7)  # type: ignore[arg-type]

    result = await router.dispatch(
        ToolCall(
            tool_name="drive.countFiles",
            arguments={"folderId": "root", "recursive": True, "category": "anime"},
        )
    )

    assert result["category"] == "video"
    assert result["totalItems"] == 1
    assert result["itemNames"] == ["银河动漫番剧.mp4"]
    assert result["itemNamesTruncated"] is False


@pytest.mark.asyncio
async def test_tool_router_count_files_truncates_item_names_at_limit():
    db = DummyDb()
    db.scalar = AsyncMock(return_value=1)
    rows = [
        SimpleNamespace(
            file_id=100 + index,
            file_name=f"video-{index:02d}.mp4",
            file_size=100,
            mime_type="video/mp4",
            file_ext="mp4",
            folder_id=1,
            storage_object_id=200 + index,
            created_at=None,
            updated_at=None,
        )
        for index in range(13)
    ]
    db.scalars = AsyncMock(side_effect=[[1], rows])
    router = ToolRouter(db=db, user_id=7)  # type: ignore[arg-type]

    result = await router.dispatch(
        ToolCall(
            tool_name="drive.countFiles",
            arguments={"folderId": "root", "recursive": True, "category": "video"},
        )
    )

    assert result["totalItems"] == 13
    assert len(result["itemNames"]) == 12
    assert result["itemNames"][0] == "video-00.mp4"
    assert result["itemNames"][-1] == "video-11.mp4"
    assert result["itemNamesTruncated"] is True
