"""Expense model definitions."""

from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, Field
from pymongo import DESCENDING, IndexModel

from service.shared.models.enums import Category, TransactionType
from service.shared.models.types import PositiveAmount

# TTL: 2 years in seconds (365 * 2 * 24 * 60 * 60)
TTL_TWO_YEARS = 63072000


class ExpenseInput(BaseModel):
    """Schema for creating a new expense (client input)."""

    amount: PositiveAmount
    category: Category
    transaction_type: TransactionType
    created_at: datetime = Field(..., description='Transaction timestamp')
    merchant: str | None = None
    description: str | None = None


class Expense(ExpenseInput):
    """Full expense model as stored in database."""

    id: str = Field(..., alias='_id')

    model_config = {'populate_by_name': True}

    indexes: ClassVar[list[IndexModel]] = [
        IndexModel([('created_at', DESCENDING)], expireAfterSeconds=TTL_TWO_YEARS, name='created_at_ttl'),
    ]


class ExpenseCreateResponse(BaseModel):
    """Response schema for expense creation."""

    message: str = 'Expense created successfully'
    expense_id: str
