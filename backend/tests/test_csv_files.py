"""CSV import at file level: header, encoding, size and row limits; exports."""

from __future__ import annotations

import io

import pytest
from openpyxl import load_workbook

from app.exchange.csv_import import MAX_CSV_BYTES, MAX_CSV_ROWS
from app.exchange.safe_text import neutralise

from .conftest import API
from .test_csv_import import GOOD, HEADER, changed, csv_of


def post(client, body: bytes):
    return client.post(f"{API}/assets/import-csv", content=body)


def test_byte_order_mark_blank_lines_and_column_order_are_tolerated(client):
    columns = HEADER.split(",")
    reordered = ",".join(reversed(columns)).upper()
    row = ",".join(reversed(GOOD.split(",")))
    body = b"\xef\xbb\xbf" + f"{reordered}\r\n\r\n{row}\r\n\r\n".encode("utf-8")

    report = post(client, body).json()

    assert report["imported"] == ["AST-601"]
    assert report["total_rows"] == 1


@pytest.mark.parametrize(
    ("header", "fragment"),
    [
        (HEADER.replace(",region", ""), "Missing column(s): region."),
        (HEADER + ",owner", "Unknown column(s): owner."),
        (HEADER.replace("lat,lon", "lat,lat"), "Repeated column(s): lat."),
        (HEADER.replace("risk_level", "risk"), "Missing column(s): risk_level. Unknown column(s): risk."),
    ],
)
def test_a_bad_header_rejects_the_whole_file(client, engine, header, fragment):
    response = post(client, csv_of(GOOD, header=header))

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail.startswith("Header row rejected. ")
    assert fragment in detail
    assert "Expected columns: asset_id, name, pipeline" in detail
    assert engine.snapshot().kpis.active_assets == 14


def test_unreadable_files_are_rejected(client, engine):
    empty = post(client, b"")
    blank = post(client, b"\n\n  \n")
    not_utf8 = post(client, HEADER.encode() + b"\n\xff\xfe\x00bad")
    too_large = post(client, csv_of(GOOD) + b" " * MAX_CSV_BYTES)

    assert (empty.status_code, empty.json()["detail"]) == (422, "The file is empty.")
    assert blank.json()["detail"] == "The file is empty."
    assert (not_utf8.status_code, not_utf8.json()["detail"]) == (422, "The file is not valid UTF-8 text.")
    assert (too_large.status_code, too_large.json()["detail"]) == (413, "The file is larger than the 256 KB limit.")
    assert engine.snapshot().sequence == 0


def test_row_limit_is_enforced_for_the_whole_file(client, engine):
    rows = [changed(asset_id=f"AST-{1000 + n}", name="Row") for n in range(MAX_CSV_ROWS + 1)]

    over = post(client, csv_of(*rows))
    at_limit = post(client, csv_of(*rows[:MAX_CSV_ROWS]))

    assert (over.status_code, over.json()["detail"]) == (422, "The file has 501 data rows; the limit is 500.")
    assert at_limit.status_code == 200
    assert len(at_limit.json()["imported"]) == MAX_CSV_ROWS


def test_a_row_with_the_wrong_number_of_cells_is_a_row_error(client):
    report = post(client, csv_of(GOOD + ",extra", changed(asset_id="AST-602"))).json()

    assert report["imported"] == ["AST-602"]
    assert report["errors"] == [
        {"row": 2, "column": "(row)", "reason": "The row has 14 cells; the header has 13.", "value": ""}
    ]


def test_formula_like_text_is_neutralised():
    for start in "=+-@":
        assert neutralise(f"{start}SUM(1)") == f"'{start}SUM(1)"
    assert neutralise("Tees Valley") == "Tees Valley"
    assert neutralise("") == ""


def test_xlsx_export_holds_active_assets_only_with_exact_money(client, engine):
    engine.soft_delete("AST-401")
    response = client.get(f"{API}/assets/export-xlsx")

    workbook = load_workbook(io.BytesIO(response.content))
    rows = list(workbook["Assets"].iter_rows(min_row=2, values_only=True))
    summary = {row[0]: row[1:] for row in workbook["Summary"].iter_rows(min_row=2, values_only=True)}

    assert "assetflow_portfolio.xlsx" in response.headers["content-disposition"]
    assert workbook.sheetnames == ["Assets", "Summary"]
    assert [row[0] for row in rows] == [f"AST-{n}" for n in range(402, 417) if n not in (412, 414)]
    assert rows[0][1:7] == (
        "Humber Grid Substation Plot B", "Industrial Land & Brownfield Sites",
        "02. Technical Due Diligence", "Humber", 42000, 6800000,
    )
    assert summary["Active assets"] == (13, 394597000)
    assert summary["Pipeline: Industrial Land"] == (3, 28100000)
    assert summary["Organisation"][0].startswith("Meridian Capital Assets")


def test_xlsx_export_and_sample_csv_never_emit_a_live_formula(client, engine):
    created = client.post(
        f"{API}/assets",
        json={
            "name": "=HYPERLINK(\"http://example.invalid\")", "pipeline": "LAND_ACQUISITION", "region": "@Humber",
            "area_sqm": 10, "capital_value_gbp": "1.00", "lead_engineer": "+Ada Fenwick", "lat": 53.7,
            "lon": -0.3, "grid_capacity_mva": 1, "permits_verified": False, "risk_level": "LOW",
        },
    )
    assert created.status_code == 201

    sheet = load_workbook(io.BytesIO(client.get(f"{API}/assets/export-xlsx").content))["Assets"]
    row = next(r for r in sheet.iter_rows(min_row=2) if r[0].value == created.json()["asset_id"])

    assert [row[i].value for i in (1, 4, 7)] == [
        "'=HYPERLINK(\"http://example.invalid\")", "'@Humber", "'+Ada Fenwick",
    ]
    assert all(row[i].data_type == "s" for i in (1, 4, 7))
    # Numbers stay numbers: a negative longitude is not text and is not touched.
    assert (row[9].value, row[9].data_type) == (-0.3, "n")
    for line in client.get(f"{API}/assets/sample-csv").text.splitlines():
        assert not line.startswith(("=", "+", "-", "@"))
