"""The four pipelines and their ordered stages.

This table is the single source of truth: the engine refuses a stage that is not
in the asset's own pipeline, and the frontend receives the order from the snapshot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Pipeline


@dataclass(frozen=True)
class Stage:
    code: str
    name: str
    #: The record expected on file once an asset reaches this stage.
    document: str


@dataclass(frozen=True)
class PipelineSpec:
    pipeline: Pipeline
    label: str
    short_label: str
    stages: tuple[Stage, ...]

    def index_of(self, stage_code: str) -> int | None:
        codes = [stage.code for stage in self.stages]
        return codes.index(stage_code) if stage_code in codes else None


def _spec(pipeline: Pipeline, label: str, short_label: str, *stages: tuple[str, str]) -> PipelineSpec:
    return PipelineSpec(
        pipeline=pipeline,
        label=label,
        short_label=short_label,
        stages=tuple(Stage(code=stage_code(name), name=name, document=doc) for name, doc in stages),
    )


def stage_code(text: str) -> str:
    """``"02. Planning & Grid Permits"`` -> ``PLANNING_GRID_PERMITS``.

    Accepts a code, a stage name or a numbered label, so a spreadsheet may use
    whichever form its author copied from the board.
    """
    words = re.sub(r"[^A-Za-z]+", " ", text).split()
    return "_".join(word.upper() for word in words)


def stage_label(index: int, stage: Stage) -> str:
    return f"{index + 1:02d}. {stage.name}"


SPECS: dict[Pipeline, PipelineSpec] = {
    spec.pipeline: spec
    for spec in (
        _spec(
            Pipeline.LAND_ACQUISITION, "Industrial Land & Brownfield Sites", "Industrial Land",
            ("Site Scouting", "Site scouting brief"),
            ("Technical Due Diligence", "Ground and environmental report"),
            ("Commercial Negotiation", "Heads of terms"),
            ("Title Closed", "Registered title record"),
        ),
        _spec(
            Pipeline.BUILD_TO_SUIT, "Custom Industrial & Logistics Facilities", "Build-to-Suit",
            ("Engineering Design", "Design basis"),
            ("Planning & Grid Permits", "Planning and grid application pack"),
            ("Civil Execution", "Construction programme"),
            ("Operational Handover", "Handover dossier"),
        ),
        _spec(
            Pipeline.MULTI_TENANT_PARKS, "Industrial Parks & Warehousing", "Multi-Tenant Parks",
            ("Unit Available", "Unit condition schedule"),
            ("Technical Fit-Out", "Fit-out specification"),
            ("Lease Contract Review", "Lease draft"),
            ("Active Operation", "Occupation certificate"),
        ),
        _spec(
            Pipeline.ADVISORY_VALUATION, "Technical & Environmental Audits", "Technical Advisory",
            ("Scope Intake", "Engagement scope letter"),
            ("Field Inspection", "Inspection field notes"),
            ("Compliance Modelling", "Compliance model workbook"),
            ("Certified Report", "Signed report"),
        ),
    )
}

STAGES_PER_PIPELINE = 4
