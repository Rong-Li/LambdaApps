"""Enum definitions for homeapp service."""

from enum import Enum


class Category(str, Enum):
    """Expense category enum."""

    Groceries = 'Groceries'
    EatOut = 'EatOut'
    Transportation = 'Transportation'
    Mortgage = 'Mortgage'
    Utilities = 'Utilities'
    Shopping = 'Shopping'
    Gas = 'Gas'
    Insurance = 'Insurance'


class TransactionType(str, Enum):
    """Transaction type enum."""

    Credit = 'Credit'  # Income / Earning
    Debit = 'Debit'  # Expense / Spending


class Currency(str, Enum):
    """Currency enum."""

    CAD = 'CAD'
    RMB = 'RMB'


class CollectionName(str, Enum):
    """MongoDB collection names."""

    Expense = 'expense'
