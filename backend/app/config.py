"""Runtime settings read from environment variables."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

API_PREFIX = "/api/v1"


@dataclass(frozen=True)
class Settings:
    heartbeat_seconds: float
    retention_days: int


def _number(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, default))
    except ValueError:
        return default
    # "inf" and "nan" parse as floats but are not usable settings.
    return value if math.isfinite(value) else default


def load_settings() -> Settings:
    """Read settings; invalid values fall back to the defaults.

    * ``ASSETFLOW_HEARTBEAT_SECONDS``  silence on the stream before a heartbeat (5.0)
    * ``ASSETFLOW_RETENTION_DAYS``     days an asset stays in the trash bin (30)

    The frontend treats eight seconds of silence as a dead connection, so the
    heartbeat is kept between 1 and 6 seconds. Retention is kept between 1 and
    365 days.
    """
    heartbeat = _number("ASSETFLOW_HEARTBEAT_SECONDS", 5.0)
    retention = int(_number("ASSETFLOW_RETENTION_DAYS", 30))
    return Settings(
        heartbeat_seconds=min(6.0, max(1.0, heartbeat)),
        retention_days=min(365, max(1, retention)),
    )
