"""Settings read from the environment: defaults, fallbacks and clamping."""

from __future__ import annotations

import pytest

from app.config import load_settings


def test_defaults(monkeypatch):
    monkeypatch.delenv("ASSETFLOW_HEARTBEAT_SECONDS", raising=False)
    monkeypatch.delenv("ASSETFLOW_RETENTION_DAYS", raising=False)

    settings = load_settings()

    assert (settings.heartbeat_seconds, settings.retention_days) == (5.0, 30)


@pytest.mark.parametrize(
    ("heartbeat", "retention", "expected"),
    [
        ("2.5", "7", (2.5, 7)),
        ("0", "0", (1.0, 1)),  # clamped up
        ("60", "9999", (6.0, 365)),  # clamped down
        ("soon", "many", (5.0, 30)),  # not numbers
        ("inf", "nan", (5.0, 30)),  # numbers that are not usable
        ("-3", "-3", (1.0, 1)),
    ],
)
def test_invalid_values_fall_back_and_valid_ones_are_clamped(monkeypatch, heartbeat, retention, expected):
    monkeypatch.setenv("ASSETFLOW_HEARTBEAT_SECONDS", heartbeat)
    monkeypatch.setenv("ASSETFLOW_RETENTION_DAYS", retention)

    settings = load_settings()

    assert (settings.heartbeat_seconds, settings.retention_days) == expected
