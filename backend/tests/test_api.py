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
