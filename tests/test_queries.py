#!/usr/bin/env python3
"""queries.json is valid and complete (pure test, no wx/db)."""

import os
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

REQUIRED = ("flows", "report", "suppliers", "categories",
            "cbo_suppliers", "cbo_categories", "category", "supplier",
            "delete_transaction")


def test_queries_json_is_valid_and_complete():
    with open(os.path.join(ROOT, "queries.json"), encoding="utf-8") as f:
        queries = json.load(f)
    for key in REQUIRED:
        assert key in queries, "missing query: %s" % key
        assert isinstance(queries[key], str) and queries[key].strip()
