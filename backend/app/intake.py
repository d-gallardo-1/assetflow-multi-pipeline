"""Validation of a new asset, shared by ``POST /assets`` and the CSV import.

One model holds every rule, so an asset typed into the API and an asset read
from a spreadsheet are accepted or refused for the same reasons.
"""

from __future__ import annotations

import unicodedata
from decimal import Decimal
from typing import Annotated, Iterable

from pydantic import (
    AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator,
)

from .models import Pipeline, RiskLevel
from .pipelines import SPECS, stage_code

ASSET_ID_PATTERN = r"^AST-\d{3,6}$"
#: The largest number that pattern can hold.
MAX_ASSET_NUMBER = 999_999
#: Seed assets end at AST-416.
FIRST_ASSIGNED_NUMBER = 417

MAX_AREA_SQM = 50_000_000
MAX_CAPITAL_GBP = Decimal("50000000000")
MAX_GRID_MVA = 5_000



def _printable(text: str) -> str:
    """Refuse control characters. They have no place in a name, and a workbook
    cannot store them: one such value would make every later export fail."""
    if any(unicodedata.category(character) == "Cc" for character in text):
        raise ValueError("must not contain control characters")
    return text


Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80), AfterValidator(_printable)
]

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


def next_asset_id(taken: Iterable[str]) -> str:
    """One past the highest number in use. When that would no longer fit the id
    pattern, the first free number instead, so an assigned id is always usable."""
    numbers = {int(asset_id.split("-")[1]) for asset_id in taken}
    number = max(FIRST_ASSIGNED_NUMBER - 1, *numbers) + 1
    if number > MAX_ASSET_NUMBER:
        number = next(n for n in range(FIRST_ASSIGNED_NUMBER, MAX_ASSET_NUMBER + 1) if n not in numbers)
    return f"AST-{number}"


CSV_COLUMNS: tuple[str, ...] = tuple(AssetInput.model_fields)
