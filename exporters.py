#!/usr/bin/env python3
"""
Export services for PyggyBank.

Pure data-to-file builders, with no wxPython and no database: they take the
domain rows (the same dicts the Controller returns) and produce a file. This
keeps the heavy openpyxl logic out of the GUI event handlers and makes it
unit-testable on its own.
"""

from typing import Any, Dict, Iterable

import openpyxl
from openpyxl.styles import Font, PatternFill


class XlsExporter:
    """Build an .xlsx workbook from flow rows (event_id/flow/.../issued dicts)."""

    HEADERS = ('FLOW', 'SETTLED', 'SUPPLIER', 'CATEGORY',
               'REFERENCE', 'ISSUED', 'IN', 'OUT')

    def __init__(self) -> None:
        self._bold = Font(name='Times New Roman', bold=True)
        self._bold_underline = Font(name='Times New Roman', bold=True, underline='single')
        self._green = PatternFill(start_color='92D050', end_color='92D050', fill_type='solid')
        self._yellow = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')

    def export(self, rows: Iterable[Dict[str, Any]], path: str,
               title: str = "PyggyBank") -> str:
        """Write `rows` to an xlsx at `path`; inflows go to IN, outflows to OUT."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = title

        for col, header in enumerate(self.HEADERS, start=1):
            ws.cell(row=1, column=col, value=header)

        row = 2
        for r in rows:
            ws.cell(row=row, column=1, value=int(r["flow"]))
            ws.cell(row=row, column=2, value=int(r["settled"]))
            ws.cell(row=row, column=3, value=str(r["supplier"])).font = self._bold
            ws.cell(row=row, column=4, value=str(r["category"])).font = self._bold
            ws.cell(row=row, column=5, value=str(r["reference"]))
            ws.cell(row=row, column=6, value=str(r["issued"]))
            if int(r["flow"]) != 0:
                ws.cell(row=row, column=7, value=float(r["bill"])).fill = self._green
            else:
                ws.cell(row=row, column=8, value=float(r["bill"])).fill = self._yellow
            row += 1

        ws.cell(row=row, column=7, value="=SUM(G2:G%d)" % (row - 1)).font = self._bold
        ws.cell(row=row, column=8, value="=SUM(H2:H%d)" % (row - 1)).font = self._bold
        ws.cell(row=row, column=9, value="=(G%d-H%d)" % (row, row)).font = self._bold_underline

        wb.save(path)
        return path
