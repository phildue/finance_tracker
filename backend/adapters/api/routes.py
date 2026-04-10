from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from domain.expense import Expense
from domain.use_cases import AddExpense, ListExpenses


class CreateExpenseRequest(BaseModel):
    amount: Decimal
    currency: str
    category: str
    date: date
    description: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be positive")
        return v


class ExpenseResponse(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    category: str
    date: date
    description: Optional[str]


def _to_response(expense: Expense) -> ExpenseResponse:
    return ExpenseResponse(
        id=expense.id,
        amount=expense.amount,
        currency=expense.currency,
        category=expense.category,
        date=expense.date,
        description=expense.description,
    )


def build_router(add_expense: AddExpense, list_expenses: ListExpenses) -> APIRouter:
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

    return router
