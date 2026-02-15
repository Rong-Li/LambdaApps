"""Report model definitions."""

from typing import Optional

from pydantic import BaseModel, Field


class Report(BaseModel):
    """Monthly aggregated report stored in the reports collection."""

    # Report month in YYYY-MM format
    month: str = Field(..., pattern=r'^\d{4}-\d{2}$', description='Report month in YYYY-MM format')

    # Sum of ALL debit transactions across all categories
    total_debit: float = Field(default=0.0, ge=0)
    # Sum of ALL credit transactions (includes earnings + refunds)
    total_credit: float = Field(default=0.0, ge=0)

    # Debits from expense categories only (CategoryExpense)
    expense_debit: float = Field(default=0.0, ge=0)
    # Credits/refunds from expense categories only (CategoryExpense)
    expense_credit: float = Field(default=0.0, ge=0)

    # Debits from earning categories only (CategoryEarning)
    earning_debit: float = Field(default=0.0, ge=0)
    # Credits from earning categories, e.g. salary (CategoryEarning)
    earning_credit: float = Field(default=0.0, ge=0)

    # Debit amount broken down by each category
    debit_by_category: dict[str, float] = Field(default_factory=dict)
    # Credit amount broken down by each category
    credit_by_category: dict[str, float] = Field(default_factory=dict)
    # Number of transactions per category
    count_by_category: dict[str, int] = Field(default_factory=dict)


class TrendMonthEntry(BaseModel):
    """Single month entry in the spending trend."""

    month: str
    net_expense: float


class CurrentMonthSummary(BaseModel):
    """Current (in-progress) month summary."""

    month: str
    net_expense: float
    days_remaining: int


class TrendResponse(BaseModel):
    """Response for GET /report/trend endpoint."""

    months_requested: int
    category_filter: Optional[str] = None
    current_month: CurrentMonthSummary
    previous_month_earning: float
    trend: list[TrendMonthEntry]


class CategorySnapshot(BaseModel):
    """Category breakdown for a time range snapshot."""

    net_expense: float
    net_by_category: dict[str, float]
    count_by_category: dict[str, int]


class CategorySnapshotMonth(CategorySnapshot):
    """Category snapshot with month label."""

    month: str


class CategorySnapshotYear(CategorySnapshot):
    """Category snapshot with year label."""

    year: str


class CategoryBreakdownResponse(BaseModel):
    """Response for GET /report/category-breakdown endpoint."""

    last_month: Optional[CategorySnapshotMonth] = None
    current_year: Optional[CategorySnapshotYear] = None
    last_year: Optional[CategorySnapshotYear] = None
