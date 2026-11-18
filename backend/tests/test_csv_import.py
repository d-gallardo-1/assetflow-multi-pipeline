"""CSV import: partial acceptance, located row errors, id clashes."""

from __future__ import annotations

import pytest

from app.exchange.csv_export import to_csv
from app.exchange.csv_import import RowError, parse_csv
from app.intake import CSV_COLUMNS
from app.seed import sample_inputs

from .conftest import API, active_ids, view

HEADER = ",".join(CSV_COLUMNS)
GOOD = "AST-601,Humber Test Plot,LAND_ACQUISITION,SITE_SCOUTING,Humber,1200,250000.50,Ada Fenwick-Lowe,53.7,-0.3,4,yes,LOW"


def csv_of(*rows: str, header: str = HEADER) -> bytes:
    return "\n".join([header, *rows]).encode("utf-8")


def changed(**cells: str) -> str:
    """The good row with some cells replaced."""
    values = dict(zip(CSV_COLUMNS, GOOD.split(",")))
    values.update(cells)
    return ",".join(values[column] for column in CSV_COLUMNS)


def errors_of(*rows: str) -> list[RowError]:
    return parse_csv(csv_of(*rows), set(), set()).errors


def test_sample_batch_imports_five_assets(client, engine):
    sample = client.get(f"{API}/assets/sample-csv")
    assert sample.headers["content-type"].startswith("text/csv")

    report = client.post(f"{API}/assets/import-csv", content=sample.content).json()

    assert report == {
        "total_rows": 5, "rejected_rows": 0, "errors": [],
        "imported": ["AST-501", "AST-502", "AST-503", "AST-504", "AST-505"],
    }
    assert engine.snapshot().kpis.active_assets == 19
    imported = view(engine, "AST-504")
    assert (imported.pipeline.value, imported.stage) == ("MULTI_TENANT_PARKS", "LEASE_CONTRACT_REVIEW")
    assert imported.audit[0].detail == "Created at 03. Lease Contract Review"


def test_valid_rows_are_imported_and_invalid_rows_are_reported(client, engine):
    body = csv_of(GOOD, changed(asset_id="AST-602", risk_level="SEVERE"), changed(asset_id="AST-603"))

    report = client.post(f"{API}/assets/import-csv", content=body).json()

    assert report["imported"] == ["AST-601", "AST-603"]
    assert (report["total_rows"], report["rejected_rows"]) == (3, 1)
    (error,) = report["errors"]
    assert (error["row"], error["column"], error["value"]) == (3, "risk_level", "SEVERE")
    assert "'LOW', 'MEDIUM' or 'HIGH'" in error["reason"]
    assert "AST-602" not in active_ids(engine)


@pytest.mark.parametrize(
    ("cells", "column", "fragment"),
    [
        ({"pipeline": "RETAIL"}, "pipeline", "Input should be"),
        ({"stage": "CIVIL_EXECUTION"}, "stage", "is not a stage of LAND_ACQUISITION"),
        ({"area_sqm": "0"}, "area_sqm", "greater than or equal to 1"),
        ({"area_sqm": "12.5"}, "area_sqm", "valid integer"),
        ({"capital_value_gbp": "-1"}, "capital_value_gbp", "greater than or equal to 0"),
        ({"capital_value_gbp": "10.999"}, "capital_value_gbp", "2 decimal places"),
        ({"capital_value_gbp": "ten"}, "capital_value_gbp", "valid decimal"),
        ({"lat": "90.01"}, "lat", "less than or equal to 90"),
        ({"lon": "-180.5"}, "lon", "greater than or equal to -180"),
        ({"lat": "nan"}, "lat", "finite number"),
        ({"grid_capacity_mva": "-3"}, "grid_capacity_mva", "greater than or equal to 0"),
        ({"permits_verified": "maybe"}, "permits_verified", "true, false, yes, no"),
        ({"name": ""}, "name", "at least 2 characters"),
        ({"asset_id": "A-1"}, "asset_id", "should match pattern"),
    ],
)
def test_each_bad_cell_is_reported_with_row_column_and_reason(cells, column, fragment):
    (error,) = errors_of(GOOD, changed(**{"asset_id": "AST-602", **cells}))

    assert (error.row, error.column) == (3, column)
    assert fragment in error.reason


def test_one_row_can_report_several_columns():
    errors = errors_of(changed(lat="100", lon="200", risk_level="x"))

    assert [(e.row, e.column) for e in errors] == [(2, "lat"), (2, "lon"), (2, "risk_level")]


@pytest.mark.parametrize("spelling", ["true", "YES", "y", "1", "false", "No", "n", "0"])
def test_boolean_spellings(spelling):
    parsed = parse_csv(csv_of(changed(permits_verified=spelling)), set(), set())

    assert parsed.valid[0].permits_verified is (spelling.lower() in {"true", "yes", "y", "1"})


def test_codes_are_read_regardless_of_case_and_stage_as_a_label():
    row = changed(pipeline="build_to_suit", stage="02. Planning & Grid Permits", risk_level="high")
    # The label contains no comma, so it needs no quoting.
    (asset,) = parse_csv(csv_of(row), set(), set()).valid

    assert (asset.pipeline.value, asset.stage, asset.risk_level.value) == (
        "BUILD_TO_SUIT", "PLANNING_GRID_PERMITS", "HIGH",
    )


def test_repeated_active_and_trashed_ids_are_row_errors_never_overwrites(client, engine):
    body = csv_of(
        GOOD,
        changed(name="Second copy"),  # AST-601 again, inside the file
        changed(asset_id="AST-401", name="Overwrite attempt"),  # active
        changed(asset_id="AST-412", name="Overwrite attempt"),  # in the trash bin
    )

    report = client.post(f"{API}/assets/import-csv", content=body).json()

    assert report["imported"] == ["AST-601"]
    assert [(e["row"], e["column"]) for e in report["errors"]] == [(3, "asset_id"), (4, "asset_id"), (5, "asset_id")]
    reasons = [e["reason"] for e in report["errors"]]
    assert "repeated inside the file (first on row 2)" in reasons[0]
    assert "already exists as an active asset" in reasons[1]
    assert "is in the trash bin" in reasons[2]
    assert view(engine, "AST-401").name == "Tees Valley Modular Logistics Hub Plot"
    assert view(engine, "AST-412").is_deleted is True


def test_a_blank_id_gets_the_next_free_one_without_taking_an_explicit_id(client):
    body = csv_of(changed(asset_id=""), changed(asset_id="AST-417"), changed(asset_id=""))

    report = client.post(f"{API}/assets/import-csv", content=body).json()

    assert sorted(report["imported"]) == ["AST-417", "AST-418", "AST-419"]
    assert report["errors"] == []


def test_importing_the_same_file_twice_rejects_every_row_the_second_time(client, engine):
    sample = to_csv(sample_inputs()).encode("utf-8")
    client.post(f"{API}/assets/import-csv", content=sample)
    sequence = engine.snapshot().sequence

    report = client.post(f"{API}/assets/import-csv", content=sample).json()

    assert (report["imported"], report["rejected_rows"]) == ([], 5)
    assert engine.snapshot().sequence == sequence  # nothing changed, nothing published
