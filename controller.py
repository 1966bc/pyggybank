#!/usr/bin/env python3
"""
Controller (domain) layer for PyggyBank.

This is the seam between the GUI and the database. Views and presenters call
the parlante methods here (get_flows, save_event, delete_event, ...) and never
see SQL, column order or the DBMS connection. The Controller turns domain
requests into parameterized queries and delegates execution to a data source
(any object exposing the DBMS API: read / write / build_sql / get_selected /
dict_queries).

It is injected with its data source (dependency injection), so it can be
unit-tested against an in-memory SQLite database without the wxPython app.
"""

from typing import Any, Dict, List, Optional

from models import FlowFilter


class Controller:
    """Domain operations on top of a DBMS-like data source."""

    def __init__(self, db) -> None:
        self.db = db

    # ------------------------------------------------------------------ #
    # flows / events
    # ------------------------------------------------------------------ #
    @staticmethod
    def _flag(value: Optional[bool]) -> Any:
        """Map a tri-state flag (None/True/False) to a SQL LIKE argument."""
        if value is None:
            return '%'
        return 1 if value else 0

    def _flow_args(self, f: FlowFilter) -> tuple:
        return (self._flag(f.flow),
                self._flag(f.settled),
                self._flag(f.enabled),
                f.supplier_id,
                f.category_id,
                f.start_date)

    def get_flows(self, f: FlowFilter) -> List[Dict[str, Any]]:
        """Return the events list (for the main grid) matching the filter."""
        return self.db.read(True, self.db.dict_queries['flows'], self._flow_args(f)) or []

    def get_report_rows(self, f: FlowFilter) -> List[Dict[str, Any]]:
        """Return the rows for the PDF report matching the filter."""
        return self.db.read(True, self.db.dict_queries['report'], self._flow_args(f)) or []

    def oldest_issued(self) -> Optional[Any]:
        """Return the oldest 'issued' date in the events table, or None."""
        row = self.db.read(
            False, "SELECT issued AS issued FROM events ORDER BY issued ASC LIMIT 1")
        return row['issued'] if row else None

    def get_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        return self.db.get_selected('events', 'event_id', event_id)

    def save_event(self, record: tuple, event_id: Optional[int] = None) -> Optional[int]:
        """Insert a new event, or update the one identified by event_id."""
        if event_id is None:
            sql = self.db.build_sql('events', 'insert')
            return self.db.write(sql, record)
        sql = self.db.build_sql('events', 'update')
        return self.db.write(sql, record + (event_id,))

    def delete_event(self, event_id: int) -> Optional[int]:
        return self.db.write(self.db.dict_queries['delete_transaction'], (event_id,))

    # ------------------------------------------------------------------ #
    # lookup tables (categories / suppliers)
    # ------------------------------------------------------------------ #
    def list_enabled_categories(self) -> List[Dict[str, Any]]:
        return self.db.read(True, self.db.dict_queries['cbo_categories']) or []

    def list_enabled_suppliers(self) -> List[Dict[str, Any]]:
        return self.db.read(True, self.db.dict_queries['cbo_suppliers']) or []
