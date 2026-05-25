#!/usr/bin/env python3
"""
Integration tests for the Controller against a throwaway copy of pyggy.db.

The DBMS layer (build_sql, identifier validation, dict rows) is exercised
through the domain methods the GUI actually calls.
"""

import os
import shutil
import datetime

import pytest

from controller import Controller
from models import FlowFilter

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))


@pytest.fixture
def controller(tmp_path):
    import engine as engine_mod
    shutil.copy(os.path.join(ROOT, "pyggy.db"), tmp_path / "pyggy.db")
    engine_mod._EngineMeta._instance = None          # reset the singleton
    eng = engine_mod.Engine(database=str(tmp_path / "pyggy.db"))
    try:
        yield Controller(eng)
    finally:
        eng.close()
        engine_mod._EngineMeta._instance = None


def test_flag_mapping():
    assert Controller._flag(None) == '%'
    assert Controller._flag(True) == 1
    assert Controller._flag(False) == 0


def test_get_flows_returns_named_rows(controller):
    rows = controller.get_flows(FlowFilter())
    assert rows, "expected sample data"
    assert {"event_id", "flow", "supplier", "bill", "issued"} <= set(rows[0])


def test_filter_in_flow_only(controller):
    only_in = controller.get_flows(FlowFilter(flow=True))
    assert only_in
    assert all(r["flow"] == 1 for r in only_in)


def test_flow_filter_defaults():
    f = FlowFilter()
    # enabled defaults to True now (everyday list hides soft-deleted rows)
    assert f.enabled is True
    # the issued range is wide-open by default
    assert f.start_date == datetime.datetime(1900, 1, 1)
    assert f.end_date == datetime.datetime(2100, 1, 1)


def test_flow_args_carries_the_date_range(controller):
    f = FlowFilter(start_date=datetime.datetime(2020, 1, 1),
                   end_date=datetime.datetime(2020, 12, 31))
    args = controller.flow_args(f)
    # order must match the BETWEEN ? AND ? at the tail of the flows query
    assert len(args) == 7
    assert args[-2:] == (f.start_date, f.end_date)


def test_end_date_upper_bound_excludes_everything(controller):
    # a range that ends before any sample data must return no rows
    f = FlowFilter(end_date=datetime.datetime(1901, 1, 1))
    assert controller.get_flows(f) == []


def test_count_events_matches_unfiltered_rows(controller):
    # show-everything filter (enabled=None) lines up with the raw count
    shown = controller.get_flows(FlowFilter(enabled=None))
    assert controller.count_events() == len(shown)


def test_backup_database_creates_a_usable_copy(controller, tmp_path):
    dest = tmp_path / "backup.db"
    assert controller.backup_database(str(dest)) is True
    assert dest.exists() and dest.stat().st_size > 0
    # the copy must be a real SQLite db with the same number of events
    import sqlite3
    con = sqlite3.connect(str(dest))
    try:
        copied = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    finally:
        con.close()
    assert copied == controller.count_events()


def test_compact_database(controller):
    assert controller.compact_database() is True


def test_clear_transactions_empties_the_table(controller):
    assert controller.count_events() > 0
    controller.clear_transactions()
    assert controller.count_events() == 0
    assert controller.get_flows(FlowFilter(enabled=None)) == []


def test_clear_transactions_resets_the_id_counter(controller):
    controller.clear_transactions()
    new_id = controller.save_event({"reference": "FIRST", "bill": 1.0})
    # the AUTOINCREMENT counter was reset, so the first new row is id 1
    assert new_id == 1


def test_save_get_delete_round_trip(controller):
    before = len(controller.get_flows(FlowFilter()))
    # named record: order is irrelevant, SQL is built from the keys
    record = {"reference": "PYTEST", "bill": 9.99, "flow": 1, "settled": 1,
              "supplier_id": 1, "category_id": 1,
              "issued": datetime.datetime(2026, 5, 24),
              "expiration": datetime.datetime(2026, 6, 24),
              "description": "desc", "modify": datetime.datetime.now(), "enable": 1}

    new_id = controller.save_event(record)
    assert isinstance(new_id, int)

    saved = controller.get_event(new_id)
    assert saved["reference"] == "PYTEST"
    assert saved["bill"] == 9.99

    controller.save_event({"reference": "PYTEST2", "bill": 5.0}, event_id=new_id)
    assert controller.get_event(new_id)["reference"] == "PYTEST2"
    assert controller.get_event(new_id)["bill"] == 5.0

    controller.delete_event(new_id)
    assert controller.get_event(new_id) is None
    assert len(controller.get_flows(FlowFilter())) == before


def test_name_resolution(controller):
    cat = controller.list_lookup("categories")[0]
    assert controller.category_name(cat["pk"]) == cat["name"]
    sup = controller.list_lookup("suppliers")[0]
    assert controller.supplier_name(sup["pk"]) == sup["name"]


def test_lookup_list_get_save(controller):
    cats = controller.list_lookup("categories")
    assert cats and set(cats[0]) == {"pk", "name", "enabled"}

    new_id = controller.save_lookup("categories", "PyTestCat", True)
    assert isinstance(new_id, int)

    rec = controller.get_lookup("categories", new_id)
    assert rec == {"pk": new_id, "name": "PyTestCat", "enabled": True}

    controller.save_lookup("categories", "PyTestCat2", False, pk=new_id)
    rec = controller.get_lookup("categories", new_id)
    assert rec["name"] == "PyTestCat2"
    assert rec["enabled"] is False
