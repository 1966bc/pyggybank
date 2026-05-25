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

import datetime
import os
import tempfile
import threading
from typing import Dict

import wx
import wx.adv
import wx.lib.dialogs
from wx.lib.wordwrap import wordwrap

from frames import update_data
from frames import lookup_manager
from frames.filter_panel import FilterPanel
import reports.rpt_flows


class Launcher(threading.Thread):
    """Open a generated file (xls) in its default app, off the GUI thread."""

    def __init__(self, path: str, app: "wx.App") -> None:
        threading.Thread.__init__(self)
        self.path = path
        self.app = app

    def run(self) -> None:
        self.app.engine.open_file(self.path)


class EventsList(wx.ListCtrl):
    """
    Virtual report list for the events grid.

    In LC_VIRTUAL mode wxPython calls OnGetItemText on the *list control*
    itself, so it must live here (not on the frame). Cell text is pulled from
    the presenter on demand; the control stores no row data.
    """

    def __init__(self, parent, presenter, **kwargs) -> None:
        super().__init__(parent, style=wx.LC_REPORT | wx.LC_VIRTUAL |
                         wx.LC_HRULES | wx.LC_VRULES, **kwargs)
        self.presenter = presenter

    def OnGetItemText(self, item: int, column: int) -> str:
        return self.presenter.cell(item, column)

    # an image list is assigned (sort arrows on the column headers); a virtual
    # list then requires these, or it asserts/segfaults while painting rows.
    # -1 means "no per-row icon".
    def OnGetItemImage(self, item: int) -> int:
        return -1

    def OnGetItemColumnImage(self, item: int, column: int) -> int:
        return -1


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

        # filter bar (owns every filter widget; builds a FlowFilter)
        self.filters = FilterPanel(p, self.presenter, self._on_filters_changed)

        # events grid (virtual: data lives in the presenter)
        self.stEvents = wx.StaticText(p, -1, 'Records')
        self.stEvents.SetFont(wx.Font(12, wx.FONTFAMILY_SWISS,
                                      wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.lstEvents = EventsList(p, self.presenter, size=(fw * 70, fw * 30))
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
        self.buttons = []
        for (id, label, help_text, handler) in buttons:
            b = wx.Button(p, id, label)
            b.SetToolTip(help_text)
            b.Bind(wx.EVT_BUTTON, handler)
            self.buttons.append(b)

        self._do_layout(p, sbb)

    # ------------------------------------------------------------------ #
    # construction helpers
    # ------------------------------------------------------------------ #
    def _build_menu(self) -> None:
        # menus mirror the action buttons and group by intent:
        # File (produce/maintain/quit, with a Database submenu) |
        # Edit (CRUD) | View (reload/filter) | Manage (lookup tables) | ? (info)
        menu_file = wx.Menu()
        menu_edit = wx.Menu()
        menu_view = wx.Menu()
        menu_manage = wx.Menu()
        menu_database = wx.Menu()
        menu_info = wx.Menu()

        # File
        self.Bind(wx.EVT_MENU, self.on_export,
                  menu_file.Append(-1, "Export to &Xls...\tCtrl+S", "export data in xls"))
        self.Bind(wx.EVT_MENU, self.on_preview,
                  menu_file.Append(-1, "&Print preview\tCtrl+P", "print preview"))
        menu_file.AppendSeparator()
        self.Bind(wx.EVT_MENU, self.OnOpenLogFile,
                  menu_file.Append(-1, "L&og file", "log info!"))

        # File > Database (maintenance: backup / compact / wipe)
        self.Bind(wx.EVT_MENU, self.OnBackup,
                  menu_database.Append(-1, "&Backup...\tCtrl+B", "save a copy of the database"))
        self.Bind(wx.EVT_MENU, self.OnCompact,
                  menu_database.Append(-1, "&Compact", "reclaim free space (VACUUM)"))
        menu_database.AppendSeparator()
        self.Bind(wx.EVT_MENU, self.OnClearTransactions,
                  menu_database.Append(-1, "Clear &transactions...", "delete ALL transactions"))
        menu_file.AppendSubMenu(menu_database, "&Database", "database maintenance")

        menu_file.AppendSeparator()
        self.Bind(wx.EVT_MENU, self.OnExit,
                  menu_file.Append(-1, "E&xit\tCtrl+Q", "Quit PyggyBank!"))

        # Edit (CRUD on the selected transaction)
        self.Bind(wx.EVT_MENU, self.on_add,
                  menu_edit.Append(-1, "&Add\tCtrl+N", "add record!"))
        self.Bind(wx.EVT_MENU, self.on_edit,
                  menu_edit.Append(-1, "&Edit\tCtrl+E", "edit selected record"))
        self.Bind(wx.EVT_MENU, self.on_delete,
                  menu_edit.Append(-1, "&Delete\tDel", "delete selected record"))

        # View (reload + display options)
        self.Bind(wx.EVT_MENU, self.on_refresh,
                  menu_view.Append(-1, "&Refresh\tF5", "reload data"))
        menu_view.AppendSeparator()
        self.miShowDisabled = menu_view.AppendCheckItem(
            -1, "Show &disabled", "include soft-deleted rows in the list")
        self.Bind(wx.EVT_MENU, self.OnShowDisabled, self.miShowDisabled)

        # Manage (lookup tables)
        self.Bind(wx.EVT_MENU, self.menuCategories,
                  menu_manage.Append(-1, "&Categories...", "update categories!"))
        self.Bind(wx.EVT_MENU, self.menuSuppliers,
                  menu_manage.Append(-1, "&Suppliers...", "update suppliers!"))

        # ? (info)
        self.Bind(wx.EVT_MENU, self.OnAbout, menu_info.Append(-1, "A&bout", "developer info!"))
        self.Bind(wx.EVT_MENU, self.OnLicence, menu_info.Append(-1, "C&opyleft", "copyleft info!"))

        menubar = wx.MenuBar()
        menubar.Append(menu_file, "&File")
        menubar.Append(menu_edit, "&Edit")
        menubar.Append(menu_view, "&View")
        menubar.Append(menu_manage, "&Manage")
        menubar.Append(menu_info, "?")
        self.SetMenuBar(menubar)

    def _do_layout(self, p: wx.Panel, sbb: wx.StaticBox) -> None:
        # filter bar on top; below it the list (left) and the action buttons
        # (right) — filters and actions are no longer interleaved.
        s1 = wx.BoxSizer(wx.VERTICAL)
        s1.Add(self.stEvents, 0, wx.EXPAND | wx.ALL, 2)
        s1.Add(self.lstEvents, 1, wx.EXPAND | wx.ALL, 2)

        s2 = wx.StaticBoxSizer(sbb, wx.VERTICAL)
        for b in self.buttons:
            s2.Add(b, 0, wx.EXPAND | wx.ALL, 5)

        middle = wx.BoxSizer(wx.HORIZONTAL)
        middle.Add(s1, 1, wx.EXPAND | wx.ALL, 6)
        middle.Add(s2, 0, wx.ALL, 6)

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(self.filters, 0, wx.EXPAND | wx.ALL, 6)
        root.Add(middle, 1, wx.EXPAND)

        p.SetSizer(root)
        root.Fit(self)
        root.SetSizeHints(self)

    # ------------------------------------------------------------------ #
    # MainView contract (called by the presenter)
    # ------------------------------------------------------------------ #
    def show_events(self, count: int, totals: Dict[str, float]) -> None:
        self.lstEvents.SetItemCount(count)
        self.lstEvents.Refresh()
        self.stEvents.SetLabel("Events %s" % count)
        self.StatusBar.SetStatusText('Wallet: %.2f' % totals['wallet'], 1)
        self.StatusBar.SetStatusText('In: %.2f Out: %.2f' % (totals['in'], totals['out']), 0)

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #
    def OnOpen(self) -> None:
        # presenter.open() resolves the oldest issued date as the lower bound;
        # the panel then drives the filter from oldest .. today (inclusive).
        self.presenter.open()
        self.filters.populate_combos()
        self.filters.set_period(self.presenter.filter.start_date,
                                datetime.datetime.now())
        self._on_filters_changed()

    def reload(self) -> None:
        """Called by the edit dialog after a save."""
        self.presenter.refresh()

    # ------------------------------------------------------------------ #
    # intent handlers (forward to the presenter)
    # ------------------------------------------------------------------ #
    def on_refresh(self, evt) -> None:
        self.OnOpen()

    def on_add(self, evt) -> None:
        obj = update_data.Dialog(self, self.presenter.controller)
        obj.OnOpen()
        obj.Center()
        obj.ShowModal()

    def on_edit(self, evt) -> None:
        row = self.lstEvents.GetFirstSelected()
        if row == -1:
            wx.GetApp().engine.answer_info(wx.GetApp().engine.no_select)
            return
        obj = update_data.Dialog(self, self.presenter.controller)
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
        rows = self.presenter.report_rows()
        info = self.presenter.report_header()
        header = reports.rpt_flows.ReportHeader(
            title=wx.GetApp().GetAppName(),
            logo=wx.GetApp().engine.logo,
            start_date=info['start_date'],
            end_date=info['end_date'],
            category=info['category'],
            supplier=info['supplier'],
            records=len(rows))
        path = reports.rpt_flows.GeneratePDF(rows, header).create_doc()
        Launcher(path, wx.GetApp()).start()

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
    # filter bar -> presenter
    # ------------------------------------------------------------------ #
    def _on_filters_changed(self) -> None:
        """The FilterPanel changed: hand the new FlowFilter to the presenter."""
        self.presenter.apply_filter(self.filters.get_filter())

    def OnShowDisabled(self, evt) -> None:
        """Menu toggle: include/exclude soft-deleted rows."""
        self.filters.set_show_disabled(evt.IsChecked())

    # ------------------------------------------------------------------ #
    # database maintenance (Database menu)
    # ------------------------------------------------------------------ #
    def OnBackup(self, evt) -> None:
        default = "pyggy-%s.db" % datetime.date.today().strftime("%Y%m%d")
        with wx.FileDialog(self, "Backup database", defaultFile=default,
                           wildcard="SQLite database (*.db)|*.db",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()
        if self.presenter.backup_database(path):
            wx.GetApp().engine.answer_info("Backup saved:\n%s" % path)
        else:
            wx.GetApp().engine.answer_info("Backup failed (see the log file).")

    def OnCompact(self, evt) -> None:
        if wx.GetApp().engine.ask("Compact the database now (VACUUM)?") != wx.ID_YES:
            wx.GetApp().engine.answer_info(wx.GetApp().engine.abort_by_user)
            return
        b = wx.GetApp().engine.busy(self)
        ok = self.presenter.compact_database()
        b = None
        wx.GetApp().engine.answer_info(
            "Database compacted." if ok else "Compact failed (see the log file).")

    def OnClearTransactions(self, evt) -> None:
        count = self.presenter.event_count()
        if count == 0:
            wx.GetApp().engine.answer_info("There are no transactions to clear.")
            return
        msg = ("Confirm operation:\nDelete ALL %s transactions?\n"
               "This cannot be undone — back up first." % count)
        if wx.GetApp().engine.ask(msg) != wx.ID_YES:
            wx.GetApp().engine.answer_info(wx.GetApp().engine.abort_by_user)
            return
        self.presenter.clear_transactions()
        wx.GetApp().engine.answer_info("All transactions deleted.")

    # ------------------------------------------------------------------ #
    # lookup managers (categories / suppliers)
    # ------------------------------------------------------------------ #
    def menuCategories(self, evt) -> None:
        self._open_lookup_manager('categories')

    def menuSuppliers(self, evt) -> None:
        self._open_lookup_manager('suppliers')

    def _open_lookup_manager(self, table: str) -> None:
        if wx.GetApp().engine.match_instance('lookup_manager') is True:
            return
        obj = lookup_manager.LookupManager(self, self.presenter.controller, table)
        wx.GetApp().engine.get_instance(obj)
        obj.OnOpen()
        obj.Show()
        obj.Center()

    # ------------------------------------------------------------------ #
    # info dialogs
    # ------------------------------------------------------------------ #
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
            # destroying the top window ends the main loop; wx then calls
            # App.OnExit(), which closes the database connection.
            self.Destroy()
