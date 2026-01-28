"""Monthly batch job Lambda handler."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from pymongo.database import Database

from service.shared.database import get_database
from service.utils.s3_utils import export_transactions_to_s3

logger = Logger()
tracer = Tracer()


def get_previous_month() -> tuple[date, date]:
    """Get first and last day of previous month."""
    today = date.today()
    first_of_current = today.replace(day=1)
    last_of_previous = first_of_current - timedelta(days=1)
    first_of_previous = last_of_previous.replace(day=1)
    return first_of_previous, last_of_previous


def fetch_monthly_expenses(db: Database, start_date: date, end_date: date) -> list[dict]:
    """Fetch all expenses for the given date range."""
    return list(
        db.expenses.find(
            {
                'created_at': {
                    '$gte': datetime.combine(start_date, datetime.min.time()),
                    '$lte': datetime.combine(end_date, datetime.max.time()),
                }
            }
        )
    )


def aggregate_expenses(expenses: list[dict]) -> dict:
    """Aggregate expenses into monthly summary."""
    total_expense = Decimal('0')
    total_earning = Decimal('0')
    expense_by_category: dict[str, Decimal] = defaultdict(Decimal)

    for expense in expenses:
        amount = Decimal(str(expense['amount']))

        if expense['transaction_type'] == 'Debit':
            total_expense += amount
            if expense.get('category'):
                expense_by_category[expense['category']] += amount
        else:  # Credit
            total_earning += amount

    return {
        'total_expense': float(total_expense),
        'total_earning': float(total_earning),
        'expense_by_category': {k: float(v) for k, v in expense_by_category.items()},
    }


def upsert_report(db: Database, month: str, aggregated_data: dict) -> None:
    """Upsert monthly report to MongoDB."""
    db.reports.update_one(
        {'month': month},
        {
            '$set': {
                'month': month,
                'total_expense': aggregated_data['total_expense'],
                'total_earning': aggregated_data['total_earning'],
                'expense_by_category': aggregated_data['expense_by_category'],
                'updated_at': datetime.utcnow(),
            },
            '$setOnInsert': {'created_at': datetime.utcnow()},
        },
        upsert=True,
    )


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Monthly batch job handler."""
    logger.info('Starting monthly batch job')

    # Step 1: Get target month
    start_date, end_date = get_previous_month()
    month_str = start_date.strftime('%Y-%m')

    logger.info(f'Processing month: {month_str}')

    # Step 2: Fetch transactions
    db = get_database()
    expenses = fetch_monthly_expenses(db, start_date, end_date)

    logger.info(f'Found {len(expenses)} expenses')

    # Step 3: Aggregate
    aggregated = aggregate_expenses(expenses)

    # Step 4: Upsert report
    upsert_report(db, month_str, aggregated)

    logger.info(f'Report upserted for {month_str}')

    # Step 5: Export to S3
    export_transactions_to_s3(
        expenses=expenses,
        investments=[],  # Future
        year=start_date.strftime('%Y'),
        month=start_date.strftime('%m'),
    )

    logger.info(f'S3 export complete: transactions/{start_date.strftime("%Y")}/{month_str}.parquet')

    return {
        'statusCode': 200,
        'body': {
            'message': 'Batch job completed successfully',
            'month': month_str,
            'expenses_processed': len(expenses),
            'total_expense': aggregated['total_expense'],
            'total_earning': aggregated['total_earning'],
        },
    }
