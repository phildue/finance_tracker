# Finance Tracker — First Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build manual expense entry and list view end-to-end, from an empty repo, using hexagonal architecture.

**Architecture:** Hexagonal (Ports & Adapters) — the `domain/` package has zero external dependencies; adapters (FastAPI HTTP, SQLite) import from domain and are wired manually in the composition root. The React frontend communicates exclusively through a thin `api.ts` module.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLite (stdlib `sqlite3`), pytest, httpx (TestClient), React 18, TypeScript, Vite

---

## File Map

```
backend/
  domain/
    __init__.py
    expense.py            # Expense dataclass (immutable, validates itself)
    ports.py              # ExpenseRepository ABC
    use_cases.py          # AddExpense, ListExpenses
  adapters/
    __init__.py
    sqlite_repository.py  # SqliteExpenseRepository
    api/
      __init__.py
      routes.py           # Pydantic models + FastAPI route handlers
      main.py             # Composition root — only file that names concrete types
  tests/
    __init__.py
    test_use_cases.py     # Pure domain tests; FakeExpenseRepository, no I/O
    test_api.py           # Integration tests; FastAPI TestClient + temp SQLite
  pytest.ini
  requirements.txt

frontend/
  (Vite scaffold, then:)
  src/
    api.ts                # All fetch() calls live here; components never call fetch
    components/
      ExpenseList.tsx
      ExpenseForm.tsx
    App.tsx               # Owns expenses state; fetches on mount and after add
    main.tsx              # Unchanged from scaffold
  vite.config.ts          # Dev proxy: /expenses → http://localhost:8000
```

---

## Task 1: Backend scaffolding

**Files:**
- Create: `backend/domain/__init__.py`
- Create: `backend/adapters/__init__.py`
- Create: `backend/adapters/api/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/domain backend/adapters/api backend/tests
touch backend/domain/__init__.py backend/adapters/__init__.py \
      backend/adapters/api/__init__.py backend/tests/__init__.py
```

- [ ] **Step 2: Create `backend/requirements.txt`**

```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
pydantic>=2.0.0
pytest>=8.0.0
httpx>=0.27.0
```

- [ ] **Step 3: Create `backend/pytest.ini`**

```ini
[pytest]
pythonpath = .
testpaths = tests
```

`pythonpath = .` makes `domain` and `adapters` importable as top-level packages when pytest is run from the `backend/` directory.

- [ ] **Step 4: Install dependencies**

```bash
cd backend && pip install -r requirements.txt
```

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "chore: scaffold backend directory structure"
```

---

## Task 2: Expense entity

**Files:**
- Create: `backend/domain/expense.py`
- Create: `backend/tests/test_use_cases.py` (first test only)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_use_cases.py`:

```python
from datetime import date
from decimal import Decimal
import pytest
from domain.expense import Expense


def test_expense_stores_fields():
    expense = Expense(
        amount=Decimal("42.50"),
        currency="EUR",
        category="groceries",
        date=date(2026, 4, 11),
    )
    assert expense.amount == Decimal("42.50")
    assert expense.currency == "EUR"
    assert expense.category == "groceries"
    assert expense.date == date(2026, 4, 11)
    assert expense.description is None
    assert expense.id is not None


def test_expense_raises_for_zero_amount():
    with pytest.raises(ValueError, match="amount must be positive"):
        Expense(amount=Decimal("0"), currency="EUR", category="food", date=date(2026, 4, 11))


def test_expense_raises_for_negative_amount():
    with pytest.raises(ValueError, match="amount must be positive"):
        Expense(amount=Decimal("-5"), currency="EUR", category="food", date=date(2026, 4, 11))


def test_expense_is_immutable():
    expense = Expense(
        amount=Decimal("10"), currency="EUR", category="food", date=date(2026, 4, 11)
    )
    with pytest.raises(Exception):
        expense.amount = Decimal("99")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_use_cases.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'domain.expense'`

- [ ] **Step 3: Implement `backend/domain/expense.py`**

```python
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Expense:
    amount: Decimal
    currency: str
    category: str
    date: date
    description: Optional[str] = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("amount must be positive")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_use_cases.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/domain/expense.py backend/tests/test_use_cases.py
git commit -m "feat: add Expense entity with validation"
```

---

## Task 3: Repository port and use cases

**Files:**
- Create: `backend/domain/ports.py`
- Create: `backend/domain/use_cases.py`
- Modify: `backend/tests/test_use_cases.py` (append new tests)

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_use_cases.py`:

```python
from domain.ports import ExpenseRepository
from domain.use_cases import AddExpense, ListExpenses


class FakeExpenseRepository(ExpenseRepository):
    def __init__(self) -> None:
        self._expenses: list[Expense] = []

    def save(self, expense: Expense) -> None:
        self._expenses.append(expense)

    def list_all(self) -> list[Expense]:
        return list(self._expenses)


def test_add_expense_returns_saved_expense():
    repo = FakeExpenseRepository()
    use_case = AddExpense(repo)

    result = use_case.execute(
        amount=Decimal("15.00"),
        currency="EUR",
        category="transport",
        date=date(2026, 4, 11),
    )

    assert result.amount == Decimal("15.00")
    assert result.currency == "EUR"
    assert len(repo.list_all()) == 1


def test_add_expense_with_optional_description():
    repo = FakeExpenseRepository()
    result = AddExpense(repo).execute(
        amount=Decimal("5"),
        currency="USD",
        category="coffee",
        date=date(2026, 4, 11),
        description="flat white",
    )
    assert result.description == "flat white"


def test_list_expenses_returns_sorted_by_date_descending():
    repo = FakeExpenseRepository()
    add = AddExpense(repo)
    add.execute(Decimal("10"), "EUR", "food", date(2026, 4, 1))
    add.execute(Decimal("20"), "EUR", "transport", date(2026, 4, 11))
    add.execute(Decimal("5"), "EUR", "coffee", date(2026, 4, 5))

    result = ListExpenses(repo).execute()

    assert result[0].date == date(2026, 4, 11)
    assert result[1].date == date(2026, 4, 5)
    assert result[2].date == date(2026, 4, 1)


def test_list_expenses_returns_empty_when_no_expenses():
    repo = FakeExpenseRepository()
    assert ListExpenses(repo).execute() == []
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && pytest tests/test_use_cases.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'domain.ports'`

- [ ] **Step 3: Implement `backend/domain/ports.py`**

```python
from abc import ABC, abstractmethod
from .expense import Expense


class ExpenseRepository(ABC):
    @abstractmethod
    def save(self, expense: Expense) -> None: ...

    @abstractmethod
    def list_all(self) -> list[Expense]: ...
```

- [ ] **Step 4: Implement `backend/domain/use_cases.py`**

```python
from datetime import date
from decimal import Decimal
from typing import Optional

from .expense import Expense
from .ports import ExpenseRepository


class AddExpense:
    def __init__(self, repository: ExpenseRepository) -> None:
        self._repository = repository

    def execute(
        self,
        amount: Decimal,
        currency: str,
        category: str,
        date: date,
        description: Optional[str] = None,
    ) -> Expense:
        expense = Expense(
            amount=amount,
            currency=currency,
            category=category,
            date=date,
            description=description,
        )
        self._repository.save(expense)
        return expense


class ListExpenses:
    def __init__(self, repository: ExpenseRepository) -> None:
        self._repository = repository

    def execute(self) -> list[Expense]:
        return sorted(self._repository.list_all(), key=lambda e: e.date, reverse=True)
```

- [ ] **Step 5: Run all tests to verify they pass**

```bash
cd backend && pytest tests/test_use_cases.py -v
```

Expected: `8 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/domain/ports.py backend/domain/use_cases.py backend/tests/test_use_cases.py
git commit -m "feat: add ExpenseRepository port and use cases"
```

---

## Task 4: SQLite adapter

**Files:**
- Create: `backend/adapters/sqlite_repository.py`
- Create: `backend/tests/test_api.py` (SQLite-specific tests first)

The SQLite adapter is tested indirectly through the API integration tests in Task 5. Here we add one focused test to verify the adapter round-trips an `Expense` correctly.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_api.py`:

```python
import pytest
from decimal import Decimal
from datetime import date
from uuid import uuid4
from domain.expense import Expense
from adapters.sqlite_repository import SqliteExpenseRepository


@pytest.fixture
def repo(tmp_path):
    return SqliteExpenseRepository(str(tmp_path / "test.db"))


def test_sqlite_repo_saves_and_retrieves_expense(repo):
    expense = Expense(
        amount=Decimal("99.99"),
        currency="EUR",
        category="groceries",
        date=date(2026, 4, 11),
        description="weekly shop",
    )
    repo.save(expense)

    results = repo.list_all()

    assert len(results) == 1
    retrieved = results[0]
    assert retrieved.id == expense.id
    assert retrieved.amount == Decimal("99.99")
    assert retrieved.currency == "EUR"
    assert retrieved.category == "groceries"
    assert retrieved.date == date(2026, 4, 11)
    assert retrieved.description == "weekly shop"


def test_sqlite_repo_returns_empty_list_when_no_expenses(repo):
    assert repo.list_all() == []
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && pytest tests/test_api.py::test_sqlite_repo_saves_and_retrieves_expense tests/test_api.py::test_sqlite_repo_returns_empty_list_when_no_expenses -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'adapters.sqlite_repository'`

- [ ] **Step 3: Implement `backend/adapters/sqlite_repository.py`**

```python
import sqlite3
from datetime import date
from decimal import Decimal
from uuid import UUID

from domain.expense import Expense
from domain.ports import ExpenseRepository


class SqliteExpenseRepository(ExpenseRepository):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id       TEXT PRIMARY KEY,
                    amount   TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    category TEXT NOT NULL,
                    date     TEXT NOT NULL,
                    description TEXT
                )
                """
            )

    def save(self, expense: Expense) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO expenses (id, amount, currency, category, date, description) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(expense.id),
                    str(expense.amount),
                    expense.currency,
                    expense.category,
                    expense.date.isoformat(),
                    expense.description,
                ),
            )

    def list_all(self) -> list[Expense]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM expenses").fetchall()
        return [
            Expense(
                id=UUID(row["id"]),
                amount=Decimal(row["amount"]),
                currency=row["currency"],
                category=row["category"],
                date=date.fromisoformat(row["date"]),
                description=row["description"],
            )
            for row in rows
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_api.py::test_sqlite_repo_saves_and_retrieves_expense tests/test_api.py::test_sqlite_repo_returns_empty_list_when_no_expenses -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/adapters/sqlite_repository.py backend/tests/test_api.py
git commit -m "feat: add SQLite expense repository adapter"
```

---

## Task 5: FastAPI routes and integration tests

**Files:**
- Create: `backend/adapters/api/routes.py`
- Modify: `backend/tests/test_api.py` (append API integration tests)

- [ ] **Step 1: Write the failing API integration tests**

Add these imports to the **top** of `backend/tests/test_api.py` (after the existing imports):

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from domain.use_cases import AddExpense, ListExpenses
from adapters.api.routes import build_router
```

Then append the following fixtures and tests to the **bottom** of the file:


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "api_test.db")
    repository = SqliteExpenseRepository(db_path)
    app = FastAPI()
    app.include_router(build_router(AddExpense(repository), ListExpenses(repository)))
    return TestClient(app)


def test_post_expense_returns_201(client):
    response = client.post(
        "/expenses",
        json={"amount": "42.50", "currency": "EUR", "category": "groceries", "date": "2026-04-11"},
    )
    assert response.status_code == 201
    data = response.json()
    assert Decimal(data["amount"]) == Decimal("42.50")
    assert data["currency"] == "EUR"
    assert data["category"] == "groceries"
    assert data["date"] == "2026-04-11"
    assert data["description"] is None
    assert "id" in data


def test_post_expense_with_description(client):
    response = client.post(
        "/expenses",
        json={
            "amount": "5",
            "currency": "USD",
            "category": "coffee",
            "date": "2026-04-11",
            "description": "flat white",
        },
    )
    assert response.status_code == 201
    assert response.json()["description"] == "flat white"


def test_get_expenses_returns_empty_list(client):
    response = client.get("/expenses")
    assert response.status_code == 200
    assert response.json() == []


def test_get_expenses_returns_list_sorted_by_date_descending(client):
    client.post("/expenses", json={"amount": "10", "currency": "EUR", "category": "a", "date": "2026-04-01"})
    client.post("/expenses", json={"amount": "20", "currency": "EUR", "category": "b", "date": "2026-04-11"})
    client.post("/expenses", json={"amount": "5",  "currency": "EUR", "category": "c", "date": "2026-04-05"})

    response = client.get("/expenses")
    assert response.status_code == 200
    dates = [e["date"] for e in response.json()]
    assert dates == ["2026-04-11", "2026-04-05", "2026-04-01"]


def test_post_expense_rejects_zero_amount(client):
    response = client.post(
        "/expenses",
        json={"amount": "0", "currency": "EUR", "category": "food", "date": "2026-04-11"},
    )
    assert response.status_code == 422


def test_post_expense_rejects_negative_amount(client):
    response = client.post(
        "/expenses",
        json={"amount": "-1", "currency": "EUR", "category": "food", "date": "2026-04-11"},
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && pytest tests/test_api.py -k "test_post_expense_returns_201 or test_get_expenses_returns_empty_list" -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'adapters.api.routes'`

- [ ] **Step 3: Implement `backend/adapters/api/routes.py`**

```python
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from domain.expense import Expense
from domain.use_cases import AddExpense, ListExpenses


class CreateExpenseRequest(BaseModel):
    amount: Decimal
    currency: str
    category: str
    date: date
    description: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be positive")
        return v


class ExpenseResponse(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    category: str
    date: date
    description: Optional[str]


def _to_response(expense: Expense) -> ExpenseResponse:
    return ExpenseResponse(
        id=expense.id,
        amount=expense.amount,
        currency=expense.currency,
        category=expense.category,
        date=expense.date,
        description=expense.description,
    )


def build_router(add_expense: AddExpense, list_expenses: ListExpenses) -> APIRouter:
    router = APIRouter()

    @router.post("/expenses", response_model=ExpenseResponse, status_code=201)
    def create_expense(body: CreateExpenseRequest) -> ExpenseResponse:
        expense = add_expense.execute(
            amount=body.amount,
            currency=body.currency,
            category=body.category,
            date=body.date,
            description=body.description,
        )
        return _to_response(expense)

    @router.get("/expenses", response_model=list[ExpenseResponse])
    def get_expenses() -> list[ExpenseResponse]:
        return [_to_response(e) for e in list_expenses.execute()]

    return router
```

- [ ] **Step 4: Run all backend tests to verify they pass**

```bash
cd backend && pytest -v
```

Expected: all tests pass (`10 passed` or more)

- [ ] **Step 5: Commit**

```bash
git add backend/adapters/api/routes.py backend/tests/test_api.py
git commit -m "feat: add FastAPI routes with integration tests"
```

---

## Task 6: Composition root

**Files:**
- Create: `backend/adapters/api/main.py`

No automated test for this task — it wires existing tested components. Verified by running the server.

- [ ] **Step 1: Implement `backend/adapters/api/main.py`**

```python
from fastapi import FastAPI

from adapters.sqlite_repository import SqliteExpenseRepository
from adapters.api.routes import build_router
from domain.use_cases import AddExpense, ListExpenses

app = FastAPI(title="Finance Tracker")

_repo = SqliteExpenseRepository("expenses.db")
app.include_router(build_router(AddExpense(_repo), ListExpenses(_repo)))
```

- [ ] **Step 2: Start the server and verify it responds**

```bash
cd backend && uvicorn adapters.api.main:app --reload
```

In a second terminal:

```bash
curl -s -X POST http://localhost:8000/expenses \
  -H "Content-Type: application/json" \
  -d '{"amount": "12.50", "currency": "EUR", "category": "lunch", "date": "2026-04-11"}' | python3 -m json.tool
```

Expected: JSON with `id`, `amount`, `currency`, `category`, `date`, `description: null`

```bash
curl -s http://localhost:8000/expenses | python3 -m json.tool
```

Expected: JSON array containing the expense just created.

- [ ] **Step 3: Stop the server (Ctrl-C) and commit**

```bash
git add backend/adapters/api/main.py
git commit -m "feat: add composition root and wire application"
```

---

## Task 7: Frontend scaffold and proxy config

**Files:**
- Create: `frontend/` (Vite + React scaffold)
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: Scaffold the Vite React TypeScript project**

Run from the repo root:

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
```

- [ ] **Step 2: Update `frontend/vite.config.ts` to add the dev proxy**

Replace the file contents with:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/expenses': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Step 3: Verify the dev server starts**

```bash
cd frontend && npm run dev
```

Expected: Vite dev server starts on `http://localhost:5173` and the default React page loads in the browser.

Stop the server (Ctrl-C).

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "chore: scaffold React/Vite frontend with API proxy"
```

---

## Task 8: API module

**Files:**
- Create: `frontend/src/api.ts`

- [ ] **Step 1: Create `frontend/src/api.ts`**

```typescript
export interface Expense {
  id: string
  amount: string
  currency: string
  category: string
  date: string
  description: string | null
}

export interface CreateExpensePayload {
  amount: string
  currency: string
  category: string
  date: string
  description?: string
}

export async function createExpense(payload: CreateExpensePayload): Promise<Expense> {
  const response = await fetch('/expenses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error(`Failed to create expense: ${response.status}`)
  }
  return response.json()
}

export async function listExpenses(): Promise<Expense[]> {
  const response = await fetch('/expenses')
  if (!response.ok) {
    throw new Error(`Failed to fetch expenses: ${response.status}`)
  }
  return response.json()
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build
```

Expected: build succeeds (the new file has no TS errors)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.ts
git commit -m "feat: add api.ts fetch wrapper"
```

---

## Task 9: ExpenseList component

**Files:**
- Create: `frontend/src/components/ExpenseList.tsx`

- [ ] **Step 1: Create `frontend/src/components/`**

```bash
mkdir -p frontend/src/components
```

- [ ] **Step 2: Create `frontend/src/components/ExpenseList.tsx`**

```tsx
import { Expense } from '../api'

interface Props {
  expenses: Expense[]
}

export function ExpenseList({ expenses }: Props) {
  if (expenses.length === 0) {
    return <p>No expenses yet.</p>
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Category</th>
          <th>Amount</th>
          <th>Currency</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        {expenses.map((e) => (
          <tr key={e.id}>
            <td>{e.date}</td>
            <td>{e.category}</td>
            <td>{e.amount}</td>
            <td>{e.currency}</td>
            <td>{e.description ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ExpenseList.tsx
git commit -m "feat: add ExpenseList component"
```

---

## Task 10: ExpenseForm component

**Files:**
- Create: `frontend/src/components/ExpenseForm.tsx`

- [ ] **Step 1: Create `frontend/src/components/ExpenseForm.tsx`**

```tsx
import { useState, FormEvent } from 'react'
import { createExpense } from '../api'

interface Props {
  onExpenseAdded: () => void
}

export function ExpenseForm({ onExpenseAdded }: Props) {
  const [amount, setAmount] = useState('')
  const [currency, setCurrency] = useState('EUR')
  const [category, setCategory] = useState('')
  const [date, setDate] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await createExpense({
        amount,
        currency,
        category,
        date,
        description: description || undefined,
      })
      setAmount('')
      setCategory('')
      setDate('')
      setDescription('')
      onExpenseAdded()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label htmlFor="amount">Amount</label>
        <input
          id="amount"
          type="number"
          step="0.01"
          min="0.01"
          required
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="currency">Currency</label>
        <input
          id="currency"
          type="text"
          required
          value={currency}
          onChange={(e) => setCurrency(e.target.value.toUpperCase())}
        />
      </div>
      <div>
        <label htmlFor="category">Category</label>
        <input
          id="category"
          type="text"
          required
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="date">Date</label>
        <input
          id="date"
          type="date"
          required
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="description">Description (optional)</label>
        <input
          id="description"
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <button type="submit">Add Expense</button>
    </form>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ExpenseForm.tsx
git commit -m "feat: add ExpenseForm component"
```

---

## Task 11: App component and end-to-end verification

**Files:**
- Modify: `frontend/src/App.tsx` (replace scaffold content)

- [ ] **Step 1: Replace `frontend/src/App.tsx`**

```tsx
import { useState, useEffect, useCallback } from 'react'
import { listExpenses, Expense } from './api'
import { ExpenseForm } from './components/ExpenseForm'
import { ExpenseList } from './components/ExpenseList'

function App() {
  const [expenses, setExpenses] = useState<Expense[]>([])

  const fetchExpenses = useCallback(async () => {
    const data = await listExpenses()
    setExpenses(data)
  }, [])

  useEffect(() => {
    fetchExpenses()
  }, [fetchExpenses])

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem' }}>
      <h1>Finance Tracker</h1>
      <h2>Add Expense</h2>
      <ExpenseForm onExpenseAdded={fetchExpenses} />
      <h2>Expenses</h2>
      <ExpenseList expenses={expenses} />
    </div>
  )
}

export default App
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 3: Run full end-to-end verification**

Start the backend:
```bash
cd backend && uvicorn adapters.api.main:app --reload
```

In a second terminal, start the frontend:
```bash
cd frontend && npm run dev
```

Open `http://localhost:5173` in a browser.

Verify:
- The page loads with the form and "No expenses yet."
- Fill in the form (e.g. amount=12.50, currency=EUR, category=lunch, date=2026-04-11) and click "Add Expense"
- The expense appears in the table without a page reload
- Refresh the page — the expense persists (loaded from SQLite)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: wire App component — first vertical slice complete"
```

---

## Task 12: CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Create `CLAUDE.md` at the repo root**

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

Hexagonal (Ports & Adapters). `backend/domain/` has zero external dependencies — it never imports from `adapters/`. `backend/adapters/` imports from `domain/`. The only file that names concrete types from both sides is `backend/adapters/api/main.py` (the composition root).

## Running the backend

```bash
cd backend
pip install -r requirements.txt          # first time only
uvicorn adapters.api.main:app --reload
```

API available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

## Running the frontend

```bash
cd frontend
npm install                              # first time only
npm run dev
```

UI available at `http://localhost:5173`. Dev proxy forwards `/expenses` to `http://localhost:8000` — no CORS config needed.

## Running backend tests

```bash
cd backend
pytest -v
```

Run a single test:
```bash
cd backend && pytest tests/test_use_cases.py::test_add_expense_returns_saved_expense -v
```

Domain tests (`test_use_cases.py`) use `FakeExpenseRepository` — no SQLite, no HTTP. API tests (`test_api.py`) use `TestClient` with a temp SQLite file.

## Key conventions

- Pydantic request/response models live in `adapters/api/routes.py`, not in `domain/`
- `amount` is always `Decimal`, never `float`; stored as `TEXT` in SQLite
- Sorting of expenses by date is the use case's responsibility, not the repository's
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md with architecture and dev commands"
```
