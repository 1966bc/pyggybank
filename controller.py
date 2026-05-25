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

    def flow_args(self, f: FlowFilter) -> tuple:
        """Translate a FlowFilter into the LIKE arguments of the flows queries."""
        return (self._flag(f.flow),
                self._flag(f.settled),
                self._flag(f.enabled),
                f.supplier_id,
                f.category_id,
                f.start_date,
                f.end_date)

    def get_flows(self, f: FlowFilter) -> List[Dict[str, Any]]:
        """Return the events list (for the main grid) matching the filter."""
        return self.db.read(True, self.db.dict_queries['flows'], self.flow_args(f)) or []

    def get_report_rows(self, f: FlowFilter) -> List[Dict[str, Any]]:
        """Return the rows for the PDF report matching the filter."""
        return self.db.read(True, self.db.dict_queries['report'], self.flow_args(f)) or []

    def category_name(self, category_id: int) -> Optional[str]:
        row = self.db.read(False, self.db.dict_queries['category'], (category_id,))
        return row['category'] if row else None

    def supplier_name(self, supplier_id: int) -> Optional[str]:
        row = self.db.read(False, self.db.dict_queries['supplier'], (supplier_id,))
        return row['supplier'] if row else None

    def oldest_issued(self) -> Optional[Any]:
        """Return the oldest 'issued' date in the events table, or None."""
        row = self.db.read(
            False, "SELECT issued AS issued FROM events ORDER BY issued ASC LIMIT 1")
        return row['issued'] if row else None

    def get_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        return self.db.get_selected('events', 'event_id', event_id)

    def save_event(self, record: Dict[str, Any],
                   event_id: Optional[int] = None) -> Optional[int]:
        """
        Insert a new event, or update the one identified by event_id.

        `record` is a {column: value} dict, so callers never depend on the
        physical column order: the SQL is built from the dict's own keys.
        """
        columns = list(record.keys())
        values = tuple(record[c] for c in columns)
        if event_id is None:
            sql = self.db.build_sql('events', 'insert', columns)
            return self.db.write(sql, values)
        sql = self.db.build_sql('events', 'update', columns)
        return self.db.write(sql, values + (event_id,))

    def delete_event(self, event_id: int) -> Optional[int]:
        return self.db.write(self.db.dict_queries['delete_transaction'], (event_id,))

    # ------------------------------------------------------------------ #
    # database maintenance
    # ------------------------------------------------------------------ #
    def count_events(self) -> int:
        """How many transactions are stored (0 when empty or on error)."""
        row = self.db.read(False, self.db.dict_queries['count_events'])
        return row['total'] if row else 0

    def backup_database(self, dest_path: str) -> bool:
        """Save a consistent copy of the database to dest_path."""
        return self.db.backup(dest_path)

    def compact_database(self) -> bool:
        """Reclaim free space in the database file (VACUUM)."""
        return self.db.vacuum()

    def clear_transactions(self) -> Optional[int]:
        """
        Delete every transaction and reset the AUTOINCREMENT counter, so the
        next event_id restarts from 1. Returns the affected rowcount.
        """
        affected = self.db.write(self.db.dict_queries['clear_transactions'])
        self.db.write(self.db.dict_queries['reset_sequence'], ('events',))
        return affected

    # ------------------------------------------------------------------ #
    # lookup tables (categories / suppliers)
    #
    # These are the small master tables behind the combos and the lookup
    # manager. The controller normalises their differing column names
    # (category/category_id vs supplier/supplier_id) into a stable shape:
    #     {'pk': int, 'name': str, 'enabled': bool}
    # so the generic GUI never has to know the physical column names.
    # ------------------------------------------------------------------ #
    LOOKUPS = {
        'categories': {'pk': 'category_id', 'name': 'category'},
        'suppliers': {'pk': 'supplier_id', 'name': 'supplier'},
    }

    def _normalise_lookup(self, table: str, row: Dict[str, Any]) -> Dict[str, Any]:
        cols = self.LOOKUPS[table]
        return {'pk': row[cols['pk']], 'name': row[cols['name']],
                'enabled': bool(row['enable'])}

    def list_lookup(self, table: str) -> List[Dict[str, Any]]:
        """All rows of a lookup table as {'pk', 'name', 'enabled'} dicts."""
        rows = self.db.read(True, self.db.dict_queries[table]) or []
        return [self._normalise_lookup(table, r) for r in rows]

    def list_enabled(self, table: str) -> List[Dict[str, Any]]:
        """Enabled rows only (used to populate the event dialog combos)."""
        return [r for r in self.list_lookup(table) if r['enabled']]

    def get_lookup(self, table: str, pk: int) -> Optional[Dict[str, Any]]:
        row = self.db.get_selected(table, self.LOOKUPS[table]['pk'], pk)
        return self._normalise_lookup(table, row) if row else None

    def save_lookup(self, table: str, name: str, enabled: bool,
                    pk: Optional[int] = None) -> Optional[int]:
        """Insert or update a lookup row by name + enabled flag."""
        cols = self.LOOKUPS[table]
        record = {cols['name']: name, 'enable': 1 if enabled else 0}
        columns = list(record.keys())
        values = tuple(record.values())
        if pk is None:
            return self.db.write(self.db.build_sql(table, 'insert', columns), values)
        return self.db.write(self.db.build_sql(table, 'update', columns), values + (pk,))
