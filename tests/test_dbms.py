#!/usr/bin/env python3
"""
Unit tests for the DBMS layer, on an in-memory SQLite database.

Covers SQL building (default + explicit columns), identifier validation
(SQL-injection guard), dict rows, and the read/write round-trip.
"""

import pytest

from dbms import DBMS


@pytest.fixture
def db():
    d = DBMS(":memory:")
    d.con.execute(
        "CREATE TABLE widget ("
        " widget_id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " name TEXT, qty INTEGER, enable INTEGER DEFAULT 1)")
    try:
        yield d
    finally:
        d.close()


def test_get_columns(db):
    assert db._get_columns("widget") == ("widget_id", "name", "qty", "enable")


def test_get_pk_name(db):
    assert db.get_pk_name("widget") == "widget_id"


def test_build_sql_insert_default(db):
    assert db.build_sql("widget", "insert") == \
        "INSERT INTO widget(name,qty,enable) VALUES(?,?,?)"


def test_build_sql_update_default(db):
    assert db.build_sql("widget", "update") == \
        "UPDATE widget SET name = ?, qty = ?, enable = ? WHERE widget_id = ?"


def test_build_sql_explicit_columns(db):
    assert db.build_sql("widget", "insert", ["name", "qty"]) == \
        "INSERT INTO widget(name,qty) VALUES(?,?)"
    assert db.build_sql("widget", "update", ["name"]) == \
        "UPDATE widget SET name = ? WHERE widget_id = ?"


def test_build_sql_bad_op_returns_none(db):
    assert db.build_sql("widget", "delete") is None


def test_validate_identifier_rejects_injection(db):
    with pytest.raises(ValueError):
        db._validate_sql_identifier("widget; DROP TABLE widget", "table")


def test_build_sql_rejects_bad_column(db):
    # invalid column name -> validation fails -> logged -> None (no crash)
    assert db.build_sql("widget", "insert", ["name); --"]) is None


def test_write_returns_lastrowid_and_read_gives_dicts(db):
    new_id = db.write(db.build_sql("widget", "insert"), ("hammer", 3, 1))
    assert new_id == 1

    rows = db.read(True, "SELECT * FROM widget")
    assert isinstance(rows, list) and rows[0]["name"] == "hammer"   # dict row

    one = db.read(False, "SELECT * FROM widget WHERE widget_id = ?", (new_id,))
    assert one["qty"] == 3


def test_get_selected(db):
    db.write(db.build_sql("widget", "insert"), ("nail", 10, 1))
    rec = db.get_selected("widget", "widget_id", 1)
    assert rec["name"] == "nail" and rec["enable"] == 1


def test_update_round_trip(db):
    db.write(db.build_sql("widget", "insert"), ("nail", 10, 1))
    db.write(db.build_sql("widget", "update", ["name", "qty"]), ("screw", 99, 1))
    rec = db.get_selected("widget", "widget_id", 1)
    assert rec["name"] == "screw" and rec["qty"] == 99
