from abc import ABC, abstractmethod
from .expense import Expense


class ExpenseRepository(ABC):
    @abstractmethod
    def save(self, expense: Expense) -> None: ...

    @abstractmethod
    def list_all(self) -> list[Expense]: ...
