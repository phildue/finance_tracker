from datetime import date
from decimal import Decimal
from uuid import UUID
import pytest
from domain.expense import Expense, ExpenseNotFound
from domain.ports import ExpenseRepository
from domain.use_cases import AddExpense, ListExpenses, DeleteExpense


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


class FakeExpenseRepository(ExpenseRepository):
    def __init__(self) -> None:
        self._expenses: list[Expense] = []

    def save(self, expense: Expense) -> None:
        self._expenses.append(expense)

    def list_all(self) -> list[Expense]:
        return list(self._expenses)

    def delete(self, id: UUID) -> None:
        match = [e for e in self._expenses if e.id == id]
        if not match:
            raise ExpenseNotFound(id)
        self._expenses = [e for e in self._expenses if e.id != id]

    def delete_all(self) -> None:
        self._expenses = []


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
