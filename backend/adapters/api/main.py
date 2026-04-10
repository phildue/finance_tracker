from fastapi import FastAPI

from adapters.sqlite_repository import SqliteExpenseRepository
from adapters.api.routes import build_router
from domain.use_cases import AddExpense, ListExpenses

app = FastAPI(title="Finance Tracker")

_repo = SqliteExpenseRepository("expenses.db")
app.include_router(build_router(AddExpense(_repo), ListExpenses(_repo)))
