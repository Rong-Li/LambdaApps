"""Enum definitions for homeapp service."""

from enum import Enum


class CategoryExpense(str, Enum):
    """Expense-specific categories (spending)."""
    Groceries = 'Groceries'
    DineOut = 'Dine Out'
    Shopping = 'Shopping' # Clothing, Skincare, shoppers
    Car = 'Car' # Gas, car maintenance, insurance
    Entertainment = 'Entertainment' # Sport, Entertainment, membership (apple, spotify)
    Medical = 'Medical' # Medicine, Massage, Dental
    Transportation = 'Transportation' # public transit.
    PersonalImprovement = 'Personal Improvement' # Study, Lessons, Certification
    Housing = 'Housing' # Mortgage, Condo Maintainese, Property Tax, Insurance
    HomeImprovement = 'Home Improvement'
    Utilities = 'Utilities' # Internet, Phone bill
    Gift = 'Gift' # Friends, Parent
    Travel = 'Travel' # Plane Ticket, Hotel, etc.
    Pet = 'Pet'
    Miscellaneous = 'Miscellaneous' # Haircut, others
    Investment = 'Investment'

    @classmethod
    def values(cls) -> set[str]:
        """Set of all expense category values."""
        return {c.value for c in cls}


class CategoryEarning(str, Enum):
    """Earning-specific categories (income)."""

    Salary = 'Salary'
    TaxReturn = 'Tax Return'
    CashBack = 'Cash Back' # Credit Card, Rakuten

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
    Balance = 'balance'
