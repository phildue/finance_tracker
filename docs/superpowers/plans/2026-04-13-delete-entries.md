# Delete Entries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to select one or more expense entries via checkboxes and delete them (or delete all) with a confirmation dialog.

**Architecture:** Backend gets a domain exception (`ExpenseNotFound`), two new use cases (`DeleteExpense`, `DeleteAllExpenses`), three new API endpoints, and SQLite implementations. Frontend adds checkbox selection state to `ExpenseList`, a conditional bulk-action toolbar, and three new API functions in `api.ts`.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript (frontend), SQLite, pytest, Vite dev server

---

## File Map

| File | Change |
|------|--------|
| `backend/domain/expense.py` | Add `ExpenseNotFound` exception |
| `backend/domain/ports.py` | Add `delete(id)` and `delete_all()` abstract methods |
| `backend/domain/use_cases.py` | Add `DeleteExpense` and `DeleteAllExpenses` use cases |
| `backend/adapters/sqlite_repository.py` | Implement `delete` and `delete_all` |
| `backend/adapters/api/routes.py` | Add three DELETE endpoints; extend `build_router` signature |
| `backend/adapters/api/main.py` | Wire new use cases into `build_router` |
| `backend/tests/test_use_cases.py` | Extend `FakeExpenseRepository`; add use case tests |
| `backend/tests/test_api.py` | Update `client` fixture; add API delete tests |
| `frontend/src/api.ts` | Add `deleteExpense`, `deleteExpenses`, `deleteAllExpenses` |
| `frontend/src/components/ExpenseList.tsx` | Add checkboxes, selection state, bulk toolbar |
| `frontend/src/App.tsx` | Pass `onDeleted` / `onDeleteError` to `ExpenseList` |

---

## Task 1: Add `ExpenseNotFound` and extend the port

**Files:**
- Modify: `backend/domain/expense.py`
- Modify: `backend/domain/ports.py`
- Modify: `backend/adapters/sqlite_repository.py`
- Modify: `backend/tests/test_use_cases.py`

- [ ] **Step 1: Add `ExpenseNotFound` to `domain/expense.py`**

  Append after the `Expense` class:

  ```python
  class ExpenseNotFound(Exception):
      pass
  ```

- [ ] **Step 2: Add abstract methods to `domain/ports.py`**

  The file currently imports only `Expense`. Add `UUID` to the imports and two new abstract methods:

  ```python
  from abc import ABC, abstractmethod
  from uuid import UUID
  from .expense import Expense


  class ExpenseRepository(ABC):
      @abstractmethod
      def save(self, expense: Expense) -> None: ...

      @abstractmethod
      def list_all(self) -> list[Expense]: ...

      @abstractmethod
      def delete(self, id: UUID) -> None: ...

      @abstractmethod
      def delete_all(self) -> None: ...
  ```

- [ ] **Step 3: Add stub implementations to `SqliteExpenseRepository`**

  Adding abstract methods to the port makes `SqliteExpenseRepository` non-instantiable until it implements them. Add stubs at the bottom of the class (real implementation comes in Task 4):

  ```python
  def delete(self, id: UUID) -> None:
      raise NotImplementedError

  def delete_all(self) -> None:
      raise NotImplementedError
  ```

  Also add `UUID` to the imports at the top of `adapters/sqlite_repository.py` — it already imports `UUID`, so verify it's there.

- [ ] **Step 4: Extend `FakeExpenseRepository` in `tests/test_use_cases.py`**

  The fake is defined in the test file. Add `delete` and `delete_all`, and update the import line so `ExpenseNotFound` and `UUID` are available:

  ```python
  from uuid import UUID
  from domain.expense import Expense, ExpenseNotFound
  from domain.ports import ExpenseRepository
  from domain.use_cases import AddExpense, ListExpenses
  ```

  Add methods to `FakeExpenseRepository`:

  ```python
  def delete(self, id: UUID) -> None:
      match = [e for e in self._expenses if e.id == id]
      if not match:
          raise ExpenseNotFound(id)
      self._expenses = [e for e in self._expenses if e.id != id]

  def delete_all(self) -> None:
      self._expenses = []
  ```

- [ ] **Step 5: Run existing tests to verify nothing broke**

  ```bash
  cd backend && pytest -v
  ```

  Expected: all existing tests pass (the `NotImplementedError` stubs are never called by existing tests).

- [ ] **Step 6: Commit**

  ```bash
  git add backend/domain/expense.py backend/domain/ports.py \
          backend/adapters/sqlite_repository.py backend/tests/test_use_cases.py
  git commit -m "feat: add ExpenseNotFound exception and delete port methods"
  ```

---

## Task 2: `DeleteExpense` use case (TDD)

**Files:**
- Modify: `backend/tests/test_use_cases.py`
- Modify: `backend/domain/use_cases.py`

- [ ] **Step 1: Write the failing tests**

  Add to `tests/test_use_cases.py` (also add `DeleteExpense` to the import line):

  ```python
  from domain.use_cases import AddExpense, ListExpenses, DeleteExpense
  ```

  ```python
  def test_delete_expense_removes_it_from_repository():
      repo = FakeExpenseRepository()
      add = AddExpense(repo)
      expense = add.execute(Decimal("10"), "EUR", "food", date(2026, 4, 11))

      DeleteExpense(repo).execute(expense.id)

      assert repo.list_all() == []


  def test_delete_expense_raises_when_not_found():
      repo = FakeExpenseRepository()
      import uuid
      with pytest.raises(ExpenseNotFound):
          DeleteExpense(repo).execute(uuid.uuid4())
  ```

- [ ] **Step 2: Run to verify they fail**

  ```bash
  cd backend && pytest tests/test_use_cases.py::test_delete_expense_removes_it_from_repository tests/test_use_cases.py::test_delete_expense_raises_when_not_found -v
  ```

  Expected: `ImportError` — `DeleteExpense` not defined yet.

- [ ] **Step 3: Implement `DeleteExpense` in `domain/use_cases.py`**

  Add at the end of the file. Also add `UUID` to the imports:

  ```python
  from uuid import UUID
  ```

  ```python
  class DeleteExpense:
      def __init__(self, repository: ExpenseRepository) -> None:
          self._repository = repository

      def execute(self, id: UUID) -> None:
          self._repository.delete(id)
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  cd backend && pytest tests/test_use_cases.py::test_delete_expense_removes_it_from_repository tests/test_use_cases.py::test_delete_expense_raises_when_not_found -v
  ```

  Expected: both PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/domain/use_cases.py backend/tests/test_use_cases.py
  git commit -m "feat: add DeleteExpense use case"
  ```

---

## Task 3: `DeleteAllExpenses` use case (TDD)

**Files:**
- Modify: `backend/tests/test_use_cases.py`
- Modify: `backend/domain/use_cases.py`

- [ ] **Step 1: Write the failing test**

  Add to `tests/test_use_cases.py` (update import to include `DeleteAllExpenses`):

  ```python
  from domain.use_cases import AddExpense, ListExpenses, DeleteExpense, DeleteAllExpenses
  ```

  ```python
  def test_delete_all_expenses_empties_repository():
      repo = FakeExpenseRepository()
      add = AddExpense(repo)
      add.execute(Decimal("10"), "EUR", "food", date(2026, 4, 11))
      add.execute(Decimal("20"), "EUR", "transport", date(2026, 4, 12))

      DeleteAllExpenses(repo).execute()

      assert repo.list_all() == []
  ```

- [ ] **Step 2: Run to verify it fails**

  ```bash
  cd backend && pytest tests/test_use_cases.py::test_delete_all_expenses_empties_repository -v
  ```

  Expected: `ImportError` — `DeleteAllExpenses` not defined yet.

- [ ] **Step 3: Implement `DeleteAllExpenses` in `domain/use_cases.py`**

  Add at the end of the file:

  ```python
  class DeleteAllExpenses:
      def __init__(self, repository: ExpenseRepository) -> None:
          self._repository = repository

      def execute(self) -> None:
          self._repository.delete_all()
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  cd backend && pytest tests/test_use_cases.py::test_delete_all_expenses_empties_repository -v
  ```

  Expected: PASS.

- [ ] **Step 5: Run full suite**

  ```bash
  cd backend && pytest -v
  ```

  Expected: all tests pass.

- [ ] **Step 6: Commit**

  ```bash
  git add backend/domain/use_cases.py backend/tests/test_use_cases.py
  git commit -m "feat: add DeleteAllExpenses use case"
  ```

---

## Task 4: SQLite repository delete methods (TDD)

**Files:**
- Modify: `backend/tests/test_api.py`
- Modify: `backend/adapters/sqlite_repository.py`

- [ ] **Step 1: Write failing SQLite repository tests**

  Add to `tests/test_api.py`. Update the imports to include the new classes:

  ```python
  from domain.use_cases import AddExpense, ListExpenses, DeleteExpense, DeleteAllExpenses
  from domain.expense import ExpenseNotFound
  ```

  Add tests (these use the `repo` fixture from the existing file — a `SqliteExpenseRepository` backed by a tmp db):

  ```python
  def test_sqlite_repo_delete_removes_expense(repo):
      expense = Expense(
          amount=Decimal("10"),
          currency="EUR",
          category="food",
          date=date(2026, 4, 11),
      )
      repo.save(expense)
      repo.delete(expense.id)
      assert repo.list_all() == []


  def test_sqlite_repo_delete_raises_when_not_found(repo):
      import uuid
      with pytest.raises(ExpenseNotFound):
          repo.delete(uuid.uuid4())


  def test_sqlite_repo_delete_all_empties_table(repo):
      repo.save(Expense(amount=Decimal("10"), currency="EUR", category="a", date=date(2026, 4, 11)))
      repo.save(Expense(amount=Decimal("20"), currency="EUR", category="b", date=date(2026, 4, 12)))
      repo.delete_all()
      assert repo.list_all() == []
  ```

- [ ] **Step 2: Run to verify they fail**

  ```bash
  cd backend && pytest tests/test_api.py::test_sqlite_repo_delete_removes_expense tests/test_api.py::test_sqlite_repo_delete_raises_when_not_found tests/test_api.py::test_sqlite_repo_delete_all_empties_table -v
  ```

  Expected: FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement delete methods in `SqliteExpenseRepository`**

  Replace the `NotImplementedError` stubs. Also add `ExpenseNotFound` to the imports at the top:

  ```python
  from domain.expense import Expense, ExpenseNotFound
  ```

  ```python
  def delete(self, id: UUID) -> None:
      with self._connect() as conn:
          cursor = conn.execute(
              "DELETE FROM expenses WHERE id = ?", (str(id),)
          )
          if cursor.rowcount == 0:
              raise ExpenseNotFound(id)

  def delete_all(self) -> None:
      with self._connect() as conn:
          conn.execute("DELETE FROM expenses")
  ```

- [ ] **Step 4: Run the new tests to verify they pass**

  ```bash
  cd backend && pytest tests/test_api.py::test_sqlite_repo_delete_removes_expense tests/test_api.py::test_sqlite_repo_delete_raises_when_not_found tests/test_api.py::test_sqlite_repo_delete_all_empties_table -v
  ```

  Expected: all PASS.

- [ ] **Step 5: Run full suite**

  ```bash
  cd backend && pytest -v
  ```

  Expected: all tests pass.

- [ ] **Step 6: Commit**

  ```bash
  git add backend/adapters/sqlite_repository.py backend/tests/test_api.py
  git commit -m "feat: implement delete methods in SqliteExpenseRepository"
  ```

---

## Task 5: API delete endpoints (TDD)

**Files:**
- Modify: `backend/tests/test_api.py`
- Modify: `backend/adapters/api/routes.py`
- Modify: `backend/adapters/api/main.py`

- [ ] **Step 1: Update the `client` fixture to wire the new use cases**

  The existing `client` fixture in `tests/test_api.py` calls `build_router(AddExpense(...), ListExpenses(...))`. Update it to also pass the delete use cases (the signature change happens in Step 3 — add both fixture and route changes together so the test file stays valid):

  ```python
  @pytest.fixture
  def client(tmp_path):
      db_path = str(tmp_path / "api_test.db")
      repository = SqliteExpenseRepository(db_path)
      app = FastAPI()
      app.include_router(build_router(
          AddExpense(repository),
          ListExpenses(repository),
          DeleteExpense(repository),
          DeleteAllExpenses(repository),
      ))
      return TestClient(app)
  ```

- [ ] **Step 2: Write failing API tests for delete endpoints**

  Add to `tests/test_api.py`:

  ```python
  def test_delete_expense_returns_204(client):
      post = client.post(
          "/expenses",
          json={"amount": "10", "currency": "EUR", "category": "food", "date": "2026-04-11"},
      )
      expense_id = post.json()["id"]

      response = client.delete(f"/expenses/{expense_id}")

      assert response.status_code == 204
      assert client.get("/expenses").json() == []


  def test_delete_expense_returns_404_when_not_found(client):
      import uuid
      response = client.delete(f"/expenses/{uuid.uuid4()}")
      assert response.status_code == 404


  def test_delete_bulk_returns_204(client):
      id1 = client.post("/expenses", json={"amount": "10", "currency": "EUR", "category": "a", "date": "2026-04-11"}).json()["id"]
      id2 = client.post("/expenses", json={"amount": "20", "currency": "EUR", "category": "b", "date": "2026-04-12"}).json()["id"]
      client.post("/expenses", json={"amount": "5", "currency": "EUR", "category": "c", "date": "2026-04-13"})

      response = client.delete("/expenses/bulk", json={"ids": [id1, id2]})

      assert response.status_code == 204
      remaining = client.get("/expenses").json()
      assert len(remaining) == 1
      assert remaining[0]["category"] == "c"


  def test_delete_all_returns_204(client):
      client.post("/expenses", json={"amount": "10", "currency": "EUR", "category": "a", "date": "2026-04-11"})
      client.post("/expenses", json={"amount": "20", "currency": "EUR", "category": "b", "date": "2026-04-12"})

      response = client.delete("/expenses")

      assert response.status_code == 204
      assert client.get("/expenses").json() == []
  ```

- [ ] **Step 3: Run to verify they fail**

  ```bash
  cd backend && pytest tests/test_api.py::test_delete_expense_returns_204 tests/test_api.py::test_delete_expense_returns_404_when_not_found tests/test_api.py::test_delete_bulk_returns_204 tests/test_api.py::test_delete_all_returns_204 -v
  ```

  Expected: FAIL — `build_router` doesn't accept the new use case params yet.

- [ ] **Step 4: Add delete endpoints to `adapters/api/routes.py`**

  Update the imports at the top of `routes.py`. The existing `from fastapi import APIRouter` line becomes:

  ```python
  from fastapi import APIRouter, HTTPException
  ```

  Also add:

  ```python
  from domain.expense import ExpenseNotFound
  from domain.use_cases import AddExpense, ListExpenses, DeleteExpense, DeleteAllExpenses
  ```

  Add a request model for bulk delete (place it with the other request models):

  ```python
  class BulkDeleteRequest(BaseModel):
      ids: list[UUID]
  ```

  Update `build_router` signature and add the three new routes:

  ```python
  def build_router(
      add_expense: AddExpense,
      list_expenses: ListExpenses,
      delete_expense: DeleteExpense,
      delete_all_expenses: DeleteAllExpenses,
  ) -> APIRouter:
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

      @router.delete("/expenses/bulk", status_code=204)
      def delete_expenses_bulk(body: BulkDeleteRequest) -> None:
          for id in body.ids:
              try:
                  delete_expense.execute(id)
              except ExpenseNotFound:
                  pass

      @router.delete("/expenses/{id}", status_code=204)
      def delete_expense_by_id(id: UUID) -> None:
          try:
              delete_expense.execute(id)
          except ExpenseNotFound:
              raise HTTPException(status_code=404, detail="Expense not found")

      @router.delete("/expenses", status_code=204)
      def delete_all() -> None:
          delete_all_expenses.execute()

      @router.get("/health")
      def health() -> dict:
          return {"status": "ok"}

      return router
  ```

  > **Note on route order:** FastAPI matches routes top-to-bottom. `/expenses/bulk` must be registered **before** `/expenses/{id}` so the literal path `bulk` doesn't get swallowed as a UUID parameter. The order above is correct.

- [ ] **Step 5: Update `adapters/api/main.py` to wire the new use cases**

  ```python
  import os

  from fastapi import FastAPI

  from adapters.sqlite_repository import SqliteExpenseRepository
  from adapters.api.routes import build_router
  from domain.use_cases import AddExpense, ListExpenses, DeleteExpense, DeleteAllExpenses

  app = FastAPI(title="Finance Tracker")

  _db_path = os.environ.get("DB_PATH", "expenses.db")
  _repo = SqliteExpenseRepository(_db_path)
  app.include_router(build_router(
      AddExpense(_repo),
      ListExpenses(_repo),
      DeleteExpense(_repo),
      DeleteAllExpenses(_repo),
  ))
  ```

- [ ] **Step 6: Run the new tests to verify they pass**

  ```bash
  cd backend && pytest tests/test_api.py::test_delete_expense_returns_204 tests/test_api.py::test_delete_expense_returns_404_when_not_found tests/test_api.py::test_delete_bulk_returns_204 tests/test_api.py::test_delete_all_returns_204 -v
  ```

  Expected: all PASS.

- [ ] **Step 7: Run full suite**

  ```bash
  cd backend && pytest -v
  ```

  Expected: all tests pass.

- [ ] **Step 8: Commit**

  ```bash
  git add backend/adapters/api/routes.py backend/adapters/api/main.py backend/tests/test_api.py
  git commit -m "feat: add DELETE /expenses endpoints (single, bulk, all)"
  ```

---

## Task 6: Frontend API functions

**Files:**
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: Add three delete functions to `api.ts`**

  Append to the end of `frontend/src/api.ts`:

  ```ts
  export async function deleteExpense(id: string): Promise<void> {
    const response = await fetch(`/expenses/${id}`, { method: 'DELETE' })
    if (!response.ok) {
      throw new Error(`Failed to delete expense: ${response.status}`)
    }
  }

  export async function deleteExpenses(ids: string[]): Promise<void> {
    const response = await fetch('/expenses/bulk', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids }),
    })
    if (!response.ok) {
      throw new Error(`Failed to delete expenses: ${response.status}`)
    }
  }

  export async function deleteAllExpenses(): Promise<void> {
    const response = await fetch('/expenses', { method: 'DELETE' })
    if (!response.ok) {
      throw new Error(`Failed to delete all expenses: ${response.status}`)
    }
  }
  ```

- [ ] **Step 2: Verify TypeScript compiles**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

  Expected: no errors.

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/api.ts
  git commit -m "feat: add deleteExpense, deleteExpenses, deleteAllExpenses to api.ts"
  ```

---

## Task 7: `ExpenseList.tsx` — checkboxes and bulk toolbar

**Files:**
- Modify: `frontend/src/components/ExpenseList.tsx`

- [ ] **Step 1: Rewrite `ExpenseList.tsx`**

  Replace the entire file with:

  ```tsx
  import { useState } from 'react'
  import type { Expense } from '../api'
  import { deleteExpenses, deleteAllExpenses } from '../api'

  interface Props {
    expenses: Expense[]
    onDeleted: () => void
    onDeleteError: (msg: string) => void
  }

  export function ExpenseList({ expenses, onDeleted, onDeleteError }: Props) {
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

    if (expenses.length === 0) {
      return <p>No expenses yet.</p>
    }

    const allSelected = selectedIds.size === expenses.length
    const someSelected = selectedIds.size > 0 && !allSelected

    function toggleAll() {
      if (allSelected) {
        setSelectedIds(new Set())
      } else {
        setSelectedIds(new Set(expenses.map((e) => e.id)))
      }
    }

    function toggleRow(id: string) {
      const next = new Set(selectedIds)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      setSelectedIds(next)
    }

    async function handleDeleteSelected() {
      if (!window.confirm(`Delete ${selectedIds.size} selected ${selectedIds.size === 1 ? 'entry' : 'entries'}?`)) return
      try {
        await deleteExpenses([...selectedIds])
        setSelectedIds(new Set())
        onDeleted()
      } catch (err) {
        onDeleteError(err instanceof Error ? err.message : 'Failed to delete entries')
      }
    }

    async function handleDeleteAll() {
      if (!window.confirm('Delete all entries?')) return
      try {
        await deleteAllExpenses()
        setSelectedIds(new Set())
        onDeleted()
      } catch (err) {
        onDeleteError(err instanceof Error ? err.message : 'Failed to delete all entries')
      }
    }

    return (
      <>
        {selectedIds.size > 0 && (
          <div>
            <span>{selectedIds.size} selected</span>
            {' '}
            <button onClick={handleDeleteSelected}>Delete selected</button>
            {' '}
            <button onClick={handleDeleteAll}>Delete all</button>
          </div>
        )}
        <table>
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(el) => { if (el) el.indeterminate = someSelected }}
                  onChange={toggleAll}
                />
              </th>
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
                <td>
                  <input
                    type="checkbox"
                    checked={selectedIds.has(e.id)}
                    onChange={() => toggleRow(e.id)}
                  />
                </td>
                <td>{e.date}</td>
                <td>{e.category}</td>
                <td>{e.amount}</td>
                <td>{e.currency}</td>
                <td>{e.description ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </>
    )
  }
  ```

- [ ] **Step 2: Verify TypeScript compiles**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

  Expected: errors about missing `onDeleted` / `onDeleteError` props in `App.tsx` (not yet updated). That's expected — proceed to Task 8.

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/components/ExpenseList.tsx
  git commit -m "feat: add checkbox selection and bulk delete toolbar to ExpenseList"
  ```

---

## Task 8: Wire `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Update `App.tsx`**

  Replace the entire file with:

  ```tsx
  import { useState, useEffect, useCallback } from 'react'
  import { listExpenses } from './api'
  import type { Expense } from './api'
  import { ExpenseForm } from './components/ExpenseForm'
  import { ExpenseList } from './components/ExpenseList'

  function App() {
    const [expenses, setExpenses] = useState<Expense[]>([])
    const [fetchError, setFetchError] = useState<string | null>(null)
    const [deleteError, setDeleteError] = useState<string | null>(null)

    const fetchExpenses = useCallback(async () => {
      try {
        const data = await listExpenses()
        setExpenses(data)
        setFetchError(null)
      } catch (err) {
        setFetchError(err instanceof Error ? err.message : 'Failed to load expenses')
      }
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
        {fetchError && <p style={{ color: 'red' }}>{fetchError}</p>}
        {deleteError && <p style={{ color: 'red' }}>{deleteError}</p>}
        <ExpenseList
          expenses={expenses}
          onDeleted={fetchExpenses}
          onDeleteError={setDeleteError}
        />
      </div>
    )
  }

  export default App
  ```

- [ ] **Step 2: Verify TypeScript compiles cleanly**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

  Expected: no errors.

- [ ] **Step 3: Smoke test in the browser**

  Start the backend and frontend:

  ```bash
  # Terminal 1
  cd backend && uvicorn adapters.api.main:app --reload

  # Terminal 2
  cd frontend && npm run dev
  ```

  Open `http://localhost:5173` and verify:
  - Expenses table has a checkbox column
  - Checking a row reveals the toolbar with "Delete selected" and "Delete all" buttons
  - Header checkbox selects/deselects all rows
  - "Delete selected" shows a confirm dialog and removes checked rows on confirm
  - "Delete all" shows a confirm dialog and clears the list on confirm
  - Dismissing the dialog cancels the action

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/App.tsx
  git commit -m "feat: wire delete callbacks into App"
  ```
