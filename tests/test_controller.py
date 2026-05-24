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


def test_save_get_delete_round_trip(controller):
    before = len(controller.get_flows(FlowFilter()))
    record = (1, 1, 1, 1, "PYTEST", 9.99,
              datetime.datetime(2026, 5, 24), datetime.datetime(2026, 6, 24),
              "desc", datetime.datetime.now(), 1)

    new_id = controller.save_event(record)
    assert isinstance(new_id, int)

    saved = controller.get_event(new_id)
    assert saved["reference"] == "PYTEST"
    assert saved["bill"] == 9.99

    # update
    updated = (0, 1, 1, 0, "PYTEST2", 5.0,
               datetime.datetime(2026, 5, 24), datetime.datetime(2026, 6, 24),
               "desc2", datetime.datetime.now(), 1)
    controller.save_event(updated, event_id=new_id)
    assert controller.get_event(new_id)["reference"] == "PYTEST2"

    controller.delete_event(new_id)
    assert controller.get_event(new_id) is None
    assert len(controller.get_flows(FlowFilter())) == before
