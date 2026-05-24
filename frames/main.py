#-----------------------------------------------------------------------------
# project:  pyggybank
# module:   main.py
# authors:  1966bc
# mailto:   [giuseppe.costanzi@gmail.com]
# modify:   2026 - ported to Python 3 / wxPython 4 (Phoenix)
# version:  3.0
# copyright: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
# license: wxWindows License
#-----------------------------------------------------------------------------

"""
This module provides the MainFrame class for pyggybank.
The MainFrame is the top window of the project and contains all the other
components.
"""

import os
import tempfile
import threading
from typing import Any, Dict, List, Tuple

import wx
import wx.adv
import wx.lib.mixins.listctrl
import wx.lib.dialogs
from wx.lib.wordwrap import wordwrap
import openpyxl

from frames import update_data
from frames import filters
import reports.rpt_flows


ID_FLOW = wx.NewIdRef()
ID_SETTLED = wx.NewIdRef()
ID_ENABLED = wx.NewIdRef()
ID_LIST = wx.NewIdRef()
ID_COMBO = wx.NewIdRef()
ID_OPTIONS = wx.NewIdRef()


class Launcher(threading.Thread):
    """Open a generated file (xls) in its default app, off the GUI thread."""

    def __init__(self, path: str, app: "wx.App") -> None:
        threading.Thread.__init__(self)
        self.path = path
        self.app = app

    def run(self) -> None:
        self.app.engine.open_file(self.path)


class MainFrame(wx.Frame, wx.lib.mixins.listctrl.ColumnSorterMixin):
    """PyggyBank main window."""

    def __init__(self) -> None:

        wx.Frame.__init__(self,
                          None,
                          wx.ID_ANY,
                          style=wx.GetApp().engine.frame_style(),
                          name='main')

        # set some frame attributes
        self.SetIcon(wx.Icon(wx.GetApp().engine.icon, wx.BITMAP_TYPE_ICO))
        self.SetTitle("%s %s" % (wx.GetApp().GetAppName(), wx.GetApp().engine.version))
        self.Bind(wx.EVT_CLOSE, self.OnExit)

        p = wx.Panel(self, -1)

        # menu
        menu_file = wx.Menu()
        menu_utilities = wx.Menu()
        menu_info = wx.Menu()

        item_exit = menu_file.Append(-1, "E&xit", "Quit PyggyBank!")
        self.Bind(wx.EVT_MENU, self.OnExit, item_exit)

        item_readme = menu_utilities.Append(-1, "Read me", "read me!")
        self.Bind(wx.EVT_MENU, self.OnRead, item_readme)
        item_category = menu_utilities.Append(-1, "Categories", "update categories!")
        self.Bind(wx.EVT_MENU, self.menuCategories, item_category)
        item_supplier = menu_utilities.Append(-1, "Suppliers", "update suppliers!")
        self.Bind(wx.EVT_MENU, self.menuSuppliers, item_supplier)
        item_log = menu_utilities.Append(-1, "L&og file", "log info!")
        self.Bind(wx.EVT_MENU, self.OnOpenLogFile, item_log)

        item_info = menu_info.Append(-1, "A&bout", "developer info!")
        self.Bind(wx.EVT_MENU, self.OnAbout, item_info)
        item_licence = menu_info.Append(-1, "C&opyleft", "copyleft info!")
        self.Bind(wx.EVT_MENU, self.OnLicence, item_licence)

        menubar = wx.MenuBar()
        menubar.Append(menu_file, "&File")
        menubar.Append(menu_utilities, "&Utilities")
        menubar.Append(menu_info, "?")
        self.SetMenuBar(menubar)

        # statusbar
        self.StatusBar = self.CreateStatusBar(1, wx.STB_SIZEGRIP)
        self.StatusBar.SetFieldsCount(2)
        self.StatusBar.SetStatusWidths([-8, -2])
        self.StatusBar.SetStatusText('Total:0', 1)

        # widgets
        self.calStartDate = wx.adv.DatePickerCtrl(p, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY)
        self.calStartDate.SetToolTip('start date!')
        self.calStartDate.Bind(wx.adv.EVT_DATE_CHANGED, self.on_date_changed)

        self.cbFilter = wx.ComboBox(p, ID_COMBO,
                                    size=(wx.GetApp().engine.get_font() * 20, -1),
                                    style=wx.CB_READONLY | wx.CB_DROPDOWN)
        self.cbFilter.Bind(wx.EVT_COMBOBOX, self.OnItemSelected)

        self.stEvents = wx.StaticText(p, -1, 'Records')
        self.stEvents.SetFont(wx.Font(12, wx.FONTFAMILY_SWISS,
                                      wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.lstEvents = wx.ListCtrl(p, ID_LIST,
                                     style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES,
                                     size=(wx.GetApp().engine.get_font() * 70,
                                           wx.GetApp().engine.get_font() * 30),)

        self.lstEvents.SetToolTip('Double click to edit!')
        self.lstEvents.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        self.lstEvents.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)

        # event_id is not shown as a column: it is stored as the item data
        # (see set_values) and used as the key into itemDataMap.
        fw = wx.GetApp().engine.get_font()
        self.lstEvents.InsertColumn(0, 'Flow', wx.LIST_FORMAT_CENTER, width=fw * 5)
        self.lstEvents.InsertColumn(1, 'Suppliers', wx.LIST_FORMAT_LEFT, width=fw * 10)
        self.lstEvents.InsertColumn(2, 'Category', wx.LIST_FORMAT_LEFT, width=fw * 10)
        self.lstEvents.InsertColumn(3, 'Settled', wx.LIST_FORMAT_CENTER, width=fw * 10)
        self.lstEvents.InsertColumn(4, 'Reference', wx.LIST_FORMAT_CENTER, width=fw * 10)
        self.lstEvents.InsertColumn(5, 'Currency', wx.LIST_FORMAT_CENTER, width=fw * 10)
        self.lstEvents.InsertColumn(6, 'Issued', wx.LIST_FORMAT_CENTER, width=fw * 10)

        # ListCtrl columns sort (transparent PNG arrows, no colour mask needed)
        self.itemDataMap: Dict[int, Tuple] = {}
        il = wx.ImageList(16, 16, True)
        self.up = il.Add(wx.Bitmap(wx.GetApp().engine.up_icon, wx.BITMAP_TYPE_PNG))
        self.dn = il.Add(wx.Bitmap(wx.GetApp().engine.down_icon, wx.BITMAP_TYPE_PNG))
        wx.lib.mixins.listctrl.ColumnSorterMixin.__init__(self, 7)
        self.lstEvents.AssignImageList(il, wx.IMAGE_LIST_SMALL)

        sbb = wx.StaticBox(p, wx.ID_ANY)

        bts = [(wx.ID_REFRESH, '&Refresh', 'reload data'),
               (wx.ID_ADD, '&Add ', 'add record!'),
               (wx.ID_EDIT, '&Edit', 'edit selected record'),
               (wx.ID_DELETE, '&Delete', 'delete selected record'),
               (wx.ID_PREVIEW, '&Preview', 'print preview'),
               (wx.ID_FILE, '&Xls', 'export data in xls'),
               (wx.ID_CLOSE, '&Close', 'close app'), ]

        for (id, label, help_text) in bts:
            b = wx.Button(p, id, label,)
            b.SetToolTip(help_text)
            b.Bind(wx.EVT_BUTTON, self.OnClick)

        cks = [(ID_FLOW, "FLow"),
               (ID_SETTLED, "Settled"),
               (ID_ENABLED, "Enabled"), ]

        for (id, label,) in cks:
            c = wx.CheckBox(p, id, label, style=(wx.CHK_3STATE | wx.CHK_ALLOW_3RD_STATE_FOR_USER))
            c.Bind(wx.EVT_CHECKBOX, self.OnClick)

        sbo = wx.StaticBox(p, wx.ID_ANY)
        ops = ['None', 'Categories', 'Suppliers']
        self.rbOptions = wx.RadioBox(p, ID_OPTIONS, "Combo filter",
                                     wx.DefaultPosition, wx.DefaultSize,
                                     ops, 3, wx.RA_SPECIFY_COLS | wx.NO_BORDER)
        self.rbOptions.Bind(wx.EVT_RADIOBOX, self.OnClick,)

        # sizers
        s0 = wx.BoxSizer(wx.HORIZONTAL)
        s1 = wx.BoxSizer(wx.VERTICAL)
        s2 = wx.StaticBoxSizer(sbb, wx.VERTICAL)
        s3 = wx.StaticBoxSizer(sbo, wx.VERTICAL)

        w = (self.rbOptions, self.cbFilter)
        for i in w:
            s3.Add(i, 0, wx.EXPAND | wx.ALL)

        w = (self.stEvents, self.lstEvents, s3,)
        for i in w:
            s1.Add(i, 0, wx.EXPAND | wx.ALL, 2)

        for i in p.GetChildren():
            if isinstance(i, (wx.adv.DatePickerCtrl, wx.Button, wx.CheckBox)):
                s2.Add(i, 0, wx.EXPAND | wx.ALL, 5)

        w = (s1, s2,)
        for i in w:
            s0.Add(i, 0, wx.ALL, 10)

        p.SetSizer(s0)
        s0.Fit(self)
        s0.SetSizeHints(self)

    def OnOpen(self) -> None:
        self.OnClick(self.FindWindowById(wx.ID_REFRESH))

    def OnClick(self, evt: wx.CommandEvent) -> None:
        """Dispatch every button/checkbox/radio click by its widget id."""

        if evt.GetId() == wx.ID_REFRESH:

            sql = "SELECT issued AS issued FROM events ORDER BY issued ASC LIMIT 1"
            rs = wx.GetApp().engine.read(False, sql, ())

            oldest = rs["issued"] if rs else None
            self.calStartDate.SetValue(wx.GetApp().engine.set_calendar_date(oldest))
            self.lst_transactions = None
            self.get_args()

        elif evt.GetId() == wx.ID_ADD:

            obj = update_data.Dialog(parent=self)
            obj.OnOpen()
            obj.Center()
            obj.ShowModal()

        elif evt.GetId() == wx.ID_EDIT:

            index = self.lstEvents.GetFirstSelected()

            if index != -1:
                obj = update_data.Dialog(parent=self)
                obj.OnOpen(self.selected_event)
                obj.Center()
                obj.ShowModal()
            else:
                wx.GetApp().engine.answer_info(wx.GetApp().engine.no_select)

        elif evt.GetId() == wx.ID_DELETE:

            index = self.lstEvents.GetFirstSelected()

            if index != -1:

                msg = ("Confirm operation:\nDelete transaction :\n%s"
                       % self.selected_event["reference"])

                if wx.GetApp().engine.ask(msg) == wx.ID_YES:

                    wx.GetApp().engine.write(wx.GetApp().engine.dict_queries['delete_transaction'],
                                             (self.selected_event["event_id"],))
                    self.get_args()
                else:
                    wx.GetApp().engine.answer_info(wx.GetApp().engine.abort_by_user)
            else:
                wx.GetApp().engine.answer_info(wx.GetApp().engine.no_select)

        elif evt.GetId() == ID_OPTIONS:

            if self.rbOptions.GetSelection() == 0:
                rs = []
                self.get_args()
            else:
                if self.rbOptions.GetSelection() == 1:
                    rs = wx.GetApp().engine.read(True, wx.GetApp().engine.dict_queries['cbo_categories'])
                elif self.rbOptions.GetSelection() == 2:
                    rs = wx.GetApp().engine.read(True, wx.GetApp().engine.dict_queries['cbo_suppliers'])

            self.set_values(ID_COMBO, rs)

        elif evt.GetId() in (ID_FLOW, ID_SETTLED, ID_ENABLED):
            self.get_args()

        elif evt.GetId() == wx.ID_PREVIEW:
            self.get_values((wx.ID_PREVIEW, True, wx.GetApp().engine.dict_queries['report'], self.args))

        elif evt.GetId() == wx.ID_FILE:

            # build excel file
            b = wx.GetApp().engine.busy(self)
            fd, path = tempfile.mkstemp(".xlsx")
            os.close(fd)

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = wx.GetApp().GetAppName()

            bold = wx.GetApp().engine.xls_style_font(True, False, 'Times New Roman')
            green = wx.GetApp().engine.xls_bg_colour("green")
            yellow = wx.GetApp().engine.xls_bg_colour("yellow")

            headers = ['FLOW', 'SETTLED', 'SUPPLIER', 'CATEGORY',
                       'REFERENCE', 'ISSUED', 'IN', 'OUT']
            for col, header in enumerate(headers, start=1):
                ws.cell(row=1, column=col, value=header)

            row = 2
            for i in self.rs:
                ws.cell(row=row, column=1, value=int(i["flow"]))
                ws.cell(row=row, column=2, value=int(i["settled"]))
                ws.cell(row=row, column=3, value=str(i["supplier"])).font = bold
                ws.cell(row=row, column=4, value=str(i["category"])).font = bold
                ws.cell(row=row, column=5, value=str(i["reference"]))
                ws.cell(row=row, column=6, value=str(i["issued"]))
                if int(i["flow"]) != 0:
                    ws.cell(row=row, column=7, value=float(i["bill"])).fill = green
                else:
                    ws.cell(row=row, column=8, value=float(i["bill"])).fill = yellow
                row += 1

            # some formula...
            ws.cell(row=row, column=7, value="=SUM(G2:G%d)" % (row - 1)).font = bold
            ws.cell(row=row, column=8, value="=SUM(H2:H%d)" % (row - 1)).font = bold
            c = ws.cell(row=row, column=9, value="=(G%d-H%d)" % (row, row))
            c.font = wx.GetApp().engine.xls_style_font(True, True, 'Times New Roman')

            wb.save(path)
            Launcher(path, wx.GetApp()).start()
            b = None

        elif evt.GetId() == wx.ID_CLOSE:
            self.OnExit(self)

    def on_date_changed(self, evt: "wx.adv.DateEvent") -> None:
        self.get_args()

    def OnItemSelected(self, evt: wx.CommandEvent) -> None:

        if evt.GetId() == ID_LIST:
            index = self.lstEvents.GetFirstSelected()
            if index != -1:
                pk = self.lstEvents.GetItemData(index)
                # make a dict for the selected row
                self.selected_event = wx.GetApp().engine.get_selected('events', 'event_id', pk)

        elif evt.GetId() == ID_COMBO:
            self.get_args()

    def OnItemActivated(self, evt: wx.ListEvent) -> None:
        self.OnClick(self.FindWindowById(wx.ID_EDIT))

    def get_args(self) -> None:
        """Collect the filter widgets state and (re)populate the ListCtrl."""

        self.args = (self.get_state(self.FindWindowById(ID_FLOW).Get3StateValue()),
                     self.get_state(self.FindWindowById(ID_SETTLED).Get3StateValue()),
                     self.get_state(self.FindWindowById(ID_ENABLED).Get3StateValue()),
                     self.get_combo_filter()[0], self.get_combo_filter()[1],
                     wx.GetApp().engine.get_calendar_date(self.calStartDate.GetValue()))

        self.get_values((ID_LIST, True, wx.GetApp().engine.dict_queries['flows'], self.args))

    def get_values(self, args: Tuple) -> None:
        """
        Run a query and route the result.

        Args:
            args[0]: widget id, args[1]: fetchall/fetchone,
            args[2]: sql statement, args[3]: sql arguments.
            wx.ID_PREVIEW builds the PDF report; anything else fills a widget.
        """

        rs = wx.GetApp().engine.read(args[1], args[2], args[3])

        if args[0] == wx.ID_PREVIEW:
            paper = reports.rpt_flows.GeneratePDF(rs, self.args, wx.GetApp())
            paper.create_doc()
        else:
            self.set_values(args[0], rs)

    def set_values(self, which: int, rs: List[Dict[str, Any]]) -> None:
        """Fill the events ListCtrl (and wallet totals) or the filter combo."""

        if which == ID_LIST:
            self.rs = rs
            self.wallet_in = 0
            self.wallet_out = 0
            self.lstEvents.DeleteAllItems()
            self.stEvents.SetLabel("Events %s" % (len(rs)))

            for i in rs:
                index = self.lstEvents.InsertItem(self.lstEvents.GetItemCount(), str(i["flow"]))
                self.lstEvents.SetItem(index, 1, str(i["supplier"]).strip())
                self.lstEvents.SetItem(index, 2, str(i["category"]).strip())
                self.lstEvents.SetItem(index, 3, str(i["settled"]))
                self.lstEvents.SetItem(index, 4, str(i["reference"]))
                # if flow = 1 add to wallet
                if i["flow"]:
                    self.wallet_in += i["bill"]
                else:
                    self.wallet_out += i["bill"]
                self.lstEvents.SetItem(index, 5, str(i["bill"]))
                self.lstEvents.SetItem(index, 6, str(i["issued"]))

                # store event_id as item data: it is the key into itemDataMap
                # (used by ColumnSorterMixin) and how we recover the PK on click
                self.lstEvents.SetItemData(index, i["event_id"])
                self.itemDataMap[i["event_id"]] = (i["flow"], i["supplier"], i["category"],
                                                   i["settled"], i["reference"], i["bill"],
                                                   i["issued"])
            # keep a reference to selected row
            if self.lst_transactions is not None:
                self.lstEvents.Select(self.lst_transactions, 1)
                self.lstEvents.EnsureVisible(self.lst_transactions)

            msg = 'Wallet: %s' % (self.wallet_in - self.wallet_out)
            self.StatusBar.SetStatusText(msg, 1)
            msg = 'In: %s Out: %s' % (self.wallet_in, self.wallet_out)
            self.StatusBar.SetStatusText(msg, 0)

        elif which == ID_COMBO:
            self.cbFilter.SetValue('')
            self.cbFilter.Clear()
            if rs:
                for i in rs:
                    values = list(i.values())
                    pk = int(values[0])
                    data = str(values[1]).strip()
                    self.cbFilter.Append(data, (pk, data))

    def get_state(self, state: int) -> Any:
        """Map a 3-state checkbox value to a SQL LIKE argument."""
        if state == 0:
            state = '%'
        elif state == 1:
            state = 1
        elif state == 2:
            state = 0

        return state

    def get_combo_filter(self) -> Tuple[Any, Any]:
        """
        Return the (supplier_id, category_id) LIKE arguments from the combo.

        '%' means "no filter". When the radio box selects a category/supplier
        filter but no combo item is chosen yet (GetSelection() == -1), fall
        back to no filter instead of crashing on GetClientData(-1).
        """
        supplier_id: Any = '%'
        category_id: Any = '%'

        option = self.rbOptions.GetSelection()
        if option == 0:
            return supplier_id, category_id

        selection = self.cbFilter.GetSelection()
        if selection == wx.NOT_FOUND:
            return supplier_id, category_id

        combo_id = int(self.cbFilter.GetClientData(selection)[0])
        if option == 1:
            category_id = combo_id
        elif option == 2:
            supplier_id = combo_id

        return supplier_id, category_id

    def menuCategories(self, evt: wx.CommandEvent) -> None:

        # checks if there's already an instance
        if wx.GetApp().engine.match_instance('filters') is True:
            return

        obj = filters.Frame(parent=self)
        wx.GetApp().engine.get_instance(obj)
        obj.OnOpen('categories', 'category_id')
        obj.Show()
        obj.Center()

    def menuSuppliers(self, evt: wx.CommandEvent) -> None:

        # checks if there's already an instance
        if wx.GetApp().engine.match_instance('filters') is True:
            return

        obj = filters.Frame(parent=self)
        wx.GetApp().engine.get_instance(obj)
        obj.OnOpen('suppliers', 'supplier_id')
        obj.Show()
        obj.Center()

    def GetListCtrl(self) -> wx.ListCtrl:
        return self.lstEvents

    def GetSortImages(self) -> Tuple[int, int]:
        return (self.dn, self.up)

    def OnRead(self, evt: wx.CommandEvent) -> None:
        try:
            with open('readme', "r") as f:
                msg = f.read()
        except IOError:
            msg = "Read me file doesn't exist!"
            wx.MessageBox(msg, wx.GetApp().GetAppName(), wx.OK | wx.ICON_INFORMATION)
            return

        dlg = wx.lib.dialogs.ScrolledMessageDialog(self, msg, "Read me")
        dlg.ShowModal()

    def OnAbout(self, evt: wx.CommandEvent) -> None:

        info = wx.adv.AboutDialogInfo()
        info.Name = wx.GetApp().engine.title
        info.Version = wx.GetApp().engine.version
        info.Copyright = wx.GetApp().engine.copyleft
        info.Description = wordwrap(wx.GetApp().engine.description, 350, wx.ClientDC(self))
        info.WebSite = (wx.GetApp().engine.web, wx.GetApp().engine.web)
        info.Developers = [wx.GetApp().engine.developer]

        wx.adv.AboutBox(info)

    def OnLicence(self, evt: wx.CommandEvent) -> None:

        with open(os.path.join(os.getcwd(), "copying"), "r") as f:
            msg = f.read()
        dlg = wx.lib.dialogs.ScrolledMessageDialog(self, msg, 'Copyleft')
        dlg.ShowModal()

    def OnOpenLogFile(self, evt: wx.CommandEvent) -> None:
        try:
            with open(wx.GetApp().engine.log, "r") as f:
                msg = f.read()
        except IOError:
            msg = "Log file doesn't exist!"
            wx.MessageBox(msg, wx.GetApp().GetAppName(), wx.OK | wx.ICON_INFORMATION)
            return

        dlg = wx.lib.dialogs.ScrolledMessageDialog(self, msg, "Log file")
        dlg.ShowModal()

    def OnExit(self, evt) -> None:
        msg = "Quit me?"
        ret = wx.MessageBox(msg, wx.GetApp().GetAppName(),
                            wx.YES_NO | wx.ICON_QUESTION | wx.CENTRE | wx.NO_DEFAULT)
        if ret == wx.YES:
            wx.GetApp().OnExit()
