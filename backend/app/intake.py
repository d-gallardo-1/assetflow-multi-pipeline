"""Validation of a new asset, shared by ``POST /assets`` and the CSV import.

One model holds every rule, so an asset typed into the API and an asset read
from a spreadsheet are accepted or refused for the same reasons.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from .models import Pipeline, RiskLevel
from .pipelines import SPECS, stage_code

ASSET_ID_PATTERN = r"^AST-\d{3,6}$"

MAX_AREA_SQM = 50_000_000
MAX_CAPITAL_GBP = Decimal("50000000000")
MAX_GRID_MVA = 5_000

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]

# Spelled out so the accepted forms are documented, not left to a library default.
_TRUE = {"true", "yes", "y", "1"}
_FALSE = {"false", "no", "n", "0"}


class AssetInput(BaseModel):
    """Field names are also the CSV column names."""

    model_config = ConfigDict(extra="forbid")

    #: Optional: the server assigns the next free id when it is missing.
    asset_id: Annotated[str, StringConstraints(strip_whitespace=True, pattern=ASSET_ID_PATTERN)] | None = None
    name: Text
    pipeline: Pipeline
    #: Defaults to the first stage of the pipeline.
    stage: str = ""
    region: Text
    area_sqm: Annotated[int, Field(ge=1, le=MAX_AREA_SQM)]
    capital_value_gbp: Annotated[Decimal, Field(ge=0, le=MAX_CAPITAL_GBP, decimal_places=2)]
    lead_engineer: Text
    lat: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
    lon: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
    grid_capacity_mva: Annotated[float, Field(ge=0, le=MAX_GRID_MVA, allow_inf_nan=False)]
    permits_verified: bool
    risk_level: RiskLevel

    @field_validator("asset_id", mode="before")
    @classmethod
    def _blank_id_means_assign(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("pipeline", "risk_level", mode="before")
    @classmethod
    def _upper_case_codes(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("permits_verified", mode="before")
    @classmethod
    def _boolean_spellings(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip().lower()
            if text in _TRUE:
                return True
            if text in _FALSE:
                return False
            raise ValueError("must be one of true, false, yes, no, y, n, 1, 0")
        return value

    @model_validator(mode="after")
    def _stage_belongs_to_pipeline(self) -> "AssetInput":
        spec = SPECS[self.pipeline]
        code = stage_code(self.stage) if self.stage.strip() else spec.stages[0].code
        if spec.index_of(code) is None:
            allowed = ", ".join(stage.code for stage in spec.stages)
            raise ValueError(f"stage: '{self.stage}' is not a stage of {self.pipeline.value}; expected one of {allowed}")
        self.stage = code
        return self


CSV_COLUMNS: tuple[str, ...] = tuple(AssetInput.model_fields)
