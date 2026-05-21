from __future__ import annotations

import mimetypes
from pathlib import Path

DEFAULT_MIME_TYPE = "application/octet-stream"

_GENERIC_MIME_TYPES = {
    "",
    "application/octet-stream",
    "binary/octet-stream",
}

# Keep overrides explicit so behavior is stable across OS/runtime MIME databases.
_EXTENSION_MIME_OVERRIDES: dict[str, str] = {
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "mkv": "video/x-matroska",
    "webm": "video/webm",
    "m4v": "video/x-m4v",
    "avi": "video/x-msvideo",
}


def normalize_mime_type(mime_type: str | None) -> str:
    return (mime_type or "").strip().lower()


def resolve_file_mime_type(
    *,
    mime_type: str | None,
    file_ext: str | None = None,
    file_name: str | None = None,
    default: str = DEFAULT_MIME_TYPE,
) -> str:
    normalized_mime_type = normalize_mime_type(mime_type)
    if normalized_mime_type and normalized_mime_type not in _GENERIC_MIME_TYPES:
        return normalized_mime_type

    extension = _normalize_extension(file_ext) or _extract_extension(file_name)
    if not extension:
        return default

    overridden = _EXTENSION_MIME_OVERRIDES.get(extension)
    if overridden:
        return overridden

    guessed, _encoding = mimetypes.guess_type(f"file.{extension}", strict=False)
    guessed_type = normalize_mime_type(guessed)
    if guessed_type:
        return guessed_type

    return default


def _normalize_extension(file_ext: str | None) -> str:
    return (file_ext or "").strip().lower().lstrip(".")


def _extract_extension(file_name: str | None) -> str:
    if not file_name:
        return ""
    suffix = Path(file_name.strip()).suffix
    return suffix.lower().lstrip(".")

