from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Expense:
    amount: Decimal
    currency: str
    category: str
    date: date
    description: Optional[str] = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("amount must be positive")


class ExpenseNotFound(Exception):
    pass
