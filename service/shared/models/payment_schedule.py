"""Payment schedule model definitions."""

from datetime import date, datetime, timezone
from typing import Annotated, ClassVar

from pydantic import BaseModel, Field, field_validator, model_validator
from pymongo import DESCENDING, IndexModel

from service.shared.models.enums import Category, Currency, Frequency, TransactionType
from service.shared.models.types import PositiveAmount

# TTL: 6 months in seconds (180 * 24 * 60 * 60)
TTL_SIX_MONTHS = 15552000


class PaymentScheduleInput(BaseModel):
    """Schema for creating a new payment schedule (client input)."""

    name: str = Field(..., min_length=1, max_length=100, description='Schedule name')
    amount: PositiveAmount
    currency: Currency = Currency.CAD
    transaction_type: TransactionType = TransactionType.Debit
    category: Category
    merchant: str | None = None
    description: str | None = None
    frequency: Frequency
    monthly_dates: Annotated[list[int], Field(min_length=1)] | None = None
    start_date: datetime
    end_date: datetime | None = None

    @field_validator('monthly_dates', mode='before')
    @classmethod
    def validate_monthly_dates(cls, v: list[int] | None) -> list[int] | None:
        """Validate monthly_dates are between 1 and 28."""
        if v is None:
            return v
        for d in v:
            if not 1 <= d <= 28:
                raise ValueError('monthly_dates must be between 1 and 28')
        return sorted(set(v))

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def normalize_to_datetime(cls, v: datetime | date | str | None) -> datetime | None:
        """Normalize input to UTC datetime."""
        if v is None:
            return None
        if isinstance(v, str):
            # Try parsing date first, then datetime
            try:
                v = date.fromisoformat(v)
            except ValueError:
                v = datetime.fromisoformat(v)

        if isinstance(v, date) and not isinstance(v, datetime):
            v = datetime.combine(v, datetime.min.time(), tzinfo=timezone.utc)

        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            else:
                v = v.astimezone(timezone.utc)
        return v

    @model_validator(mode='after')
    def validate_monthly_dates_required(self) -> 'PaymentScheduleInput':
        """Validate that monthly_dates is provided when frequency is Monthly."""
        if self.frequency == Frequency.Monthly and not self.monthly_dates:
            raise ValueError('monthly_dates is required when frequency is Monthly')
        if self.frequency != Frequency.Monthly and self.monthly_dates:
            raise ValueError('monthly_dates should only be set when frequency is Monthly')
        return self

    @model_validator(mode='after')
    def validate_date_range(self) -> 'PaymentScheduleInput':
        """Validate end_date is after start_date."""
        if self.end_date and self.end_date < self.start_date:
            raise ValueError('end_date must be on or after start_date')
        return self


class PaymentSchedule(PaymentScheduleInput):
    """Full payment schedule model as stored in database."""

    id: str = Field(..., alias='_id')
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {'populate_by_name': True}

    indexes: ClassVar[list[IndexModel]] = [
        IndexModel([('end_date', DESCENDING)], expireAfterSeconds=TTL_SIX_MONTHS, name='end_date_ttl', sparse=True),
    ]


class PaymentScheduleCreateResponse(BaseModel):
    """Response schema for payment schedule creation."""

    message: str = 'Payment schedule created successfully'
    schedule_id: str
