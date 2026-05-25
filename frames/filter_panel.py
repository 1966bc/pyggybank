#-----------------------------------------------------------------------------
# project:  pyggybank
# module:   filter_panel.py
# authors:  1966bc
# version:  3.0
# copyright: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
# license: wxWindows License
#-----------------------------------------------------------------------------

"""
FilterPanel: the events-list filter bar, extracted out of MainFrame.

It owns every filter widget, grouped by logical family (Period / Movement /
Dimensions), and exposes a single contract to the frame:

    get_filter() -> FlowFilter        build a domain filter from the widgets
    set_period(start, end)            sync the Da/A date pickers
    set_show_disabled(bool)           reflect the menu toggle (enable flag)
    populate_combos()                 fill the category / supplier combos

Any user change fires the `on_change` callback passed at construction; the
frame just forwards it to the presenter. The panel imports wxPython but no SQL
and no DBMS: data comes from the presenter, value objects from models.
"""

import datetime
from typing import Any, Callable, Optional

import wx
import wx.adv

from models import FlowFilter


class FilterPanel(wx.Panel):
    """Grouped filter bar over the events list (a passive widget container)."""

    # radio index -> tri-state value (None means "any")
    _TRI = {0: None, 1: True, 2: False}

    def __init__(self, parent, presenter, on_change: Callable[[], None]) -> None:
        super().__init__(parent, wx.ID_ANY)
        self.presenter = presenter
        self.on_change = on_change
        self._show_disabled = False

        engine = wx.GetApp().engine
        fw = engine.get_font()

        # --- Period --------------------------------------------------- #
        self.calStart = wx.adv.DatePickerCtrl(
            self, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY)
        self.calEnd = wx.adv.DatePickerCtrl(
            self, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY)
        self.calStart.SetToolTip('from date (inclusive)')
        self.calEnd.SetToolTip('to date (inclusive)')
        for cal in (self.calStart, self.calEnd):
            cal.Bind(wx.adv.EVT_DATE_CHANGED, self._on_change)

        self.btnMonth = wx.Button(self, wx.ID_ANY, "Month")
        self.btnYear = wx.Button(self, wx.ID_ANY, "Year")
        self.btnAll = wx.Button(self, wx.ID_ANY, "All")
        self.btnMonth.Bind(wx.EVT_BUTTON, self._on_month)
        self.btnYear.Bind(wx.EVT_BUTTON, self._on_year)
        self.btnAll.Bind(wx.EVT_BUTTON, self._on_all)

        # --- Movement ------------------------------------------------- #
        self.rbFlow = wx.RadioBox(self, wx.ID_ANY, "Type",
                                  choices=['All', 'In', 'Out'],
                                  majorDimension=1, style=wx.RA_SPECIFY_COLS)
        self.rbSettled = wx.RadioBox(self, wx.ID_ANY, "State",
                                     choices=['All', 'Settled', 'Pending'],
                                     majorDimension=1, style=wx.RA_SPECIFY_COLS)
        for rb in (self.rbFlow, self.rbSettled):
            rb.Bind(wx.EVT_RADIOBOX, self._on_change)

        # --- Dimensions ----------------------------------------------- #
        self.cbCategory = wx.ComboBox(self, wx.ID_ANY, size=(fw * 18, -1),
                                      style=wx.CB_READONLY | wx.CB_DROPDOWN)
        self.cbSupplier = wx.ComboBox(self, wx.ID_ANY, size=(fw * 18, -1),
                                      style=wx.CB_READONLY | wx.CB_DROPDOWN)
        for cb in (self.cbCategory, self.cbSupplier):
            cb.Bind(wx.EVT_COMBOBOX, self._on_change)

        self._do_layout()

    # ------------------------------------------------------------------ #
    # layout
    # ------------------------------------------------------------------ #
    def _do_layout(self) -> None:
        period = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Period"),
                                   wx.VERTICAL)
        grid = wx.FlexGridSizer(2, 2, 4, 6)
        grid.Add(wx.StaticText(self, wx.ID_ANY, "From"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.calStart, 0, wx.EXPAND)
        grid.Add(wx.StaticText(self, wx.ID_ANY, "To"), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.calEnd, 0, wx.EXPAND)
        presets = wx.BoxSizer(wx.HORIZONTAL)
        for b in (self.btnMonth, self.btnYear, self.btnAll):
            presets.Add(b, 0, wx.RIGHT, 4)
        period.Add(grid, 0, wx.ALL, 4)
        period.Add(presets, 0, wx.ALL, 4)

        movement = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Movement"),
                                     wx.HORIZONTAL)
        movement.Add(self.rbFlow, 0, wx.ALL, 4)
        movement.Add(self.rbSettled, 0, wx.ALL, 4)

        dims = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Dimensions"),
                                 wx.VERTICAL)
        dgrid = wx.FlexGridSizer(2, 2, 4, 6)
        dgrid.Add(wx.StaticText(self, wx.ID_ANY, "Category"), 0, wx.ALIGN_CENTER_VERTICAL)
        dgrid.Add(self.cbCategory, 0, wx.EXPAND)
        dgrid.Add(wx.StaticText(self, wx.ID_ANY, "Supplier"), 0, wx.ALIGN_CENTER_VERTICAL)
        dgrid.Add(self.cbSupplier, 0, wx.EXPAND)
        dims.Add(dgrid, 0, wx.ALL, 4)

        root = wx.BoxSizer(wx.HORIZONTAL)
        for box in (period, movement, dims):
            root.Add(box, 0, wx.ALL | wx.EXPAND, 4)
        self.SetSizer(root)

    # ------------------------------------------------------------------ #
    # public contract (used by MainFrame)
    # ------------------------------------------------------------------ #
    def populate_combos(self) -> None:
        """Fill the category / supplier combos with an '(any)' entry first."""
        self._fill(self.cbCategory, '(all categories)',
                   self.presenter.categories())
        self._fill(self.cbSupplier, '(all suppliers)',
                   self.presenter.suppliers())

    def set_period(self, start: datetime.datetime, end: datetime.datetime) -> None:
        """Sync the Da/A pickers without firing on_change."""
        engine = wx.GetApp().engine
        self.calStart.SetValue(engine.set_calendar_date(start))
        self.calEnd.SetValue(engine.set_calendar_date(end))

    def set_show_disabled(self, show: bool) -> None:
        """Reflect the 'show disabled' menu toggle and reload."""
        self._show_disabled = show
        self._emit()

    def get_filter(self) -> FlowFilter:
        """Build a FlowFilter from the current widget state."""
        engine = wx.GetApp().engine
        start = engine.get_calendar_date(self.calStart.GetValue())
        # the 'To' picker is a day; make it inclusive of the whole day
        end = engine.get_calendar_date(self.calEnd.GetValue()).replace(
            hour=23, minute=59, second=59)
        return FlowFilter(
            flow=self._TRI[self.rbFlow.GetSelection()],
            settled=self._TRI[self.rbSettled.GetSelection()],
            enabled=None if self._show_disabled else True,
            category_id=self._combo_id(self.cbCategory),
            supplier_id=self._combo_id(self.cbSupplier),
            start_date=start,
            end_date=end)

    # ------------------------------------------------------------------ #
    # preset handlers
    # ------------------------------------------------------------------ #
    def _on_month(self, evt) -> None:
        today = datetime.date.today()
        start = datetime.datetime(today.year, today.month, 1)
        end = self._end_of_month(today.year, today.month)
        self.set_period(start, end)
        self._emit()

    def _on_year(self, evt) -> None:
        year = datetime.date.today().year
        self.set_period(datetime.datetime(year, 1, 1),
                        datetime.datetime(year, 12, 31))
        self._emit()

    def _on_all(self, evt) -> None:
        self.set_period(datetime.datetime(1900, 1, 1),
                        datetime.datetime(2100, 1, 1))
        self._emit()

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _on_change(self, evt) -> None:
        self._emit()

    def _emit(self) -> None:
        if self.on_change is not None:
            self.on_change()

    @staticmethod
    def _fill(combo: wx.ComboBox, any_label: str, rows) -> None:
        combo.Clear()
        combo.Append(any_label, '%')
        for r in rows:
            combo.Append(str(r['name']).strip(), int(r['pk']))
        combo.SetSelection(0)

    @staticmethod
    def _combo_id(combo: wx.ComboBox) -> Any:
        sel = combo.GetSelection()
        if sel == wx.NOT_FOUND:
            return '%'
        return combo.GetClientData(sel)

    @staticmethod
    def _end_of_month(year: int, month: int) -> datetime.datetime:
        if month == 12:
            nxt = datetime.datetime(year + 1, 1, 1)
        else:
            nxt = datetime.datetime(year, month + 1, 1)
        return nxt - datetime.timedelta(days=1)
