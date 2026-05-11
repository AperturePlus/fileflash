from __future__ import annotations

from src.core.http_headers import build_content_disposition


def test_build_content_disposition_for_ascii_filename() -> None:
    header = build_content_disposition("report.pdf", disposition="inline")
    assert header == 'inline; filename="report.pdf"; filename*=UTF-8\'\'report.pdf'


def test_build_content_disposition_for_cjk_filename() -> None:
    header = build_content_disposition("测试文档.pdf", disposition="inline")
    assert header.startswith('inline; filename="file.pdf"; filename*=UTF-8\'\'')
    assert "%E6%B5%8B%E8%AF%95%E6%96%87%E6%A1%A3.pdf" in header
    header.encode("latin-1")


def test_build_content_disposition_escapes_quotes() -> None:
    header = build_content_disposition('report "final".pdf', disposition="attachment")
    assert 'attachment; filename="report final.pdf"; filename*=UTF-8\'\'' in header


def test_build_content_disposition_fallback_for_empty_name() -> None:
    header = build_content_disposition("", disposition="attachment")
    assert header == 'attachment; filename="file"; filename*=UTF-8\'\'file'

