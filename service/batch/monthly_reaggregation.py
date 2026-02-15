"""Monthly re-aggregation batch task.

Runs on the 1st of each month to re-aggregate the past 3 months
of transactions, correcting any mid-month edits.
"""

from datetime import date, datetime, timedelta

from aws_lambda_powertools import Logger

from service.shared.database import get_database, mongo_get_expenses
from service.shared.models.enums import CollectionName
from service.batch.daily_aggregation import _aggregate, _upsert_report
from service.shared.utils.date_utils import get_month_lookback_start, get_month_range

logger = Logger()


def _get_past_months(num_months: int) -> list[tuple[date, date]]:
    """Get the first and last day for each of the past N months.

    Args:
        num_months: Number of past months to include.

    Returns:
        List of (first_day, last_day) tuples, one per month.
    """
    today = date.today()
    months = []

    for i in range(1, num_months + 1):
        # Walk back i months from the first of the current month
        ref = get_month_lookback_start(today, i)
        months.append(get_month_range(ref))

    return months


def run_monthly_reaggregation() -> dict:
    """Re-aggregate the past 3 months.

    Returns:
        Summary dict with months re-aggregated.
    """
    logger.info('Monthly re-aggregation: processing past 3 months')

    db = get_database()
    results = []

    for first_day, last_day in _get_past_months(3):
        month_str = first_day.strftime('%Y-%m')
        expenses = list(mongo_get_expenses(
            CollectionName.Expense,
            start_date=datetime.combine(first_day, datetime.min.time()),
            end_date=datetime.combine(last_day, datetime.max.time()),
        ))

        if not expenses:
            logger.info(f'No transactions for {month_str}, skipping')
            results.append({'month': month_str, 'expenses_processed': 0})
            continue

        aggregated = _aggregate(expenses, month_str)
        _upsert_report(db, aggregated)

        logger.info(f'Re-aggregated {month_str}: {len(expenses)} expenses')
        results.append({'month': month_str, 'expenses_processed': len(expenses)})

    return {'skipped': False, 'months': results}
