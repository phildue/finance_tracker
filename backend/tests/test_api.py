import pytest
from decimal import Decimal
from datetime import date
import uuid
from domain.expense import Expense, ExpenseNotFound
from adapters.sqlite_repository import SqliteExpenseRepository
from fastapi import FastAPI
from fastapi.testclient import TestClient
from domain.use_cases import AddExpense, ListExpenses
from adapters.api.routes import build_router


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


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
    with pytest.raises(ExpenseNotFound):
        repo.delete(uuid.uuid4())


def test_sqlite_repo_delete_all_empties_table(repo):
    repo.save(Expense(amount=Decimal("10"), currency="EUR", category="a", date=date(2026, 4, 11)))
    repo.save(Expense(amount=Decimal("20"), currency="EUR", category="b", date=date(2026, 4, 12)))
    repo.delete_all()
    assert repo.list_all() == []
