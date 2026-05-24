#!/usr/bin/env python3
"""
Unit tests for MainPresenter.

The whole point of the MVP refactor: this runs with NO wxPython and NO
database. The presenter is driven by a fake controller and a fake view.
"""

import datetime

from models import FlowFilter
from presenters import MainPresenter, MainView


SAMPLE = [
    {'event_id': 1, 'flow': 1, 'supplier': 'ACME ', 'category': 'Salary',
     'settled': 1, 'reference': 'IN1', 'bill': 100.0, 'issued': '01-01-2020'},
    {'event_id': 2, 'flow': 0, 'supplier': 'Shop', 'category': 'Food',
     'settled': 1, 'reference': 'OUT1', 'bill': 30.0, 'issued': '02-01-2020'},
    {'event_id': 3, 'flow': 0, 'supplier': 'Shop', 'category': 'Food',
     'settled': 0, 'reference': 'OUT2', 'bill': 12.5, 'issued': '03-01-2020'},
]


class FakeController:
    def __init__(self, rows):
        self._rows = list(rows)
        self.deleted = []

    def oldest_issued(self):
        return "2012-01-31"

    def get_flows(self, f):
        return list(self._rows)

    def delete_event(self, event_id):
        self.deleted.append(event_id)
        self._rows = [r for r in self._rows if r['event_id'] != event_id]


class FakeView:
    def __init__(self):
        self.last = None
        self.calls = 0

    def show_events(self, count, totals):
        self.last = (count, dict(totals))
        self.calls += 1


def make(rows=SAMPLE):
    c = FakeController(rows)
    p = MainPresenter(c)
    v = FakeView()
    p.set_view(v)
    return p, c, v


def test_fakeview_satisfies_view_contract():
    # the presenter depends on the MainView protocol, not on a concrete class
    assert isinstance(FakeView(), MainView)


def test_open_sets_start_date_and_loads():
    p, c, v = make()
    p.open()
    assert p.filter.start_date == datetime.datetime(2012, 1, 31)
    assert p.row_count() == 3
    assert v.calls == 1


def test_totals():
    p, c, v = make()
    p.refresh()
    assert p.totals == {'in': 100.0, 'out': 42.5, 'wallet': 57.5}
    assert v.last == (3, {'in': 100.0, 'out': 42.5, 'wallet': 57.5})


def test_cell_formatting_and_strip():
    p, c, v = make()
    p.refresh()
    assert p.cell(0, 0) == '1'            # flow
    assert p.cell(0, 1) == 'ACME'         # supplier, stripped
    assert p.cell(1, 4) == 'OUT1'         # reference
    assert p.cell(2, 5) == '12.5'         # bill


def test_event_id_at():
    p, c, v = make()
    p.refresh()
    assert p.event_id_at(0) == 1
    assert p.event_id_at(2) == 3


def test_sort_by_bill_descending():
    p, c, v = make()
    p.refresh()
    p.sort(5, ascending=False)            # column 5 = Currency/bill
    assert [r['bill'] for r in p.rows] == [100.0, 30.0, 12.5]
    assert p.cell(0, 5) == '100.0'


def test_delete_event_refreshes():
    p, c, v = make()
    p.refresh()
    p.delete_event(0)                     # deletes event_id 1
    assert c.deleted == [1]
    assert p.row_count() == 2
    assert p.totals == {'in': 0, 'out': 42.5, 'wallet': -42.5}
