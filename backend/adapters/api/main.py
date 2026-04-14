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
