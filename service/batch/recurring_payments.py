"""Recurring payments batch job Lambda handler.

This batch job runs daily at 5:00 AM UTC and creates expenses
from active payment schedules that are due.
"""

from datetime import date, datetime, timedelta, timezone

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from service.shared.database import get_database, mongo_get_payment_schedules, mongo_insert
from service.shared.models import ExpenseInput
from service.shared.models.enums import CollectionName, Frequency

logger = Logger()
tracer = Tracer()


def is_schedule_due(schedule: dict, today: date) -> bool:
    """Check if a payment schedule is due today.

    Args:
        schedule: Payment schedule document from MongoDB
        today: Today's date

    Returns:
        True if payment is due today, False otherwise
    """
    start_date = schedule['start_date']
    if isinstance(start_date, datetime):
        start_date = start_date.date()

    # If today is before start_date, not due
    if today < start_date:
        return False

    # If end_date exists and today is after end_date, not due
    end_date = schedule.get('end_date')
    if end_date:
        if isinstance(end_date, datetime):
            end_date = end_date.date()
        if today > end_date:
            return False

    frequency = Frequency(schedule['frequency'])

    if frequency == Frequency.Weekly:
        # Due every 7 days from start_date
        days_since_start = (today - start_date).days
        return days_since_start % 7 == 0

    elif frequency == Frequency.Biweekly:
        # Due every 14 days from start_date
        days_since_start = (today - start_date).days
        return days_since_start % 14 == 0

    elif frequency == Frequency.Monthly:
        # Due if today's day-of-month is in monthly_dates
        monthly_dates = schedule.get('monthly_dates', [])
        return today.day in monthly_dates

    return False


def create_expense_from_schedule(schedule: dict) -> ExpenseInput:
    """Create an expense document from a payment schedule.

    Args:
        schedule: Payment schedule document

    Returns:
        ExpenseInput object
    """
    now = datetime.now(timezone.utc)

    # Combine fields into description
    name = schedule.get('name', 'N/A')
    merchant = schedule.get('merchant', 'N/A')
    frequency = schedule.get('frequency', 'N/A')
    start_date = schedule.get('start_date')
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    end_date = schedule.get('end_date')
    if isinstance(end_date, datetime):
        end_date = end_date.date()
    desc = schedule.get('description', '')

    combined_desc = f"Schedule: {name} | Merchant: {merchant} | Freq: {frequency} | Start: {start_date}"
    if end_date:
        combined_desc += f" | End: {end_date}"
    if desc:
        combined_desc += f" | Note: {desc}"

    return ExpenseInput(
        amount=schedule['amount'],
        currency=schedule.get('currency', 'CAD'),
        category=schedule['category'],
        transaction_type=schedule.get('transaction_type', 'Debit'),
        created_at=now,
        merchant=schedule.get('merchant'),
        description=combined_desc,
        recurring_payment=True,
    )


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Recurring payments batch job handler.

    Runs daily to create expenses from active payment schedules that are due.
    """
    logger.info('Starting recurring payments batch job')

    today = date.today()
    logger.info(f'Processing schedules for date: {today}')

    # Step 1: Get all active payment schedules
    cursor = mongo_get_payment_schedules(
        CollectionName.PaymentSchedule,
    )
    schedules = list(cursor)
    logger.info(f'Found {len(schedules)} active payment schedules')

    # Step 2: Filter schedules that are due today
    due_schedules = [s for s in schedules if is_schedule_due(s, today)]
    logger.info(f'Found {len(due_schedules)} schedules due today')

    # Step 3: Create expenses for each due schedule
    expenses_created = 0
    errors = []

    for schedule in due_schedules:
        try:
            expense = create_expense_from_schedule(schedule)
            mongo_insert(expense.model_dump(), CollectionName.Expense)
            expenses_created += 1
            logger.info(
                f'Created expense from schedule',
                extra={
                    'schedule_id': str(schedule['_id']),
                    'schedule_name': schedule.get('name'),
                    'amount': schedule['amount'],
                },
            )
        except Exception as e:
            error_msg = f"Failed to create expense for schedule {schedule['_id']}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    logger.info(
        f'Recurring payments batch job completed',
        extra={
            'date': str(today),
            'schedules_checked': len(schedules),
            'schedules_due': len(due_schedules),
            'expenses_created': expenses_created,
            'errors': len(errors),
        },
    )

    return {
        'statusCode': 200,
        'body': {
            'message': 'Recurring payments batch job completed',
            'date': str(today),
            'schedules_checked': len(schedules),
            'schedules_due': len(due_schedules),
            'expenses_created': expenses_created,
            'errors': errors,
        },
    }
