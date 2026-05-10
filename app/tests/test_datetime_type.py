from __future__ import annotations

from datetime import UTC, datetime

from src.models.types import UTCDateTime


def test_utc_datetime_type_normalizes_bind_and_result_values():
    type_ = UTCDateTime()
    aware_value = datetime(2026, 5, 10, 14, 13, 41, 123456, tzinfo=UTC)

    bound_value = type_.process_bind_param(aware_value, None)
    assert bound_value == aware_value.replace(tzinfo=None)
    assert bound_value.tzinfo is None

    result_value = type_.process_result_value(bound_value, None)
    assert result_value == aware_value
    assert result_value.tzinfo is UTC


def test_utc_datetime_type_preserves_naive_input_as_utc_on_result():
    type_ = UTCDateTime()
    naive_value = datetime(2026, 5, 10, 14, 13, 41, 123456)

    bound_value = type_.process_bind_param(naive_value, None)
    assert bound_value == naive_value
    assert bound_value.tzinfo is None

    result_value = type_.process_result_value(bound_value, None)
    assert result_value == naive_value.replace(tzinfo=UTC)
    assert result_value.tzinfo is UTC