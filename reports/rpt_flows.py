#-----------------------------------------------------------------------------
# project:  pyggy bank
# module:   rpt_flows.py
# authors:  giuseppe costanzi aka 1966bc
# mailto:   [giuseppe.costanzi@gmail.com]
# modify:   2026 - ported to Python 3 / reportlab 4
# version:  3.0
# description: PDF report of the flows
#-----------------------------------------------------------------------------

"""
PDF report builder.

Decoupled from the application: it receives the rows to print and a ReportHeader
value object (title, logo path, filter summary). It has no wxPython, no database
and no app reference; it builds the file and returns its path. Opening the file
is the caller's responsibility.
"""

import os
import datetime
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List

from reportlab.platypus import Spacer, SimpleDocTemplate, Table, TableStyle
from reportlab.platypus.flowables import Image, PageBreak
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4


@dataclass
class ReportHeader:
    """Everything the report needs about its context (no app/engine)."""
    title: str
    logo: str
    start_date: datetime.datetime
    end_date: datetime.datetime
    category: str
    supplier: str
    records: int


class GeneratePDF:
    def __init__(self, rows: List[Dict[str, Any]], header: ReportHeader) -> None:
        self.rows = rows
        self.header = header
        self.today = datetime.date.today()
        self.story: list = []

    def _footer(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont('Courier', 9)
        canvas.drawString(inch, 0.75 * inch, "%s - %s" % (self.today.strftime('%d/%m/%Y'),
                                                          canvas.getPageNumber()))
        canvas.drawString(490, 0.75 * inch, "his Majesty")
        canvas.setFont('Times-Bold', 8)
        canvas.drawCentredString(0.5 * A4[0], 0.5 * inch, "%s" % self.header.title)
        canvas.restoreState()

    def reportHeader(self) -> Table:
        logo = Image(self.header.logo)
        logo.drawHeight = 0.80 * inch
        logo.drawWidth = 1.20 * inch

        t = Table((('Data Report', '', [logo]),
                   ("Start Date", self.header.start_date.strftime('%d/%m/%Y'), ''),
                   ("End Date", self.header.end_date.strftime('%d/%m/%Y'), ''),
                   ("Category", self.header.category, ''),
                   ("Supplier", self.header.supplier, ''),
                   ("Records", self.header.records, '')),
                  (80, 80, 250),
                  (18, 18, 18, 18, 18, 18,))
        t.setStyle(TableStyle([('SPAN', (2, 0), (2, -1)),
                               ('BOX', (0, 1), (1, -1), 0.5, colors.lightgrey),
                               ('LINEABOVE', (0, -1), (1, -1), 0.5, colors.lightgrey),
                               ('TEXTCOLOR', (1, 1), (1, -3), colors.red),
                               ('TEXTCOLOR', (1, 1), (1, -4), colors.blue),
                               ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                               ('FONT', (0, 0), (0, 0), 'Times-Bold', 18), ]))
        return t

    def reportTable(self) -> Table:
        account = 0
        for r in self.rows:
            if r["flow"] == 1:
                account += float(r["bill"])
            else:
                account -= float(r["bill"])

        # reportlab needs sequences, so flatten the dict rows in column order
        data = [[r["supplier"], r["category"], r["reference"], r["flow"],
                 r["settled"], r["issued"], r["bill"]] for r in self.rows]
        data.insert(0, ['Supplier', 'Category', 'Reference', 'T', 'S', 'Issued', 'Bill'])
        data.insert(len(data), ['', '', '', 'account', '', round(account, 2), ''])

        t = Table(data, colWidths=(120, 70, 80, 30, 50, 80, 50),
                  hAlign='CENTER', splitByRow=1, repeatRows=2)
        t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                               ('ALIGN', (0, 1), (1, -1), 'LEFT'),
                               ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                               ('BOX', (0, 0), (-1, 0), 1.0, colors.black),
                               ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                               ('GRID', (0, 1), (-1, -2), 0.2, colors.black),
                               ('FONT', (0, 0), (-1, -1), 'Courier', 10),
                               ('FONT', (-2, -1), (-1, -1), 'Times-BoldItalic', 12),
                               ('TEXTCOLOR', (-2, -1), (-1, -1), colors.blue),
                               ('SPAN', (-2, -1), (-1, -1)),
                               ('SPAN', (-3, -1), (-4, -1)),
                               ('FONT', (-4, -1), (-3, -1), 'Times-BoldItalic', 12),
                               ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))

        bg = []
        for i, row in enumerate(data):
            if row[3] == 0:
                bg.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor('#FFE1E0')))
            elif row[3] == 1:
                bg.append(("BACKGROUND", (0, i), (-1, i), colors.lightgreen))
        t.setStyle(TableStyle(bg))
        return t

    def create_doc(self) -> str:
        """Build the PDF to a temp file and return its path."""
        self.story.append(self.reportHeader())
        self.story.append(Spacer(1, 0.2 * inch))
        self.story.append(self.reportTable())
        self.story.append(PageBreak())

        fd, path = tempfile.mkstemp(".pdf")
        os.close(fd)
        doc = SimpleDocTemplate(path, pagesize=(9.0 * inch, 11 * inch),
                                showBoundary=0, title=self.header.title)
        doc.build(self.story, onFirstPage=self._footer, onLaterPages=self._footer)
        return path
