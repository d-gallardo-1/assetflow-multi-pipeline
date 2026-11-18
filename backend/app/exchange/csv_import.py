"""Parses and validates an asset CSV.

Policy: the header decides whether the file is read at all; after that, valid
rows are imported and each invalid row is reported with its row number, column
and reason. Nothing is ever overwritten.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError

from ..intake import CSV_COLUMNS, AssetInput

MAX_CSV_BYTES = 256 * 1024
MAX_CSV_ROWS = 500
_VALUE_PREVIEW = 60


class CsvRejected(ValueError):
    """The whole file was refused. ``status_code`` is the HTTP status to answer with."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class RowError(BaseModel):
    #: Line number in the file; the header is row 1.
    row: int
    column: str
    reason: str
    value: str = ""


@dataclass
class ParsedCsv:
    total_rows: int = 0
    valid: list[AssetInput] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)


def _decode(data: bytes) -> str:
    if len(data) > MAX_CSV_BYTES:
        raise CsvRejected(413, f"The file is larger than the {MAX_CSV_BYTES // 1024} KB limit.")
    try:
        # "utf-8-sig" also accepts the byte-order mark that Excel writes.
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CsvRejected(422, "The file is not valid UTF-8 text.") from None


def _header(row: list[str] | None) -> list[str]:
    if row is None:
        raise CsvRejected(422, "The file is empty.")
    names = [cell.strip().lower() for cell in row]
    findings = (
        ("Missing column(s)", [column for column in CSV_COLUMNS if column not in names]),
        ("Unknown column(s)", sorted({name for name in names if name not in CSV_COLUMNS})),
        ("Repeated column(s)", sorted({name for name in names if names.count(name) > 1})),
    )
    problems = [f"{label}: {', '.join(found)}." for label, found in findings if found]
    if problems:
        expected = ", ".join(CSV_COLUMNS)
        raise CsvRejected(422, f"Header row rejected. {' '.join(problems)} Expected columns: {expected}.")
    return names


def _field_errors(number: int, cells: dict[str, str], invalid: ValidationError) -> list[RowError]:
    errors = []
    for problem in invalid.errors():
        reason = problem["msg"].removeprefix("Value error, ")
        # The pipeline-and-stage check belongs to no single field; it reports as "stage: ...".
        column = str(problem["loc"][0]) if problem["loc"] else "stage"
        reason = reason.removeprefix("stage: ")
        value = cells.get(column, "")[:_VALUE_PREVIEW]
        errors.append(RowError(row=number, column=column, reason=reason, value=value))
    return errors


def _id_clash(asset_id: str | None, first_seen: dict[str, int], active: set[str], trash: set[str]) -> str:
    if asset_id is None:
        return ""
    if asset_id in first_seen:
        return f"{asset_id} is repeated inside the file (first on row {first_seen[asset_id]})."
    if asset_id in trash:
        return f"{asset_id} is in the trash bin. Restore or purge it first; it is not overwritten."
    if asset_id in active:
        return f"{asset_id} already exists as an active asset; it is not overwritten."
    return ""


def parse_csv(data: bytes, active_ids: set[str], trash_ids: set[str]) -> ParsedCsv:
    """Validate ``data`` against the ids already in use; raise ``CsvRejected`` for a
    file that cannot be read at all."""
    reader = csv.reader(io.StringIO(_decode(data), newline=""))
    try:
        rows = [(reader.line_num, row) for row in reader if any(cell.strip() for cell in row)]
    except csv.Error:
        raise CsvRejected(422, "The file is not well-formed CSV.") from None
    header = _header(rows[0][1] if rows else None)
    body = rows[1:]
    if len(body) > MAX_CSV_ROWS:
        raise CsvRejected(422, f"The file has {len(body)} data rows; the limit is {MAX_CSV_ROWS}.")

    parsed = ParsedCsv(total_rows=len(body))
    first_seen: dict[str, int] = {}
    for number, row in body:
        if len(row) != len(header):
            reason = f"The row has {len(row)} cells; the header has {len(header)}."
            parsed.errors.append(RowError(row=number, column="(row)", reason=reason))
            continue
        cells = dict(zip(header, row))
        try:
            asset = AssetInput.model_validate(cells)
        except ValidationError as invalid:
            parsed.errors.extend(_field_errors(number, cells, invalid))
            continue
        clash = _id_clash(asset.asset_id, first_seen, active_ids, trash_ids)
        if clash:
            parsed.errors.append(RowError(row=number, column="asset_id", reason=clash, value=asset.asset_id or ""))
            continue
        if asset.asset_id:
            first_seen[asset.asset_id] = number
        parsed.valid.append(asset)
    return parsed
