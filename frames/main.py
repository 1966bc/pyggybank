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
MainFrame: the top window of PyggyBank.

This is a *passive view* (it implements presenters.MainView): it builds widgets,
forwards user intent to its MainPresenter, and renders whatever the presenter
tells it. It owns NO data access — it never touches SQL or the DBMS; the events
grid is virtual (wx.LC_VIRTUAL) and pulls cell text from the presenter on demand.

UI services that are not data (icon, font, frame style, xls styling) still come
from the app context (wx.GetApp().engine).
"""

import os
import tempfile
import threading
from typing import Dict

import wx
import wx.adv
import wx.lib.dialogs
from wx.lib.wordwrap import wordwrap

from frames import update_data
from frames import filters
import reports.rpt_flows


ID_FLOW = wx.NewIdRef()
ID_SETTLED = wx.NewIdRef()
ID_ENABLED = wx.NewIdRef()
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


class MainFrame(wx.Frame):
    """PyggyBank main window — passive view over a MainPresenter."""

    def __init__(self, presenter) -> None:

        wx.Frame.__init__(self,
                          None,
                          wx.ID_ANY,
                          style=wx.GetApp().engine.frame_style(),
                          name='main')

        self.presenter = presenter

        self.SetIcon(wx.Icon(wx.GetApp().engine.icon, wx.BITMAP_TYPE_ICO))
        self.SetTitle("%s %s" % (wx.GetApp().GetAppName(), wx.GetApp().engine.version))
        self.Bind(wx.EVT_CLOSE, self.OnExit)

        # sort indicator state (which column shows the arrow)
        self._sort_col = -1
        self._sort_asc = True

        p = wx.Panel(self, -1)
        self._build_menu()

        # statusbar
        self.StatusBar = self.CreateStatusBar(1, wx.STB_SIZEGRIP)
        self.StatusBar.SetFieldsCount(2)
        self.StatusBar.SetStatusWidths([-8, -2])
        self.StatusBar.SetStatusText('Total:0', 1)

        fw = wx.GetApp().engine.get_font()

        # filter widgets
        self.calStartDate = wx.adv.DatePickerCtrl(p, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY)
        self.calStartDate.SetToolTip('start date!')
        self.calStartDate.Bind(wx.adv.EVT_DATE_CHANGED, self._on_filter_changed)

        self.cbFilter = wx.ComboBox(p, ID_COMBO, size=(fw * 20, -1),
                                    style=wx.CB_READONLY | wx.CB_DROPDOWN)
        self.cbFilter.Bind(wx.EVT_COMBOBOX, self._on_filter_changed)

        # events grid (virtual: data lives in the presenter)
        self.stEvents = wx.StaticText(p, -1, 'Records')
        self.stEvents.SetFont(wx.Font(12, wx.FONTFAMILY_SWISS,
                                      wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.lstEvents = wx.ListCtrl(
            p, -1,
            style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_HRULES | wx.LC_VRULES,
            size=(fw * 70, fw * 30))
        self.lstEvents.SetToolTip('Double click to edit!')
        self.lstEvents.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_edit)
        self.lstEvents.Bind(wx.EVT_LIST_COL_CLICK, self.on_sort)

        for col, (header, _key) in enumerate(self.presenter.COLUMNS):
            fmt = wx.LIST_FORMAT_LEFT if col in (1, 2) else wx.LIST_FORMAT_CENTER
            self.lstEvents.InsertColumn(col, header, fmt, width=fw * (5 if col == 0 else 10))

        # sort-arrow images on the column headers
        il = wx.ImageList(16, 16, True)
        self.up = il.Add(wx.Bitmap(wx.GetApp().engine.up_icon, wx.BITMAP_TYPE_PNG))
        self.dn = il.Add(wx.Bitmap(wx.GetApp().engine.down_icon, wx.BITMAP_TYPE_PNG))
        self.lstEvents.AssignImageList(il, wx.IMAGE_LIST_SMALL)

        # buttons
        sbb = wx.StaticBox(p, wx.ID_ANY)
        buttons = [(wx.ID_REFRESH, '&Refresh', 'reload data', self.on_refresh),
                   (wx.ID_ADD, '&Add ', 'add record!', self.on_add),
                   (wx.ID_EDIT, '&Edit', 'edit selected record', self.on_edit),
                   (wx.ID_DELETE, '&Delete', 'delete selected record', self.on_delete),
                   (wx.ID_PREVIEW, '&Preview', 'print preview', self.on_preview),
                   (wx.ID_FILE, '&Xls', 'export data in xls', self.on_export),
                   (wx.ID_CLOSE, '&Close', 'close app', self.on_close)]
        for (id, label, help_text, handler) in buttons:
            b = wx.Button(p, id, label)
            b.SetToolTip(help_text)
            b.Bind(wx.EVT_BUTTON, handler)

        # tri-state filter checkboxes
        ck_style = wx.CHK_3STATE | wx.CHK_ALLOW_3RD_STATE_FOR_USER
        self.ckFlow = wx.CheckBox(p, ID_FLOW, "Flow", style=ck_style)
        self.ckSettled = wx.CheckBox(p, ID_SETTLED, "Settled", style=ck_style)
        self.ckEnabled = wx.CheckBox(p, ID_ENABLED, "Enabled", style=ck_style)
        for cb in (self.ckFlow, self.ckSettled, self.ckEnabled):
            cb.Bind(wx.EVT_CHECKBOX, self._on_filter_changed)

        sbo = wx.StaticBox(p, wx.ID_ANY)
        self.rbOptions = wx.RadioBox(p, ID_OPTIONS, "Combo filter",
                                     wx.DefaultPosition, wx.DefaultSize,
                                     ['None', 'Categories', 'Suppliers'], 3,
                                     wx.RA_SPECIFY_COLS | wx.NO_BORDER)
        self.rbOptions.Bind(wx.EVT_RADIOBOX, self._on_mode_changed)

        self._do_layout(p, sbb, sbo)

    # ------------------------------------------------------------------ #
    # construction helpers
    # ------------------------------------------------------------------ #
    def _build_menu(self) -> None:
        menu_file = wx.Menu()
        menu_utilities = wx.Menu()
        menu_info = wx.Menu()

        self.Bind(wx.EVT_MENU, self.OnExit, menu_file.Append(-1, "E&xit", "Quit PyggyBank!"))
        self.Bind(wx.EVT_MENU, self.OnRead, menu_utilities.Append(-1, "Read me", "read me!"))
        self.Bind(wx.EVT_MENU, self.menuCategories, menu_utilities.Append(-1, "Categories", "update categories!"))
        self.Bind(wx.EVT_MENU, self.menuSuppliers, menu_utilities.Append(-1, "Suppliers", "update suppliers!"))
        self.Bind(wx.EVT_MENU, self.OnOpenLogFile, menu_utilities.Append(-1, "L&og file", "log info!"))
        self.Bind(wx.EVT_MENU, self.OnAbout, menu_info.Append(-1, "A&bout", "developer info!"))
        self.Bind(wx.EVT_MENU, self.OnLicence, menu_info.Append(-1, "C&opyleft", "copyleft info!"))

        menubar = wx.MenuBar()
        menubar.Append(menu_file, "&File")
        menubar.Append(menu_utilities, "&Utilities")
        menubar.Append(menu_info, "?")
        self.SetMenuBar(menubar)

    def _do_layout(self, p: wx.Panel, sbb: wx.StaticBox, sbo: wx.StaticBox) -> None:
        s0 = wx.BoxSizer(wx.HORIZONTAL)
        s1 = wx.BoxSizer(wx.VERTICAL)
        s2 = wx.StaticBoxSizer(sbb, wx.VERTICAL)
        s3 = wx.StaticBoxSizer(sbo, wx.VERTICAL)

        for i in (self.rbOptions, self.cbFilter):
            s3.Add(i, 0, wx.EXPAND | wx.ALL)
        for i in (self.stEvents, self.lstEvents, s3):
            s1.Add(i, 0, wx.EXPAND | wx.ALL, 2)
        for i in p.GetChildren():
            if isinstance(i, (wx.adv.DatePickerCtrl, wx.Button, wx.CheckBox)):
                s2.Add(i, 0, wx.EXPAND | wx.ALL, 5)
        for i in (s1, s2):
            s0.Add(i, 0, wx.ALL, 10)

        p.SetSizer(s0)
        s0.Fit(self)
        s0.SetSizeHints(self)

    # ------------------------------------------------------------------ #
    # MainView contract (called by the presenter)
    # ------------------------------------------------------------------ #
    def show_events(self, count: int, totals: Dict[str, float]) -> None:
        self.lstEvents.SetItemCount(count)
        self.lstEvents.Refresh()
        self.stEvents.SetLabel("Events %s" % count)
        self.StatusBar.SetStatusText('Wallet: %s' % totals['wallet'], 1)
        self.StatusBar.SetStatusText('In: %s Out: %s' % (totals['in'], totals['out']), 0)

    # virtual list: pull cell text from the presenter on demand
    def OnGetItemText(self, item: int, column: int) -> str:
        return self.presenter.cell(item, column)

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #
    def OnOpen(self) -> None:
        self.presenter.open()
        self.calStartDate.SetValue(
            wx.GetApp().engine.set_calendar_date(self.presenter.filter.start_date))

    def reload(self) -> None:
        """Called by the edit dialog after a save."""
        self.presenter.refresh()

    # ------------------------------------------------------------------ #
    # intent handlers (forward to the presenter)
    # ------------------------------------------------------------------ #
    def on_refresh(self, evt) -> None:
        self.OnOpen()

    def on_add(self, evt) -> None:
        obj = update_data.Dialog(parent=self)
        obj.OnOpen()
        obj.Center()
        obj.ShowModal()

    def on_edit(self, evt) -> None:
        row = self.lstEvents.GetFirstSelected()
        if row == -1:
            wx.GetApp().engine.answer_info(wx.GetApp().engine.no_select)
            return
        obj = update_data.Dialog(parent=self)
        obj.OnOpen(self.presenter.get_event(row))
        obj.Center()
        obj.ShowModal()

    def on_delete(self, evt) -> None:
        row = self.lstEvents.GetFirstSelected()
        if row == -1:
            wx.GetApp().engine.answer_info(wx.GetApp().engine.no_select)
            return
        msg = "Confirm operation:\nDelete transaction :\n%s" % self.presenter.cell(row, 4)
        if wx.GetApp().engine.ask(msg) == wx.ID_YES:
            self.presenter.delete_event(row)
        else:
            wx.GetApp().engine.answer_info(wx.GetApp().engine.abort_by_user)

    def on_preview(self, evt) -> None:
        paper = reports.rpt_flows.GeneratePDF(
            self.presenter.report_rows(), self.presenter.report_args(), wx.GetApp())
        paper.create_doc()

    def on_export(self, evt) -> None:
        b = wx.GetApp().engine.busy(self)
        fd, path = tempfile.mkstemp(".xlsx")
        os.close(fd)
        self.presenter.export_xlsx(path)
        Launcher(path, wx.GetApp()).start()
        b = None

    def on_close(self, evt) -> None:
        self.OnExit(self)

    def on_sort(self, evt: wx.ListEvent) -> None:
        col = evt.GetColumn()
        if col == self._sort_col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col, self._sort_asc = col, True
        self.presenter.sort(col, self._sort_asc)
        for c in range(self.lstEvents.GetColumnCount()):
            self.lstEvents.ClearColumnImage(c)
        self.lstEvents.SetColumnImage(col, self.up if self._sort_asc else self.dn)

    # ------------------------------------------------------------------ #
    # filter widgets -> presenter
    # ------------------------------------------------------------------ #
    @staticmethod
    def _tri_state(cb: wx.CheckBox):
        value = cb.Get3StateValue()
        if value == wx.CHK_UNCHECKED:
            return None          # any
        if value == wx.CHK_CHECKED:
            return True
        return False             # CHK_UNDETERMINED

    def _filter_state(self) -> dict:
        supplier_id = '%'
        category_id = '%'
        mode = self.rbOptions.GetSelection()
        if mode != 0:
            sel = self.cbFilter.GetSelection()
            if sel != wx.NOT_FOUND:
                combo_id = int(self.cbFilter.GetClientData(sel)[0])
                if mode == 1:
                    category_id = combo_id
                elif mode == 2:
                    supplier_id = combo_id
        return dict(
            flow=self._tri_state(self.ckFlow),
            settled=self._tri_state(self.ckSettled),
            enabled=self._tri_state(self.ckEnabled),
            supplier_id=supplier_id,
            category_id=category_id,
            start_date=wx.GetApp().engine.get_calendar_date(self.calStartDate.GetValue()))

    def _on_filter_changed(self, evt) -> None:
        self.presenter.set_filter(**self._filter_state())

    def _on_mode_changed(self, evt) -> None:
        self._populate_combo()
        self._on_filter_changed(evt)

    def _populate_combo(self) -> None:
        self.cbFilter.SetValue('')
        self.cbFilter.Clear()
        mode = self.rbOptions.GetSelection()
        if mode == 0:
            return
        rows = self.presenter.categories() if mode == 1 else self.presenter.suppliers()
        for r in rows:
            values = list(r.values())
            self.cbFilter.Append(str(values[1]).strip(), (int(values[0]), str(values[1]).strip()))

    # ------------------------------------------------------------------ #
    # lookup managers (categories / suppliers)
    # ------------------------------------------------------------------ #
    def menuCategories(self, evt) -> None:
        if wx.GetApp().engine.match_instance('filters') is True:
            return
        obj = filters.Frame(parent=self)
        wx.GetApp().engine.get_instance(obj)
        obj.OnOpen('categories', 'category_id')
        obj.Show()
        obj.Center()

    def menuSuppliers(self, evt) -> None:
        if wx.GetApp().engine.match_instance('filters') is True:
            return
        obj = filters.Frame(parent=self)
        wx.GetApp().engine.get_instance(obj)
        obj.OnOpen('suppliers', 'supplier_id')
        obj.Show()
        obj.Center()

    # ------------------------------------------------------------------ #
    # info dialogs
    # ------------------------------------------------------------------ #
    def OnRead(self, evt) -> None:
        try:
            with open('readme', "r") as f:
                msg = f.read()
        except IOError:
            wx.MessageBox("Read me file doesn't exist!", wx.GetApp().GetAppName(),
                          wx.OK | wx.ICON_INFORMATION)
            return
        wx.lib.dialogs.ScrolledMessageDialog(self, msg, "Read me").ShowModal()

    def OnAbout(self, evt) -> None:
        info = wx.adv.AboutDialogInfo()
        info.Name = wx.GetApp().engine.title
        info.Version = wx.GetApp().engine.version
        info.Copyright = wx.GetApp().engine.copyleft
        info.Description = wordwrap(wx.GetApp().engine.description, 350, wx.ClientDC(self))
        info.WebSite = (wx.GetApp().engine.web, wx.GetApp().engine.web)
        info.Developers = [wx.GetApp().engine.developer]
        wx.adv.AboutBox(info)

    def OnLicence(self, evt) -> None:
        with open(os.path.join(os.getcwd(), "copying"), "r") as f:
            msg = f.read()
        wx.lib.dialogs.ScrolledMessageDialog(self, msg, 'Copyleft').ShowModal()

    def OnOpenLogFile(self, evt) -> None:
        try:
            with open(wx.GetApp().engine.log, "r") as f:
                msg = f.read()
        except IOError:
            wx.MessageBox("Log file doesn't exist!", wx.GetApp().GetAppName(),
                          wx.OK | wx.ICON_INFORMATION)
            return
        wx.lib.dialogs.ScrolledMessageDialog(self, msg, "Log file").ShowModal()

    def OnExit(self, evt) -> None:
        ret = wx.MessageBox("Quit me?", wx.GetApp().GetAppName(),
                            wx.YES_NO | wx.ICON_QUESTION | wx.CENTRE | wx.NO_DEFAULT)
        if ret == wx.YES:
            wx.GetApp().OnExit()
