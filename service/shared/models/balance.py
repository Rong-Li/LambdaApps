"""Balance model definitions."""

from datetime import date, datetime, timezone

from pydantic import BaseModel, Field, field_validator


class BalanceInput(BaseModel):
    """Schema for creating a new balance record (client input)."""

    cad_balance: float
    rmb_balance: float
    record_time: datetime
    note: str | None = None

    @field_validator('record_time', mode='before')
    @classmethod
    def normalize_to_utc(cls, v: datetime | str) -> datetime:
        """Normalize timestamp to UTC. Convert if timezone-aware, assume UTC if naive."""
        if isinstance(v, str):
            v = datetime.fromisoformat(v)
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)


class Balance(BalanceInput):
    """Full balance model as stored in database."""

    id: str = Field(..., alias='_id')
    reconciled: bool = False
    cad_off_amount: float | None = None
    rmb_off_amount: float | None = None
    last_balance_date: date | None = None

    model_config = {'populate_by_name': True}


class BalanceResponse(BaseModel):
    """Response schema for balance creation and reconciliation."""

    message: str
    balance_id: str
    reconciled: bool
    cad_off_amount: float
    rmb_off_amount: float
