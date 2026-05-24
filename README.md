# PyggyBank 3.0

A small desktop "piggy bank" / personal cash-flow manager: record money **in**
and **out**, tag each entry with a supplier and a category, filter the ledger,
and print it to PDF or export it to Excel.

Built with **Python 3 + wxPython 4 (Phoenix)**, **SQLite**, **ReportLab** and
**openpyxl**.

> Version 3.0 is a full port of the original 2017 codebase (Python 2 + wxPython
> 2.8 Classic) **and** an architectural refactor to a clean MVP design. See the
> changelog at the bottom.

## Architecture (Model–View–Presenter)

The GUI never touches SQL or the database: everything goes through a domain
layer. Data access is fully decoupled from presentation.

```
 View (wxPython, passive)        Presenter (pure Python)      Domain / data
 ─────────────────────────       ───────────────────────      ─────────────────────
 MainFrame  ── intent ──►  MainPresenter ──►  Controller ──►  DBMS ──►  SQLite
   (implements MainView)     (filters, totals,   (get_flows,    (connection,
   virtual ListCtrl          sorting; no wx)     save_event,    read/write,
 dialogs / lookup editor                         lookups…)      build_sql)
 XlsExporter, GeneratePDF  ◄──── data by name (dicts) ─────►     SQL from queries.json
```

| Module | Responsibility |
|--------|----------------|
| `pyggy.py` | launcher + dependency injection (`Engine → Controller → MainPresenter → MainFrame`) |
| `dbms.py` | `DBMS`: SQLite connection, `read`/`write`, `build_sql`, SQL-identifier validation, **dict rows** |
| `engine.py` | `Engine(DBMS)` singleton; loads `queries.json`; UI services (icon, font, calendar, dialogs) + `log.txt` logging |
| `controller.py` | domain layer: `get_flows`, `save_event`, lookup CRUD, name resolution |
| `models.py` | `FlowFilter` value object |
| `presenters.py` | `MainPresenter` (pure, testable) + `MainView` protocol |
| `exporters.py` | `XlsExporter` (openpyxl, pure) |
| `reports/rpt_flows.py` | `GeneratePDF` + `ReportHeader` (ReportLab, no app reference) |
| `frames/main.py` | `MainFrame` — passive view, virtual `ListCtrl` |
| `frames/update_data.py` | add / edit an event |
| `frames/lookup_manager.py` | list & manage categories / suppliers |
| `frames/lookup_editor.py` | add / edit one category or supplier |
| `queries.json` | the SQL statements (data, not code) |
| `pyggy.db` | sample SQLite database |

## Requirements

* Python 3.8+
* wxPython >= 4.2 (Phoenix)
* reportlab >= 4.0
* openpyxl >= 3.0
* SQLite (bundled with Python)

## Run

```sh
# if wxPython is installed system-wide, let the venv see it:
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python pyggy.py
```

(If wxPython is *not* installed system-wide, add `wxPython` to the pip install
and drop `--system-site-packages`.)

The window follows your desktop's GTK theme (light or dark) — that is intended.

## Development & tests

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

The presenter, exporter and report tests run with **no wxPython and no
database** (the payoff of the MVP split); the controller/DBMS tests run against
an in-memory or throwaway SQLite copy.

## Changelog

### 3.0
* Ported Python 2 → 3 and wxPython 2.8 (Classic) → 4.2 (Phoenix).
* `xlwt` → `openpyxl`; ReportLab 2 → 4.
* Refactored to MVP: passive `MainFrame` over a `MainPresenter`, with a
  `Controller`/`DBMS` data layer. The GUI no longer issues SQL.
* Virtual `ListCtrl`; dict-based rows; SQL moved to `queries.json`.
* Export (XLS) and the PDF report extracted into standalone, app-independent
  services.
* Type hints, docstrings, `on_log` → `log.txt`, and a pytest suite.

### 2.3 (historical, Python 2 / wxPython 2.8)
Architecture centred on `wx.GetApp()`; ran on Debian Squeeze. Original launch:
`python pyggy.py` with Python ≤ 2.6, wxPython 2.8.10.1, ReportLab 2.4.

## Author & license

Giuseppe Costanzi (1966bc) — <giuseppe.costanzi@gmail.com>
GNU GPL v3 / wxWindows License. See `LICENSE` and `copying`.
