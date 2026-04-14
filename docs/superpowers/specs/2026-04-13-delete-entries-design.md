# Delete Entries Feature — Design Spec

**Date:** 2026-04-13  
**Issue:** #3 — Add remove entry button

## Summary

Allow users to delete one or more expense entries from the list. Selection is checkbox-based; a bulk action toolbar appears once at least one row is checked. Deletion requires a confirmation dialog. A "Delete all" shortcut is available from the toolbar.

## UX

- Each row in `ExpenseList` has a checkbox in a leading column.
- A header checkbox toggles all rows (checked = all selected, indeterminate = some selected, unchecked = none).
- When at least one row is checked, a toolbar appears above the table with:
  - A count label ("N selected")
  - **Delete selected** button — deletes the checked rows
  - **Delete all** button — deletes every entry regardless of selection
- Both buttons show a `window.confirm()` dialog before proceeding.
- After a successful delete the expense list refreshes automatically.
- Delete errors are displayed above the table (same pattern as existing fetch errors).

## Backend — Domain

### Port changes (`domain/ports.py`)

Two new abstract methods on `ExpenseRepository`:

```python
@abstractmethod
def delete(self, id: UUID) -> None: ...

@abstractmethod
def delete_all(self) -> None: ...
```

### New exception (`domain/expense.py` or `domain/exceptions.py`)

```python
class ExpenseNotFound(Exception):
    pass
```

### New use cases (`domain/use_cases.py`)

```python
class DeleteExpense:
    def execute(self, id: UUID) -> None: ...   # raises ExpenseNotFound if id does not exist

class DeleteAllExpenses:
    def execute(self) -> None: ...
```

## Backend — Adapter

### SQLite repository (`adapters/sqlite_repository.py`)

```python
def delete(self, id: UUID) -> None:
    # DELETE FROM expenses WHERE id = ?

def delete_all(self) -> None:
    # DELETE FROM expenses
```

### API routes (`adapters/api/routes.py`)

Three new endpoints, all returning 204 No Content:

| Method | Path | Body | Action |
|--------|------|------|--------|
| DELETE | `/expenses/{id}` | — | Delete one entry (404 if not found) |
| DELETE | `/expenses/bulk` | `{"ids": ["uuid", ...]}` | Delete selected entries |
| DELETE | `/expenses` | — | Delete all entries |

`build_router` receives two additional use case params: `delete_expense: DeleteExpense` and `delete_all_expenses: DeleteAllExpenses`.

### Composition root (`adapters/api/main.py`)

Instantiates and wires `DeleteExpense` and `DeleteAllExpenses` into `build_router`.

## Frontend

### `api.ts`

Three new functions:

```ts
deleteExpense(id: string): Promise<void>          // DELETE /expenses/{id}
deleteExpenses(ids: string[]): Promise<void>      // DELETE /expenses/bulk
deleteAllExpenses(): Promise<void>                // DELETE /expenses
```

### `ExpenseList.tsx`

New props:
```ts
onDeleted: () => void
onDeleteError: (msg: string) => void
```

New state:
```ts
selectedIds: Set<string>
```

Behaviour:
- Checkbox column added as the first column.
- Header checkbox: checked when `selectedIds.size === expenses.length`, indeterminate when `0 < selectedIds.size < expenses.length`.
- Toolbar renders when `selectedIds.size > 0`.
- "Delete selected": `window.confirm("Delete N selected entries?")` → `deleteExpenses([...selectedIds])` → `onDeleted()`.
- "Delete all": `window.confirm("Delete all entries?")` → `deleteAllExpenses()` → `onDeleted()`.
- On error: calls `onDeleteError(message)`.
- Clears `selectedIds` after any successful delete.

### `App.tsx`

Passes `onDeleted={fetchExpenses}` and `onDeleteError` (sets a `deleteError` state) to `ExpenseList`. Displays `deleteError` above the expenses section.

## Testing

### Backend unit tests (`tests/test_use_cases.py`)

- `DeleteExpense` removes the correct entry from the fake repository.
- `DeleteExpense` with unknown ID raises `ExpenseNotFound`.
- `DeleteAllExpenses` empties the repository.

### Backend API tests (`tests/test_api.py`)

- `DELETE /expenses/{id}` returns 204 and the entry is gone.
- `DELETE /expenses/{id}` with unknown ID returns 404.
- `DELETE /expenses/bulk` returns 204 and listed entries are gone.
- `DELETE /expenses` returns 204 and the list is empty.
