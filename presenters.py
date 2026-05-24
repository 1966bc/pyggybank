#!/usr/bin/env python3
"""
Presenters for PyggyBank (Model-View-Presenter).

A Presenter holds the screen's state and orchestration logic in plain Python:
it asks the Controller for data, computes derived values (wallet totals),
keeps the row list and the display strings, and tells its (passive) view what
to render. It has no wxPython import, so it is unit-testable on its own.

The view is injected later via set_view(); the Presenter is injected with its
Controller (dependency injection).
"""

import datetime
from typing import Any, Dict, List, Optional, Tuple

from models import FlowFilter


class MainPresenter:
    """Presenter for the main events window."""

    # columns shown in the events grid, with the flows-row key each maps to
    COLUMNS: Tuple[Tuple[str, str], ...] = (
        ('Flow', 'flow'),
        ('Suppliers', 'supplier'),
        ('Category', 'category'),
        ('Settled', 'settled'),
        ('Reference', 'reference'),
        ('Currency', 'bill'),
        ('Issued', 'issued'),
    )

    def __init__(self, controller) -> None:
        self.controller = controller
        self.view = None
        self.filter = FlowFilter()
        self.rows: List[Dict[str, Any]] = []
        self._display: List[Tuple[str, ...]] = []
        self.totals: Dict[str, float] = {'in': 0, 'out': 0, 'wallet': 0}

    def set_view(self, view) -> None:
        self.view = view

    # ------------------------------------------------------------------ #
    # lifecycle / filtering
    # ------------------------------------------------------------------ #
    def open(self) -> None:
        """Initial load: start from the oldest issued date, then refresh."""
        oldest = self.controller.oldest_issued()
        if oldest is not None:
            self.filter.start_date = self._to_datetime(oldest)
        self.refresh()

    def set_filter(self, **changes: Any) -> None:
        """Update one or more filter fields and reload."""
        for key, value in changes.items():
            setattr(self.filter, key, value)
        self.refresh()

    def refresh(self) -> None:
        """Re-query, recompute totals and ask the view to render."""
        self.rows = self.controller.get_flows(self.filter)
        self._display = [self._format(row) for row in self.rows]
        self._compute_totals()
        if self.view is not None:
            self.view.show_events(len(self._display), self.totals)

    # ------------------------------------------------------------------ #
    # virtual-list accessors (the view asks for cell text on demand)
    # ------------------------------------------------------------------ #
    def row_count(self) -> int:
        return len(self._display)

    def cell(self, row: int, col: int) -> str:
        return self._display[row][col]

    def event_id_at(self, row: int) -> int:
        return self.rows[row]['event_id']

    # ------------------------------------------------------------------ #
    # actions
    # ------------------------------------------------------------------ #
    def delete_event(self, row: int) -> None:
        self.controller.delete_event(self.rows[row]['event_id'])
        self.refresh()

    def sort(self, col: int, ascending: bool = True) -> None:
        """Sort the in-memory rows by the column's key, then re-render."""
        key = self.COLUMNS[col][1]
        self.rows.sort(key=lambda r: r[key], reverse=not ascending)
        self._display = [self._format(row) for row in self.rows]
        if self.view is not None:
            self.view.show_events(len(self._display), self.totals)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _format(self, row: Dict[str, Any]) -> Tuple[str, ...]:
        return tuple(str(row[key]).strip() for _, key in self.COLUMNS)

    def _compute_totals(self) -> None:
        win = sum(r['bill'] for r in self.rows if r['flow'])
        wout = sum(r['bill'] for r in self.rows if not r['flow'])
        self.totals = {'in': win, 'out': wout, 'wallet': win - wout}

    @staticmethod
    def _to_datetime(value: Any) -> datetime.datetime:
        if isinstance(value, str):
            return datetime.datetime.strptime(value[:10], "%Y-%m-%d")
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)
        return datetime.datetime(1900, 1, 1)
