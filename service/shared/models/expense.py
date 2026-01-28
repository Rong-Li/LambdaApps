"""Expense model definitions."""

from datetime import datetime

from pydantic import BaseModel, Field

from service.shared.models.enums import Category, TransactionType
from service.shared.models.types import PositiveAmount


class ExpenseInput(BaseModel):
    """Schema for creating a new expense (client input)."""

    amount: PositiveAmount
    category: Category
    transaction_type: TransactionType
    created_at: datetime = Field(..., description='Transaction timestamp')


class Expense(ExpenseInput):
    """Full expense model as stored in database."""

    id: str = Field(..., alias='_id')

    model_config = {'populate_by_name': True}


class ExpenseCreateResponse(BaseModel):
    """Response schema for expense creation."""

    message: str = 'Expense created successfully'
    expense_id: str
