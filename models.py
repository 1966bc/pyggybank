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

    The three tri-state flags use None to mean "any" (so the view's 3-state
    checkboxes map cleanly: unchecked-mixed -> None, checked -> True,
    unchecked -> False). supplier_id / category_id use '%' to mean "any",
    matching the LIKE-based query.
    """

    flow: Optional[bool] = None
    settled: Optional[bool] = None
    enabled: Optional[bool] = None
    supplier_id: Any = '%'
    category_id: Any = '%'
    start_date: datetime.datetime = field(
        default_factory=lambda: datetime.datetime(1900, 1, 1))
