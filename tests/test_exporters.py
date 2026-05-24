#!/usr/bin/env python3
"""Unit tests for XlsExporter (pure openpyxl, no wx, no db)."""

import openpyxl

from exporters import XlsExporter

ROWS = [
    {'event_id': 1, 'flow': 1, 'supplier': 'ACME', 'category': 'Salary',
     'settled': 1, 'reference': 'IN1', 'bill': 100.0, 'issued': '01-01-2020'},
    {'event_id': 2, 'flow': 0, 'supplier': 'Shop', 'category': 'Food',
     'settled': 1, 'reference': 'OUT1', 'bill': 30.0, 'issued': '02-01-2020'},
]


def test_export_creates_valid_workbook(tmp_path):
    path = str(tmp_path / "out.xlsx")
    XlsExporter().export(ROWS, path, title="PyggyBank")

    ws = openpyxl.load_workbook(path).active
    assert ws.title == "PyggyBank"
    assert ws.cell(1, 1).value == "FLOW"
    assert ws.cell(2, 3).value == "ACME"        # supplier of row 1
    assert ws.cell(2, 7).value == 100.0          # inflow -> IN (col G)
    assert ws.cell(3, 8).value == 30.0           # outflow -> OUT (col H)

    totals = 4                                    # header + 2 data rows + totals
    assert ws.cell(totals, 7).value == "=SUM(G2:G3)"
    assert ws.cell(totals, 8).value == "=SUM(H2:H3)"
    assert ws.cell(totals, 9).value == "=(G4-H4)"
