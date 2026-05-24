#-----------------------------------------------------------------------------
# project:  pyggy bank
# module:   rpt_flows.py
# authors:  giuseppe costanzi aka 1966bc
# mailto:   [giuseppe.costanzi@gmail.com]
# modify:   2026 - ported to Python 3 / reportlab 4
# version:  3.0
# description: report data
#-----------------------------------------------------------------------------

import os
import datetime
import tempfile
import threading
from typing import Dict, List, Tuple

from reportlab.platypus import Spacer, SimpleDocTemplate, Table, TableStyle
from reportlab.platypus.flowables import Image, PageBreak
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4


class Launcher(threading.Thread):
    def __init__(self, path: str, app: "wx.App") -> None:
        threading.Thread.__init__(self)
        self.app = app
        self.path = path

    def run(self) -> None:
        self.app.engine.open_file(self.path)


class GeneratePDF:
    def __init__(self, rs: List[Dict], args: Tuple, app: "wx.App") -> None:

        self.app = app
        self.rs = rs
        self.args = args
        self.today = datetime.date.today()
        self.start_date = args[5]

        if self.args[4] != '%':
            row = self.app.engine.read(False,
                                       self.app.engine.dict_queries['category'],
                                       (self.args[4],))
            self.category = str(row["category"])
        else:
            self.category = 'No select'

        if self.args[3] != '%':
            row = self.app.engine.read(False,
                                       self.app.engine.dict_queries['supplier'],
                                       (self.args[3],))
            self.supplier = str(row["supplier"])
        else:
            self.supplier = 'No select'

        self.story = []

    def first_page(self, canvas, doc) -> None:

        canvas.saveState()
        canvas.setFont('Courier', 9)
        canvas.drawString(inch, 0.75 * inch, "%s - %s" % (self.today.strftime('%d/%m/%Y'),
                                                          canvas.getPageNumber()))
        canvas.drawString(490, 0.75 * inch, "his Majesty")
        canvas.setFont('Times-Bold', 8)
        canvas.drawCentredString(0.5 * A4[0], 0.5 * inch, "%s" % self.app.GetAppName())
        canvas.restoreState()

    def later_pages(self, canvas, doc) -> None:

        canvas.saveState()
        canvas.setFont('Courier', 9)
        canvas.drawString(inch, 0.75 * inch, "%s - %s" % (self.today.strftime('%d/%m/%Y'),
                                                          canvas.getPageNumber()))
        canvas.drawString(490, 0.75 * inch, "his Majesty")

        canvas.setFont('Times-Bold', 8)
        canvas.drawCentredString(0.5 * A4[0], 0.5 * inch, "%s" % self.app.GetAppName())
        canvas.restoreState()

    def reportHeader(self) -> Table:

        reportLogo = Image(self.app.engine.logo)
        reportLogo.drawHeight = 0.80 * inch
        reportLogo.drawWidth = 1.20 * inch

        t = Table((('Data Report', '', [reportLogo]),
                   ("Start Date", self.start_date.strftime('%d/%m/%Y'), ''),
                   ("Category", self.category, ''),
                   ("Supplier", self.supplier, ''),
                   ("Records", len(self.rs), '')),
                  # colWidths, rowHeights,
                  (80, 80, 250),
                  (18, 18, 18, 18, 18,))
        # ('SPAN',(2,0),(2,-1)) expand image
        t.setStyle(TableStyle([  # column, row
                               ('SPAN', (2, 0), (2, -1)),
                               ('BOX', (0, 1), (1, -1), 0.5, colors.lightgrey),
                               ('LINEABOVE', (0, -1), (1, -1), 0.5, colors.lightgrey),
                               ('TEXTCOLOR', (1, 1), (1, -3), colors.red),
                               ('TEXTCOLOR', (1, 1), (1, -4), colors.blue),
                               ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                               ('FONT', (0, 0), (0, 0), 'Times-Bold', 18), ]))
        return t

    def reportTable(self) -> Table:

        account = 0
        for i in self.rs:
            if i["flow"] == 1:
                account += float(i["bill"])
            else:
                account -= float(i["bill"])

        # reportlab needs sequences, so flatten the dict rows in column order
        data = [[r["supplier"], r["category"], r["reference"], r["flow"],
                 r["settled"], r["issued"], r["bill"]] for r in self.rs]

        fields = ['Supplier', 'Category', 'Reference', 'T', 'S', 'Issued', 'Bill']
        data.insert(0, fields)
        data.insert(len(data), ['', '', '', 'account', '', round(account, 2), ''])
        self.rs = data
        t = Table(data,
                  colWidths=(120, 70, 80, 30, 50, 80, 50),
                  hAlign='CENTER', splitByRow=1,
                  repeatRows=2)

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

        args = []
        for i, row in enumerate(self.rs):
            if row[3] == 0:
                args.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor('#FFE1E0')))
            elif row[3] == 1:
                args.append(("BACKGROUND", (0, i), (-1, i), colors.lightgreen))
            else:
                pass

        t.setStyle(TableStyle(args))

        return t

    def create_doc(self) -> None:

        self.story.append(self.reportHeader())
        self.story.append(Spacer(1, 0.2 * inch))
        self.story.append(self.reportTable())
        self.story.append(PageBreak())
        self.build_document()

    def build_document(self) -> None:

        fd, path = tempfile.mkstemp(".pdf")
        os.close(fd)

        doc = SimpleDocTemplate(path,
                                pagesize=(9.0 * inch, 11 * inch),
                                showBoundary=0,
                                title=self.app.GetAppName())
        doc.build(self.story,
                  onFirstPage=self.first_page,
                  onLaterPages=self.later_pages)
        Launcher(path, self.app).start()
