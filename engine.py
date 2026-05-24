#!/usr/bin/env python3
"""
Engine module - main orchestrator for PyggyBank.

Engine extends the GUI-agnostic DBMS layer with the application's domain
queries and the wxPython helper functions shared across all frames. It is a
Singleton (one instance, reached through ``wx.GetApp().engine``).

Architecture:
    - DBMS:   database connection, query execution, SQL builders
    - Engine: domain queries, error logging to file, wx helpers, app constants

Author: 1966bc (Giuseppe Costanzi)
License: GNU GPL v3
Version: 3.0
"""

import os
import datetime
import traceback
import subprocess
from typing import Any, Dict, Optional, Tuple

import wx
from openpyxl.styles import Font, PatternFill

from dbms import DBMS

APP_TITLE = "PyggyBank"


class _EngineMeta(type):
    """Metaclass implementing the Singleton pattern for Engine."""

    _instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance


class Engine(DBMS, metaclass=_EngineMeta):
    """
    Singleton orchestrator: domain queries + wxPython helpers on top of DBMS.

    Example:
        >>> engine = Engine()           # opens pyggy.db next to this module
        >>> rows = engine.read(True, engine.dict_queries['suppliers'])
        >>> rows[0]['supplier']
        'ACI'
    """

    def __init__(self, database: Optional[str] = None, autocommit: bool = True) -> None:
        if database is None:
            database = self.get_file("pyggy.db")
        super().__init__(database=database, autocommit=autocommit)

        # domain SQL (column aliases keep dict keys clean)
        self.dict_queries: Dict[str, str] = {
            'flows': "SELECT event_id, flow, supplier, category, settled,"
                     " reference, bill,"
                     " strftime('%d-%m-%Y', issued) AS issued"
                     " FROM flows"
                     " WHERE flow LIKE ? AND settled LIKE ? AND enable LIKE ?"
                     " AND supplier_id LIKE ? AND category_id LIKE ? AND issued >= ?"
                     " ORDER BY issued DESC",
            'report': "SELECT supplier, category, reference, flow, settled,"
                      " strftime('%d-%m-%Y', issued) AS issued, bill"
                      " FROM flows"
                      " WHERE flow LIKE ? AND settled LIKE ? AND enable LIKE ?"
                      " AND supplier_id LIKE ? AND category_id LIKE ? AND issued >= ?"
                      " ORDER BY issued DESC",
            'suppliers': "SELECT * FROM suppliers ORDER BY supplier",
            'categories': "SELECT * FROM categories ORDER BY category",
            'cbo_suppliers': "SELECT * FROM suppliers WHERE enable = 1 ORDER BY supplier",
            'cbo_categories': "SELECT * FROM categories WHERE enable = 1 ORDER BY category",
            'category': "SELECT category FROM categories WHERE category_id = ?",
            'supplier': "SELECT supplier FROM suppliers WHERE supplier_id = ?",
            'delete_transaction': "DELETE FROM events WHERE event_id = ?",
        }

        # window registry (open frames)
        self.dict_instances: Dict[str, Any] = {}

        # app info / paths
        self.title = APP_TITLE
        self.version = '3.0'
        self.log = self.get_file("log.txt")
        self.icon = self.get_file("icons/app.ico")
        self.logo = self.get_file("images/report.gif")
        self.up_icon = self.get_file("icons/up.png")
        self.down_icon = self.get_file("icons/down.png")
        self.copyleft = "GNU GPL Version 3, 29 June 2007"
        self.developer = ("hal9000\n1966bc mailto[giuseppe.costanzi@gmail.com]"
                          "\nLocation:\nMilk Galaxy\nSolar System\nThird Planet "
                          "(Earth)\nItaly\nRome")
        self.description = "welcome on %s" % self.title
        self.web = "www.1966bc.wordpress.com"

        # UI palette / standard messages
        self.disable = (211, 211, 211)
        self.no_select = "Attention!\nNo record selected!"
        self.field_mandatory = "Attention!\nField %s is mandatory!"
        self.abort_by_user = "Operation aborted!"
        self.report_no_found = "Attention!\nReport not found!"

    def __str__(self) -> str:
        return "class: {0}\napp title: {1}\nversion: {2}".format(
            self.__class__.__name__, self.title, self.version)

    # ------------------------------------------------------------------ #
    # paths & logging
    # ------------------------------------------------------------------ #
    def get_file(self, filename: str) -> str:
        """Return the full path of a file living next to this module."""
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

    def get_log_file(self) -> str:
        """Return the log file path."""
        return self.get_file("log.txt")

    def on_log(self, function: str, exc_value: Exception, exc_type: type,
               module: Any, caller: str = None) -> None:
        """Append the error to log.txt with timestamp and traceback."""
        try:
            ts = datetime.datetime.now().astimezone().isoformat(
                sep=" ", timespec="seconds")
            module_name = getattr(module, "__name__", str(module))
            header = "{0}\n{1}.{2}".format(ts, type(self).__name__, function)
            if caller:
                header += "  (caller: {0})".format(caller)
            log_text = "{0}\n{1}: {2}\n{3}\n{4}\n".format(
                header, exc_type.__name__, exc_value, module_name,
                traceback.format_exc())
            with open(self.get_log_file(), "a",
                      encoding="utf-8", errors="backslashreplace") as fh:
                fh.write(log_text)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # wx calendar helpers
    # ------------------------------------------------------------------ #
    def get_calendar_date(self, my_calendar: "wx.DateTime",
                          get_time: bool = False) -> datetime.datetime:
        """Convert a wx.DateTime (from a DatePickerCtrl) to a datetime."""
        now = datetime.datetime.now()
        if get_time:
            return datetime.datetime(my_calendar.GetYear(),
                                     my_calendar.GetMonth() + 1,
                                     my_calendar.GetDay(),
                                     now.hour, now.minute, now.second)
        return datetime.datetime(my_calendar.GetYear(),
                                 my_calendar.GetMonth() + 1,
                                 my_calendar.GetDay())

    def set_calendar_date(self, my_date: Any) -> "wx.DateTime":
        """Convert a datetime/str (from the DB) to a wx.DateTime."""
        if my_date is None:
            return wx.DateTime.Today()
        if isinstance(my_date, str):
            try:
                my_date = datetime.datetime.strptime(my_date, "%Y-%m-%d")
            except ValueError as v:
                ulr = len(v.args[0].partition('unconverted data remains: ')[2])
                if ulr:
                    my_date = datetime.datetime.strptime(my_date[:-ulr], "%Y-%m-%d")
                else:
                    raise
        return wx.DateTime.FromDMY(my_date.day, my_date.month - 1, my_date.year)

    # ------------------------------------------------------------------ #
    # wx combo helpers
    # ------------------------------------------------------------------ #
    def get_combo_id(self, caller: Any, widget_id: int) -> int:
        """Return the primary key stored as client data of the combo selection."""
        widget = caller.FindWindowById(widget_id)
        return int(widget.GetClientData(widget.GetSelection())[0])

    def set_combo(self, d: Dict[int, Tuple], caller: Any) -> None:
        """
        Populate one or more combos.

        Args:
            d: {widget_id: (store_dict, sql, args, with_nothing)}
               store_dict maps primary key -> combo index.
            caller: the frame owning the combos.
        """
        for widget_id, (store, sql, args, with_nothing) in d.items():
            combo = caller.FindWindowById(widget_id)
            if with_nothing is not None:
                combo.Append('Nothing', (0, 'Nothing'))
            for row in self.read(True, sql, args) or []:
                values = list(row.values())
                pk = int(values[0])
                showed = str(values[1]).strip()
                combo.Append(showed, (pk, showed))
            for index in range(combo.GetCount()):
                store[int(combo.GetClientData(index)[0])] = index

    # ------------------------------------------------------------------ #
    # xls (openpyxl) styling
    # ------------------------------------------------------------------ #
    def xls_bg_colour(self, colour: str) -> PatternFill:
        """Return a solid openpyxl PatternFill for the given colour name."""
        dict_colour = {"green": "92D050", "red": "FF0000", "white": "FFFFFF",
                       "yellow": "FFFF00", "gray": "BFBFBF", "blue": "0070C0",
                       "magenta": "FF00FF", "cyan": "00FFFF"}
        hex_colour = dict_colour[colour]
        return PatternFill(start_color=hex_colour, end_color=hex_colour,
                           fill_type="solid")

    def xls_style_font(self, is_bold: bool, is_underline: bool,
                       font_name: str) -> Font:
        """Return an openpyxl Font."""
        return Font(name=font_name, bold=bool(is_bold),
                    underline='single' if is_underline else 'none')

    # ------------------------------------------------------------------ #
    # window registry
    # ------------------------------------------------------------------ #
    def get_instance(self, which: Any) -> None:
        self.dict_instances[which.GetName()] = which

    def del_instance(self, which: Any) -> None:
        self.dict_instances.pop(which.GetName(), None)

    def match_instance(self, which: str) -> bool:
        return which in self.dict_instances

    # ------------------------------------------------------------------ #
    # misc wx helpers
    # ------------------------------------------------------------------ #
    def open_file(self, path: str) -> None:
        if os.path.exists(path):
            if os.name == 'posix':
                subprocess.call(["xdg-open", path])
            else:
                os.startfile(path)
        else:
            wx.MessageBox(self.report_no_found, self.title,
                          wx.OK | wx.ICON_INFORMATION)

    def busy(self, caller: Any) -> "wx.BusyInfo":
        return wx.BusyInfo("Attendere prego!\ncaricamento dati in corso...")

    def ask(self, msg: str) -> int:
        return wx.MessageDialog(None, msg, self.title,
                                wx.YES_NO | wx.ICON_QUESTION).ShowModal()

    def answer_info(self, msg: str) -> int:
        return wx.MessageBox(msg, self.title, wx.OK | wx.ICON_INFORMATION)

    def fields_control(self, d: Dict[Any, str]) -> Optional[int]:
        for widget, label in d.items():
            if len(widget.GetValue()) == 0:
                self.answer_info(self.field_mandatory % label)
                widget.SetFocus()
                return 0

    def get_font(self) -> int:
        try:
            fw = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT).GetPointSize() + 1
        except Exception:
            fw = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT).GetPointSize() + 1
        return fw

    def frame_style(self) -> int:
        return (wx.DEFAULT_FRAME_STYLE ^
                (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX) |
                wx.FRAME_FLOAT_ON_PARENT)


def main():
    engine = Engine()
    print(engine)
    print(engine.con)
    rs = engine.read(True, "SELECT name FROM sqlite_master WHERE type = 'table'")
    if rs:
        for row in rs:
            print(row["name"])
    engine.close()


if __name__ == "__main__":
    main()
