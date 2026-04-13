import sqlite3
from datetime import date
from decimal import Decimal
from uuid import UUID

from domain.expense import Expense, ExpenseNotFound
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
