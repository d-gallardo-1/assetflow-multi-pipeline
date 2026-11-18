"""Shared fixtures. The clock is injected so tests can move time."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.engine import PortfolioEngine
from app.main import build_engine, create_app

API = "/api/v1"
START = datetime(2026, 3, 2, 8, 0, tzinfo=timezone.utc)


class Clock:
    """A clock that only moves when a test moves it."""

    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta: float) -> None:
        self.now += timedelta(**delta)


@pytest.fixture()
def clock() -> Clock:
    return Clock()


@pytest.fixture()
def engine(clock: Clock) -> PortfolioEngine:
    return build_engine(clock=clock)


@pytest.fixture()
def client(engine: PortfolioEngine):
    with TestClient(create_app(engine)) as test_client:
        yield test_client


def view(engine: PortfolioEngine, asset_id: str):
    """The read-side view of one asset, active or in the trash bin."""
    snapshot = engine.snapshot()
    active = [asset for board in snapshot.pipelines for asset in board.assets]
    for asset in [*active, *snapshot.trash]:
        if asset.asset_id == asset_id:
            return asset
    raise AssertionError(f"{asset_id} is not in the snapshot")


def active_ids(engine: PortfolioEngine) -> list[str]:
    return [asset.asset_id for board in engine.snapshot().pipelines for asset in board.assets]


def trash_ids(engine: PortfolioEngine) -> list[str]:
    return [asset.asset_id for asset in engine.snapshot().trash]


def parse_sse(frame: str) -> tuple[str, dict]:
    """Split one SSE frame into ``(event name, decoded data)``."""
    fields = dict(line.split(": ", 1) for line in frame.strip().splitlines())
    return fields["event"], json.loads(fields["data"])
