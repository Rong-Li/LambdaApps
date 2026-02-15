"""Daily aggregation batch task.

Aggregates the current month's transactions into the Report model
and upserts the result into the reports collection.
"""

from collections import defaultdict
from datetime import date, datetime

from aws_lambda_powertools import Logger

from service.shared.database import get_database, mongo_get_expenses
from service.shared.models.enums import CategoryEarning, CategoryExpense, CollectionName
from service.shared.models.report import Report

logger = Logger()




def _aggregate(expenses: list[dict], month: str) -> Report:
    """Aggregate a list of expense documents into a Report object."""
    total_debit = 0.0
    total_credit = 0.0
    expense_debit = 0.0
    expense_credit = 0.0
    earning_debit = 0.0
    earning_credit = 0.0
    debit_by_category: dict[str, float] = defaultdict(float)
    credit_by_category: dict[str, float] = defaultdict(float)
    count_by_category: dict[str, int] = defaultdict(int)

    for expense in expenses:
        amount = float(expense['amount'])
        category = expense.get('category')
        txn_type = expense.get('transaction_type')

        if txn_type == 'Debit':
            total_debit += amount
            if category:
                debit_by_category[category] += amount
                count_by_category[category] += 1
                if category in CategoryExpense.values():
                    expense_debit += amount
                elif category in CategoryEarning.values():
                    earning_debit += amount
        elif txn_type == 'Credit':
            total_credit += amount
            if category:
                credit_by_category[category] += amount
                count_by_category[category] += 1
                if category in CategoryExpense.values():
                    expense_credit += amount
                elif category in CategoryEarning.values():
                    earning_credit += amount

    return Report(
        month=month,
        total_debit=total_debit,
        total_credit=total_credit,
        expense_debit=expense_debit,
        expense_credit=expense_credit,
        earning_debit=earning_debit,
        earning_credit=earning_credit,
        debit_by_category=dict(debit_by_category),
        credit_by_category=dict(credit_by_category),
        count_by_category=dict(count_by_category),
    )


def _upsert_report(db, report: Report) -> None:
    """Upsert a monthly report document."""
    report_dict = report.model_dump()
    month = report_dict.pop('month')
    db.reports.update_one(
        {'month': month},
        {
            '$set': {
                'month': month,
                **report_dict,
                'updated_at': datetime.utcnow(),
            },
            '$setOnInsert': {'created_at': datetime.utcnow()},
        },
        upsert=True,
    )


def run_daily_aggregation() -> dict:
    """Aggregate the current month's transactions and upsert the report.

    Skips if no transactions are found for the current month.

    Returns:
        Summary dict with month and expenses_processed count.
    """
    today = date.today()
    first_of_month = today.replace(day=1)
    month_str = today.strftime('%Y-%m')

    logger.info(f'Daily aggregation: processing month {month_str}')

    db = get_database()
    expenses = list(mongo_get_expenses(
        CollectionName.Expense,
        start_date=datetime.combine(first_of_month, datetime.min.time()),
        end_date=datetime.combine(today, datetime.max.time()),
    ))

    if not expenses:
        logger.info(f'No transactions found for {month_str}, skipping')
        return {'month': month_str, 'expenses_processed': 0, 'skipped': True}

    aggregated = _aggregate(expenses, month_str)
    _upsert_report(db, aggregated)

    logger.info(f'Daily aggregation complete for {month_str}: {len(expenses)} expenses')
    return {'month': month_str, 'expenses_processed': len(expenses), 'skipped': False}
