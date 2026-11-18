"""The refusal raised by engine commands, and the default clock."""

from __future__ import annotations

from datetime import datetime, timezone


class CommandRejected(Exception):
    """A command was refused. ``status_code`` is the HTTP status to answer with."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
