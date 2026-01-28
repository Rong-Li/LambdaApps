"""Report model definitions."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class Report(BaseModel):
    """Monthly aggregated report."""

    month: str = Field(..., pattern=r'^\d{4}-\d{2}$', description='YYYY-MM format')
    total_expense: float = Field(..., ge=0)
    total_earning: float = Field(..., ge=0)
    expense_by_category: dict[str, float]

    @computed_field
    @property
    def net(self) -> float:
        """Calculate net (earning - expense)."""
        return self.total_earning - self.total_expense


class ReportExpenseResponse(BaseModel):
    """Response schema for report expense endpoint."""

    start_date: date
    end_date: date
    category_filter: Optional[str] = None
    reports: list[Report]
    message: Optional[str] = None
