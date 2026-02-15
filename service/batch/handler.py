"""Daily batch job Lambda handler.

Unified daily pipeline that runs 3 tasks in sequence:
1. Recurring payments — create expenses from due payment schedules
2. Daily aggregation — aggregate current month's transactions
3. Monthly re-aggregation — re-aggregate past 3 months (1st of month only)
"""

from datetime import date
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from service.batch.daily_aggregation import run_daily_aggregation
from service.batch.monthly_reaggregation import run_monthly_reaggregation
from service.batch.recurring_payments import run_recurring_payments

logger = Logger()
tracer = Tracer()


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Unified daily batch job handler."""
    logger.info('Starting daily batch pipeline')

    # Task 1: Recurring payments
    payments_result = run_recurring_payments()
    logger.info('Recurring payments complete', extra=payments_result)

    # Task 2: Daily aggregation
    aggregation_result = run_daily_aggregation()
    logger.info('Daily aggregation complete', extra=aggregation_result)

    # Task 3: Monthly re-aggregation (runs only on the 1st)
    if date.today().day == 15:
        reaggregation_result = run_monthly_reaggregation()
    else:
        reaggregation_result = {'skipped': True, 'reason': 'not_first_of_month'}
    logger.info('Monthly re-aggregation check complete', extra=reaggregation_result)

    logger.info('Daily batch pipeline complete')

    return {
        'statusCode': 200,
        'body': {
            'message': 'Daily batch pipeline completed',
            'recurring_payments': payments_result,
            'daily_aggregation': aggregation_result,
            'monthly_reaggregation': reaggregation_result,
        },
    }
