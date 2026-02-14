"""Cash model definitions."""

from datetime import date, datetime, timezone
from typing import ClassVar

from pydantic import BaseModel, Field, field_validator
from pymongo import DESCENDING, IndexModel

from service.shared.models.enums import TransactionType
from service.shared.models.types import PositiveAmount

# TTL: 3 months in seconds (90 days * 24 * 60 * 60)
TTL_THREE_MONTHS = 7776000


class CashTransaction(BaseModel):
    """Model for individual cash transactions."""

    record_type: str = Field(default='transaction', frozen=True)
    amount: PositiveAmount
    type: TransactionType
    timestamp: datetime = Field(..., description='Transaction timestamp')

    @field_validator('timestamp', mode='before')
    @classmethod
    def normalize_to_utc(cls, v: datetime | str) -> datetime:
        """Normalize timestamp to UTC. Convert if timezone-aware, assume UTC if naive."""
        if isinstance(v, str):
            v = datetime.fromisoformat(v)
        if v.tzinfo is None:
            # Naive datetime: assume UTC
            return v.replace(tzinfo=timezone.utc)
        # Timezone-aware: convert to UTC
        return v.astimezone(timezone.utc)

    indexes: ClassVar[list[IndexModel]] = [
        IndexModel([('timestamp', DESCENDING)], expireAfterSeconds=TTL_THREE_MONTHS, name='timestamp_ttl'),
    ]


class CashBalance(BaseModel):
    """Model for the current balance."""

    record_type: str = Field(default='balance', frozen=True)
    balance: float = 0.0
    last_updated_date: date = Field(default_factory=date.today)


class CashResponse(BaseModel):
    """Response schema for GET /cash endpoint."""

    balance: CashBalance
    transactions: list[CashTransaction]
