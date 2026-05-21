from __future__ import annotations

import mimetypes
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DANGEROUS_SUFFIXES = frozenset(
    {
        ".app",
        ".apk",
        ".bat",
        ".cmd",
        ".com",
        ".cpl",
        ".dll",
        ".dmg",
        ".exe",
        ".hta",
        ".iso",
        ".jar",
        ".js",
        ".lnk",
        ".msi",
        ".ps1",
        ".scr",
        ".vbs",
        ".wsf",
    }
)
DECOY_SUFFIXES = frozenset(
    {
        ".csv",
        ".doc",
        ".docx",
        ".jpg",
        ".jpeg",
        ".pdf",
        ".png",
        ".ppt",
        ".txt",
        ".xls",
        ".xlsx",
        ".zip",
    }
)
MACH_O_SIGNATURES = (
    b"\xFE\xED\xFA\xCE",
    b"\xFE\xED\xFA\xCF",
    b"\xCE\xFA\xED\xFE",
    b"\xCF\xFA\xED\xFE",
)
SHEBANG_KEYWORDS = (b"powershell", b"pwsh", b"bash", b"wscript", b"cscript", b"python", b"node")


def run_dangerous_file_scan(payload: dict[str, Any] | Any) -> dict[str, Any]:
    raw_path = str(payload.get("localPath") or payload.get("inputPath") or "").strip()
    if not raw_path:
        raise ValueError("Scan payload requires localPath or inputPath")

    file_path = Path(raw_path).expanduser()
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"Scan target not found: {file_path}")

    header = _read_header(file_path)
    suffixes = [suffix.lower() for suffix in file_path.suffixes]
    signals: list[str] = []

    if suffixes:
        last_suffix = suffixes[-1]
        if last_suffix in DANGEROUS_SUFFIXES:
            signals.append(f"dangerous-extension:{last_suffix}")
        if (
            len(suffixes) >= 2
            and suffixes[-2] in DECOY_SUFFIXES
            and last_suffix in DANGEROUS_SUFFIXES
        ):
            signals.append(f"double-extension:{suffixes[-2]}{last_suffix}")

    signals.extend(_detect_magic_signals(header))
    risk_score = min(100, len(signals) * 25)
    scan_result = "blocked" if signals else "clean"
    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    scanned_at = datetime.now(UTC).isoformat()

    details = {
        "fileName": file_path.name,
        "suffixes": suffixes,
        "mimeType": mime_type,
        "fileSize": file_path.stat().st_size,
        "signals": signals,
    }
    return {
        "scanType": "dangerousFileHeuristic",
        "scanResult": scan_result,
        "engineName": "fileflash-heuristic",
        "engineVersion": "2026.04",
        "riskScore": risk_score,
        "detectedSignals": signals,
        "scannedAt": scanned_at,
        "details": details,
    }


def _read_header(file_path: Path, max_bytes: int = 4096) -> bytes:
    with file_path.open("rb") as fp:
        return fp.read(max_bytes)


def _detect_magic_signals(header: bytes) -> list[str]:
    signals: list[str] = []
    if header.startswith(b"MZ"):
        signals.append("magic:portable-executable")
    if header.startswith(b"\x7FELF"):
        signals.append("magic:elf")
    if any(header.startswith(signature) for signature in MACH_O_SIGNATURES):
        signals.append("magic:macho")

    if header.startswith(b"#!"):
        line = header.splitlines()[0].lower()
        if any(keyword in line for keyword in SHEBANG_KEYWORDS):
            signals.append("script:shebang-executable")
    return signals
