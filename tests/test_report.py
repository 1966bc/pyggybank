#!/usr/bin/env python3
"""
The PDF report builds with NO wxPython, NO database and NO app reference —
just rows + a ReportHeader. That is the point of the N7-bis decoupling.
"""

import os
import datetime

from reports.rpt_flows import GeneratePDF, ReportHeader

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

ROWS = [
    {'supplier': 'ACME', 'category': 'Salary', 'reference': 'IN1',
     'flow': 1, 'settled': 1, 'issued': '01-01-2020', 'bill': 100.0},
    {'supplier': 'Shop', 'category': 'Food', 'reference': 'OUT1',
     'flow': 0, 'settled': 1, 'issued': '02-01-2020', 'bill': 30.0},
]


def test_pdf_built_without_app():
    header = ReportHeader(
        title="PyggyBank",
        logo=os.path.join(ROOT, "images", "report.gif"),
        start_date=datetime.datetime(2020, 1, 1),
        end_date=datetime.datetime(2020, 12, 31),
        category="No select",
        supplier="No select",
        records=len(ROWS))

    path = GeneratePDF(list(ROWS), header).create_doc()
    try:
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        os.remove(path)
