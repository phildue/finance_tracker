from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

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


class DeleteExpense:
    def __init__(self, repository: ExpenseRepository) -> None:
        self._repository = repository

    def execute(self, id: UUID) -> None:
        self._repository.delete(id)
