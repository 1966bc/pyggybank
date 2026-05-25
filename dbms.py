#!/usr/bin/env python3
"""
Database Management System (DBMS) layer for PyggyBank.

This module provides the DBMS class, the GUI-agnostic foundation of the data
access layer. It handles the SQLite connection, query execution and SQL
generation. Engine (engine.py) extends it with application/wxPython logic.

Architecture:
    - DBMS:   base database layer (this module)
    - Engine: orchestrator that extends DBMS with domain queries and wx helpers

Key Features:
    - SQLite connection management
    - Dictionary-based result sets (no positional indexing)
    - Parameterized queries only (SQL injection prevention)
    - SQL identifier validation for table/column names
    - Centralized error logging via on_log()

Author: 1966bc (Giuseppe Costanzi)
License: GNU GPL v3
Version: 3.0
"""

import re
import sys
import inspect
import sqlite3
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


class DBMS:
    """
    Database Management System base layer for SQLite operations.

    Provides connection management, query execution and SQL builders with
    error handling. Rows are returned as dictionaries keyed by column name,
    so callers use ``row["column"]`` and never positional indexing.

    Attributes:
        database (str): path to the SQLite database file
        autocommit (bool): autocommit mode (default: True)
        con: SQLite connection object (managed internally)

    Example:
        >>> db = DBMS("pyggy.db")
        >>> rows = db.read(True, "SELECT * FROM suppliers WHERE enable = ?", (1,))
        >>> rows[0]["supplier"]
        'ACI'
    """

    def __init__(self, database: str, autocommit: bool = True) -> None:
        self.database = database
        self.autocommit = autocommit
        self.con = self._set_connection()

    def __str__(self) -> str:
        return "class: {0}\nMRO: {1}".format(
            self.__class__.__name__,
            [x.__name__ for x in self.__class__.__mro__])

    # ------------------------------------------------------------------ #
    # connection
    # ------------------------------------------------------------------ #
    def _dict_factory(self, cursor: sqlite3.Cursor, row: tuple) -> Dict[str, Any]:
        """Convert a SQLite row into a dictionary keyed by column name."""
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    def _set_connection(self) -> Optional[sqlite3.Connection]:
        try:
            con = sqlite3.connect(
                self.database,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            con.row_factory = self._dict_factory
            con.execute("PRAGMA foreign_keys = ON")
            if self.autocommit:
                con.isolation_level = None  # autocommit mode
            return con
        except Exception as e:
            self._log(e)
            return None

    def _ensure_connection(self) -> None:
        """Open a new connection if there is none."""
        if self.con is None:
            self.con = self._set_connection()

    def close(self) -> None:
        """Close the database connection."""
        if self.con:
            try:
                self.con.close()
                self.con = None
            except Exception as e:
                self._log(e)

    # ------------------------------------------------------------------ #
    # query execution
    # ------------------------------------------------------------------ #
    def read(self, fetch: bool, sql: str,
             args: Tuple = ()) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """
        Execute a SELECT query.

        Args:
            fetch: True -> list of dicts (possibly empty); False -> one dict or None
            sql: SQL query string
            args: parameters for the query

        Returns:
            list[dict] | dict | None (None on error)
        """
        cursor = None
        try:
            self._ensure_connection()
            if self.con is None:
                raise RuntimeError("No active DB connection")

            cursor = self.con.cursor()
            cursor.execute(sql, args)
            return cursor.fetchall() if fetch else cursor.fetchone()
        except Exception as e:
            self._log(e)
            return None
        finally:
            if cursor:
                cursor.close()

    def write(self, sql: str, args: Tuple = ()) -> Optional[int]:
        """
        Execute an INSERT/UPDATE/DELETE statement.

        Returns:
            lastrowid when meaningful, otherwise the affected rowcount,
            or None on error. Commits only when autocommit is disabled.
        """
        cursor = None
        try:
            self._ensure_connection()
            if self.con is None:
                raise RuntimeError("No active DB connection")

            cursor = self.con.cursor()
            cursor.execute(sql, args)
            if not self.autocommit:
                self.con.commit()

            last_id = cursor.lastrowid
            return last_id if last_id not in (None, 0) else cursor.rowcount
        except Exception as e:
            try:
                if self.con and not self.autocommit:
                    self.con.rollback()
            except Exception:
                pass
            self._log(e)
            return None
        finally:
            if cursor:
                cursor.close()

    # ------------------------------------------------------------------ #
    # maintenance
    # ------------------------------------------------------------------ #
    def backup(self, dest_path: str) -> bool:
        """
        Write a consistent copy of the database to dest_path.

        Uses the SQLite online-backup API, so it is safe even with the
        connection open. Returns True on success, False on error.
        """
        dest = None
        try:
            self._ensure_connection()
            if self.con is None:
                raise RuntimeError("No active DB connection")
            dest = sqlite3.connect(dest_path)
            with dest:
                self.con.backup(dest)
            return True
        except Exception as e:
            self._log(e)
            return False
        finally:
            if dest is not None:
                dest.close()

    def vacuum(self) -> bool:
        """Compact the database file (reclaim free pages). True on success."""
        try:
            self._ensure_connection()
            if self.con is None:
                raise RuntimeError("No active DB connection")
            self.con.execute("VACUUM")
            return True
        except Exception as e:
            self._log(e)
            return False

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def get_selected(self, table: str, field: str, value: Any) -> Optional[Dict[str, Any]]:
        """
        Return a single record as a dictionary (used when a row is clicked).

        Args:
            table: table name
            field: primary key column name
            value: primary key value

        Returns:
            dict keyed by column name, or None.
        """
        self._validate_sql_identifier(table, "table")
        self._validate_sql_identifier(field, "column")
        sql = "SELECT * FROM {0} WHERE {1} = ?".format(table, field)
        return self.read(False, sql, (value,))

    def get_pk_name(self, table: str) -> Optional[str]:
        """Return the primary key column name (the first column by convention)."""
        columns = self._get_columns(table)
        return columns[0] if columns else None

    def _validate_sql_identifier(self, identifier: str,
                                 identifier_type: str = "identifier") -> None:
        """
        Validate a SQL identifier (table/column name) to prevent SQL injection.

        Raises:
            ValueError: if it does not match ^[a-zA-Z_][a-zA-Z0-9_]*$
        """
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            raise ValueError(
                "Invalid SQL {0} name: '{1}'. Must match ^[a-zA-Z_][a-zA-Z0-9_]*$"
                .format(identifier_type, identifier))

    def _get_columns(self, table: str) -> Tuple[str, ...]:
        """Return all column names in declaration order (PK first) via PRAGMA."""
        cursor = None
        try:
            self._validate_sql_identifier(table, "table")
            self._ensure_connection()
            if self.con is None:
                raise RuntimeError("No active DB connection")

            cursor = self.con.cursor()
            cursor.execute("PRAGMA table_info({0})".format(table))
            rows = cursor.fetchall()
            return tuple(row["name"] for row in sorted(rows, key=lambda r: r["cid"]))
        except Exception as e:
            self._log(e)
            return tuple()
        finally:
            if cursor:
                cursor.close()

    def build_sql(self, table: str, op: str,
                  columns: Optional[Sequence[str]] = None) -> Optional[str]:
        """
        Build an INSERT or UPDATE statement.

        Conventions:
            - the PK is the first column (used in the WHERE clause on UPDATE)
            - placeholders use '?' (SQLite style)
            - if `columns` is given, exactly those columns are written (each is
              validated); otherwise all non-PK columns are used. Passing the
              caller's named columns lets it build the statement from a dict,
              decoupled from the physical column order.

        Example:
            >>> db.build_sql("events", "insert")
            'INSERT INTO events(flow,supplier_id,...) VALUES(?,?,...)'
            >>> db.build_sql("events", "update", ["reference", "bill"])
            'UPDATE events SET reference = ?, bill = ? WHERE event_id = ?'
        """
        try:
            self._validate_sql_identifier(table, "table")
            all_cols = list(self._get_columns(table))
            if not all_cols:
                raise ValueError("No columns found for table '{0}'".format(table))

            pk = all_cols[0]
            if columns is None:
                columns = [c for c in all_cols if c != pk]
            else:
                for c in columns:
                    self._validate_sql_identifier(c, "column")

            if op == "insert":
                cols = ",".join(columns)
                placeholders = ",".join("?" * len(columns))
                return "INSERT INTO {0}({1}) VALUES({2})".format(table, cols, placeholders)
            elif op == "update":
                set_clause = ", ".join("{0} = ?".format(c) for c in columns)
                return "UPDATE {0} SET {1} WHERE {2} = ?".format(table, set_clause, pk)
            else:
                raise ValueError("op must be 'insert' or 'update'")
        except Exception as e:
            self._log(e)
            return None

    # ------------------------------------------------------------------ #
    # logging
    # ------------------------------------------------------------------ #
    def _log(self, exception: Exception) -> None:
        """Collect frame info and delegate to on_log()."""
        f = inspect.currentframe()
        function = f.f_back.f_code.co_name if f and f.f_back else "<unknown>"
        caller = (f.f_back.f_back.f_code.co_name
                  if f and f.f_back and f.f_back.f_back else "<top>")
        self.on_log(function, exception, type(exception), sys.modules[__name__], caller)

    def on_log(self, function: str, exception: Exception, exc_type: type,
               module: Any, caller: str) -> None:
        """Log database errors. Override in Engine for file logging."""
        print("[ERROR] {0} called by {1}: {2}: {3}".format(
            function, caller, exc_type.__name__, exception))


def main():
    db = DBMS("pyggy.db")
    print(db)
    rs = db.read(True, "SELECT name FROM sqlite_master WHERE type = 'table'")
    if rs:
        for row in rs:
            print(row["name"])
    print(db.build_sql("events", "insert"))
    print(db.build_sql("events", "update"))
    db.close()


if __name__ == "__main__":
    main()
