"""Enum definitions for homeapp service."""

from enum import Enum


class CategoryExpense(str, Enum):
    """Expense-specific categories (spending)."""

    Groceries = 'Groceries'
    EatOut = 'EatOut'
    Transportation = 'Transportation'
    Mortgage = 'Mortgage'
    Utilities = 'Utilities'
    Shopping = 'Shopping'
    Gas = 'Gas'
    Insurance = 'Insurance'

    @classmethod
    def values(cls) -> set[str]:
        """Set of all expense category values."""
        return {c.value for c in cls}


class CategoryEarning(str, Enum):
    """Earning-specific categories (income)."""

    Salary = 'Salary'

    @classmethod
    def values(cls) -> set[str]:
        """Set of all earning category values."""
        return {c.value for c in cls}


# Dynamic union of expense and earning categories to avoid repetition
Category = Enum(
    'Category',
    [(m.name, m.value) for m in list(CategoryExpense) + list(CategoryEarning)],
    type=str
)


class TransactionType(str, Enum):
    """Transaction type enum."""

    Credit = 'Credit'  # Income / Earning
    Debit = 'Debit'  # Expense / Spending


class Currency(str, Enum):
    """Currency enum."""

    CAD = 'CAD'
    RMB = 'RMB'


class Frequency(str, Enum):
    """Payment frequency enum."""

    Weekly = 'Weekly'
    Biweekly = 'Biweekly'
    Monthly = 'Monthly'


class CollectionName(str, Enum):
    """MongoDB collection names."""

    Expense = 'expense'
    PaymentSchedule = 'payment_schedule'
    Cash = 'cash'
    Report = 'report'
