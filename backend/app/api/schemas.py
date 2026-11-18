"""Request and response bodies of the asset and trash endpoints."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from ..exchange.csv_import import RowError


class StageRequest(BaseModel):
    #: A stage code or name of the asset's own pipeline; the engine decides.
    stage: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)]


class CommandAccepted(BaseModel):
    """The new state itself arrives through the stream; this only confirms it."""

    sequence: int


class AssetCreated(BaseModel):
    asset_id: str
    sequence: int


class ImportReport(BaseModel):
    total_rows: int
    imported: list[str]
    rejected_rows: int
    errors: list[RowError]


class Health(BaseModel):
    status: str = Field(examples=["ok"])
    version: str
    synthetic_data: bool
    subscribers: int
