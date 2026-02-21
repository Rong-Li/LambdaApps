"""Balance model definitions."""

from datetime import date

from pydantic import BaseModel, Field


class BalanceInput(BaseModel):
    """Schema for creating a new balance record (client input)."""

    cad_balance: float
    rmb_balance: float
    record_date: date
    note: str | None = None


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
