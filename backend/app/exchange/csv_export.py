"""Writes assets as CSV in the layout the importer reads."""

from __future__ import annotations

import csv
import io
from typing import Iterable

from ..intake import CSV_COLUMNS, AssetInput
from .safe_text import neutralise


def _cell(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return neutralise(value) if isinstance(value, str) else value


def to_csv(rows: Iterable[AssetInput]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        values = row.model_dump(mode="json")
        writer.writerow([_cell(values[column]) for column in CSV_COLUMNS])
    return buffer.getvalue()
