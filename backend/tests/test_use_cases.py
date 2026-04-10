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
