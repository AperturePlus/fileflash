from __future__ import annotations

from pathlib import Path
from urllib.parse import quote


def build_content_disposition(filename: str, *, disposition: str) -> str:
    safe_disposition = disposition if disposition in {"attachment", "inline"} else "attachment"
    original = (filename or "").strip()
    fallback = _ascii_fallback_filename(original)
    encoded = quote(original or fallback, safe="")
    escaped_fallback = fallback.replace("\\", "\\\\").replace('"', r"\"")
    return f'{safe_disposition}; filename="{escaped_fallback}"; filename*=UTF-8\'\'{encoded}'


def _ascii_fallback_filename(filename: str) -> str:
    candidate = filename
    if not candidate:
        return "file"

    stem = Path(candidate).stem or "file"
    suffix = Path(candidate).suffix
    sanitized_stem = _sanitize_ascii_token(stem) or "file"
    sanitized_suffix = _sanitize_ascii_suffix(suffix)
    return f"{sanitized_stem}{sanitized_suffix}"


def _sanitize_ascii_token(value: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_. ()[]{}+@,")
    normalized = "".join(ch for ch in value if ord(ch) < 128 and ch in allowed)
    normalized = normalized.strip(" .")
    return normalized


def _sanitize_ascii_suffix(suffix: str) -> str:
    if not suffix:
        return ""
    ascii_only = "".join(ch for ch in suffix if ord(ch) < 128 and (ch.isalnum() or ch in {".", "-", "_"}))
    if not ascii_only.startswith("."):
        ascii_only = f".{ascii_only.lstrip('.')}" if ascii_only else ""
    return ascii_only

