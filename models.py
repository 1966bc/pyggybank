#!/usr/bin/env python3
"""
Domain value objects for PyggyBank.

These are plain, GUI-agnostic data holders shared by the Controller and the
Presenters. They carry no wxPython and no SQL.
"""

import datetime
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class FlowFilter:
    """
    User-chosen filters for the events/flows list.

    flow / settled use None to mean "any", True/False to pick a side (the view
    exposes them as explicit radio choices). enabled defaults to True so the
    everyday list hides soft-deleted rows; a menu toggle sets it to None to
    show everything. supplier_id / category_id use '%' to mean "any", matching
    the LIKE-based query. start_date / end_date bound the issued range
    (BETWEEN); the wide defaults mean "no time limit".
    """

    flow: Optional[bool] = None
    settled: Optional[bool] = None
    enabled: Optional[bool] = True
    supplier_id: Any = '%'
    category_id: Any = '%'
    start_date: datetime.datetime = field(
        default_factory=lambda: datetime.datetime(1900, 1, 1))
    end_date: datetime.datetime = field(
        default_factory=lambda: datetime.datetime(2100, 1, 1))
