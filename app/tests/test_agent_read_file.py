from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from fileflash.agents.harness.tool_registry import REGISTRY
from fileflash.core.errors import ApiError


def _ensure_registered():
    import fileflash.agents.tools  # noqa: F401  triggers registration


_ensure_registered()


@pytest.mark.asyncio
async def test_read_file_text_content(tmp_path):
    _ensure_registered()
    spec = REGISTRY.get("drive.readFile")
    assert spec is not None

    db = AsyncMock()
    file_row = MagicMock()
    file_row.file_id = 7
    file_row.owner_id = 1
    file_row.file_name = "notes.txt"
    file_row.mime_type = "text/plain"
    file_row.file_ext = ".txt"
    file_row.file_size = 5
    file_row.storage_object_id = 3
    file_row.status = "active"
    file_row.is_latest = True
    db.scalar = AsyncMock(side_effect=[file_row, MagicMock(object_key="obj-key")])

    storage = AsyncMock()
    # iter_object_range yields bytes chunks
    async def _chunks(*a, **kw):
        for c in [b"hello"]:
            yield c
    storage.iter_object_range = _chunks
    storage.stat_object = AsyncMock(return_value=MagicMock(size=5))

    from fileflash.agents.harness.tool_registry import ToolContext
    ctx = ToolContext(db=db, user_id=1, file_service=None, folder_service=None, storage_reader=storage)
    output = await spec.handler(ctx, {"fileId": "7"})
    assert output["content"] == "hello"
    assert output["mime"] == "text/plain"
    assert output["bytesReturned"] == 5


@pytest.mark.asyncio
async def test_read_file_binary_returns_no_raw_bytes():
    _ensure_registered()
    spec = REGISTRY.get("drive.readFile")
    db = AsyncMock()
    file_row = MagicMock()
    file_row.file_id = 8
    file_row.owner_id = 1
    file_row.file_name = "pic.png"
    file_row.mime_type = "image/png"
    file_row.file_ext = ".png"
    file_row.file_size = 2048
    file_row.storage_object_id = 4
    file_row.status = "active"
    file_row.is_latest = True
    db.scalar = AsyncMock(side_effect=[file_row, MagicMock(object_key="obj-key")])

    storage = AsyncMock()
    storage.stat_object = AsyncMock(return_value=MagicMock(size=2048))

    from fileflash.agents.harness.tool_registry import ToolContext
    ctx = ToolContext(db=db, user_id=1, file_service=None, folder_service=None, storage_reader=storage)
    output = await spec.handler(ctx, {"fileId": "8"})
    assert "content" not in output or output.get("content") is None
    assert output["truncated"] is True


@pytest.mark.asyncio
async def test_read_file_other_user_returns_404():
    _ensure_registered()
    spec = REGISTRY.get("drive.readFile")
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=None)  # not found / not owned
    from fileflash.agents.harness.tool_registry import ToolContext
    ctx = ToolContext(db=db, user_id=1, file_service=None, folder_service=None, storage_reader=AsyncMock())
    with pytest.raises(ApiError) as exc:
        await spec.handler(ctx, {"fileId": "999"})
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_read_file_offset_beyond_size_returns_empty():
    _ensure_registered()
    spec = REGISTRY.get("drive.readFile")
    db = AsyncMock()
    file_row = MagicMock()
    file_row.file_id = 9
    file_row.owner_id = 1
    file_row.file_name = "small.txt"
    file_row.mime_type = "text/plain"
    file_row.file_ext = ".txt"
    file_row.file_size = 5
    file_row.storage_object_id = 5
    file_row.status = "active"
    file_row.is_latest = True
    db.scalar = AsyncMock(side_effect=[file_row, MagicMock(object_key="obj-key")])

    storage = AsyncMock()
    storage.stat_object = AsyncMock(return_value=MagicMock(size=5))
    storage.iter_object_range = AsyncMock()

    from fileflash.agents.harness.tool_registry import ToolContext
    ctx = ToolContext(db=db, user_id=1, file_service=None, folder_service=None, storage_reader=storage)
    output = await spec.handler(ctx, {"fileId": "9", "offset": 100})
    assert output["content"] == ""
    assert output["bytesReturned"] == 0
    assert output["truncated"] is False
    storage.iter_object_range.assert_not_called()
