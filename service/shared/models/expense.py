"""Expense model definitions."""

from datetime import date, datetime, time
from typing import Annotated, ClassVar

from pydantic import BaseModel, Field, field_validator, model_validator
from pymongo import DESCENDING, IndexModel

from service.shared.models.enums import Category, Currency, TransactionType
from service.shared.models.types import PositiveAmount

# TTL: 2 years in seconds (365 * 2 * 24 * 60 * 60)
TTL_TWO_YEARS = 63072000


class GetExpenseParams(BaseModel):
    """Query parameters for GET /expense endpoint."""

    start_date: date
    end_date: date
    category: Category | None = None
    transaction_type: TransactionType | None = None
    currency: Currency | None = None
    has_receipt: bool | None = None
    min_amount: Annotated[float, Field(ge=0)] | None = None
    max_amount: Annotated[float, Field(ge=0)] | None = None

    @field_validator('has_receipt', mode='before')
    @classmethod
    def parse_bool(cls, v: str | bool | None) -> bool | None:
        """Parse boolean from string query param."""
        if v is None or isinstance(v, bool):
            return v
        if v.lower() == 'true':
            return True
        if v.lower() == 'false':
            return False
        raise ValueError('must be true or false')

    @model_validator(mode='after')
    def validate_ranges(self) -> 'GetExpenseParams':
        """Validate date and amount ranges."""
        if self.end_date < self.start_date:
            raise ValueError('end_date must be on or after start_date')
        if self.min_amount is not None and self.max_amount is not None:
            if self.min_amount > self.max_amount:
                raise ValueError('min_amount cannot be greater than max_amount')
        return self

    @property
    def start_datetime(self) -> datetime:
        """Get start_date as datetime at start of day."""
        return datetime.combine(self.start_date, time.min)

    @property
    def end_datetime(self) -> datetime:
        """Get end_date as datetime at end of day."""
        return datetime.combine(self.end_date, time.max)


class ExpenseInput(BaseModel):
    """Schema for creating a new expense (client input)."""

    amount: PositiveAmount
    currency: Currency = Currency.CAD
    category: Category
    transaction_type: TransactionType
    created_at: datetime = Field(..., description='Transaction timestamp')
    merchant: str | None = None
    description: str | None = None
    postal_code: str | None = None
    recurring_payment: bool = False


class Expense(ExpenseInput):
    """Full expense model as stored in database."""

    id: str = Field(..., alias='_id')
    receipt_id: str | None = None

    model_config = {'populate_by_name': True}

    indexes: ClassVar[list[IndexModel]] = [
        IndexModel([('created_at', DESCENDING)], expireAfterSeconds=TTL_TWO_YEARS, name='created_at_ttl'),
    ]


class ExpenseCreateResponse(BaseModel):
    """Response schema for expense creation."""

    message: str = 'Expense created successfully'
    expense_id: str
