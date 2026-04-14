from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from domain.expense import Expense, ExpenseNotFound
from domain.use_cases import AddExpense, ListExpenses, DeleteExpense, DeleteAllExpenses


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


class BulkDeleteRequest(BaseModel):
    ids: list[UUID]


def _to_response(expense: Expense) -> ExpenseResponse:
    return ExpenseResponse(
        id=expense.id,
        amount=expense.amount,
        currency=expense.currency,
        category=expense.category,
        date=expense.date,
        description=expense.description,
    )


def build_router(
    add_expense: AddExpense,
    list_expenses: ListExpenses,
    delete_expense: DeleteExpense,
    delete_all_expenses: DeleteAllExpenses,
) -> APIRouter:
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

    @router.delete("/expenses/bulk", status_code=204)
    def delete_expenses_bulk(body: BulkDeleteRequest) -> None:
        for expense_id in body.ids:
            try:
                delete_expense.execute(expense_id)
            except ExpenseNotFound:
                pass

    @router.delete("/expenses/{id}", status_code=204)
    def delete_expense_by_id(id: UUID) -> None:
        try:
            delete_expense.execute(id)
        except ExpenseNotFound:
            raise HTTPException(status_code=404, detail="Expense not found")

    @router.delete("/expenses", status_code=204)
    def delete_all() -> None:
        delete_all_expenses.execute()

    @router.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return router
