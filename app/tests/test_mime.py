from __future__ import annotations

import pytest

from fileflash.core.mime import DEFAULT_MIME_TYPE, resolve_file_mime_type


@pytest.mark.parametrize(
    ("file_name", "expected"),
    [
        ("movie.mp4", "video/mp4"),
        ("movie.mov", "video/quicktime"),
        ("movie.mkv", "video/x-matroska"),
        ("movie.webm", "video/webm"),
        ("movie.m4v", "video/x-m4v"),
        ("movie.avi", "video/x-msvideo"),
    ],
)
def test_resolve_file_mime_type_for_generic_video_mime(file_name: str, expected: str) -> None:
    assert resolve_file_mime_type(mime_type="application/octet-stream", file_name=file_name) == expected


def test_resolve_file_mime_type_keeps_specific_mime() -> None:
    assert resolve_file_mime_type(mime_type="video/mp4", file_name="movie.mp4") == "video/mp4"


def test_resolve_file_mime_type_falls_back_when_extension_unknown() -> None:
    assert resolve_file_mime_type(mime_type="", file_name="payload.unknownext") == DEFAULT_MIME_TYPE

