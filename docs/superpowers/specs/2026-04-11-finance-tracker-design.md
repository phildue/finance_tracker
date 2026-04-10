# Finance Tracker — First Vertical Slice Design

**Date:** 2026-04-11
**Scope:** Manual expense entry + list view, end-to-end

---

## Overview

A single-user web application for tracking personal expenses. The first vertical slice delivers manual expense entry and a list view, establishing the full hexagonal architecture that all future slices (CSV upload, mobile) will extend.

**Stack:** Python (FastAPI) backend · React + Vite frontend · SQLite storage

---

## Architecture

Hexagonal architecture (Ports & Adapters), Option A — pragmatic monorepo with clear module boundaries enforced by import conventions. No DI framework; manual wiring at the composition root.

The domain package has zero external dependencies. Adapters depend on the domain; the domain never depends on adapters.

```
finance_tracker/
├── backend/
│   ├── domain/
│   │   ├── expense.py            # Expense entity + validation
│   │   ├── ports.py              # ExpenseRepository ABC
│   │   └── use_cases.py          # AddExpense, ListExpenses
│   ├── adapters/
│   │   ├── sqlite_repository.py  # SQLite impl of ExpenseRepository
│   │   └── api/
│   │       ├── main.py           # Composition root — wires repo + use cases
│   │       └── routes.py         # FastAPI route handlers
│   ├── tests/
│   │   ├── test_use_cases.py     # Pure domain tests, no I/O
│   │   └── test_api.py           # Integration tests against real SQLite
│   └── requirements.txt
├── frontend/
│   └── (Vite + React scaffold)
└── CLAUDE.md
```

---

## Domain Model

### `Expense` entity (`domain/expense.py`)

Immutable dataclass. Validation in `__post_init__` (amount must be positive). No I/O, no external imports.

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | Generated on creation |
| `amount` | `Decimal` | Never `float` — avoids rounding errors |
| `currency` | `str` | ISO 4217, e.g. `"EUR"` |
| `category` | `str` | Free text, e.g. `"groceries"` |
| `description` | `str` | Optional human-readable note |
| `date` | `date` | Date the expense occurred |

### `ExpenseRepository` port (`domain/ports.py`)

```python
class ExpenseRepository(ABC):
    def save(self, expense: Expense) -> None: ...
    def list_all(self) -> list[Expense]: ...
```

### Use cases (`domain/use_cases.py`)

Each use case receives its repository at construction time.

- `AddExpense.execute(amount, currency, category, date, description=None) -> Expense`
- `ListExpenses.execute() -> list[Expense]` — returns expenses sorted by date descending; sorting is the use case's responsibility, not the repository's

---

## Adapters

### SQLite adapter (`adapters/sqlite_repository.py`)

- Uses Python's built-in `sqlite3` — no ORM.
- Single `expenses` table mirroring entity fields.
- `Decimal` stored as `TEXT` to preserve precision.
- Translates between SQL rows and `Expense` dataclasses.

### FastAPI adapter (`adapters/api/`)

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| `POST` | `/expenses` | Runs `AddExpense`, returns created expense as JSON |
| `GET` | `/expenses` | Runs `ListExpenses`, returns array sorted by date descending |

Pydantic request/response models are defined in the `api/` adapter — not in the domain. Route handlers receive pre-wired use case instances; they never instantiate repositories directly.

**Composition root (`main.py`):**

```python
repo = SqliteExpenseRepository("expenses.db")
add_expense = AddExpense(repo)
list_expenses = ListExpenses(repo)
app.include_router(build_router(add_expense, list_expenses))
```

---

## Frontend

React + Vite. No routing library or state management library for this slice.

**Components:**
- `ExpenseForm` — controlled form (amount, currency, category, description, date). POSTs to `/expenses`, triggers list refresh on success.
- `ExpenseList` — fetches `/expenses` on mount, renders table sorted by date descending.
- `App` — owns list state, passes refresh callback to `ExpenseForm`.

**`api.ts`** — thin module wrapping all `fetch` calls. Components never call `fetch` directly. Single change point if the API shape changes.

**Dev proxy:** Vite proxies `/expenses` → `http://localhost:8000`. No CORS config needed during development.

---

## Testing Strategy

- **`test_use_cases.py`** — pure unit tests against the domain. Use an in-memory `FakeExpenseRepository` implementing the port. No SQLite, no HTTP.
- **`test_api.py`** — integration tests using FastAPI's `TestClient` with a real (temp file) SQLite database.

---

## Out of Scope for This Slice

- CSV upload
- Authentication
- Categories as a managed entity (free text only)
- Expense editing or deletion
- Mobile app
