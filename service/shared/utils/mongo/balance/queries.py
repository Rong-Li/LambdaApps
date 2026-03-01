"""Balance collection queries."""

from datetime import date, datetime, timedelta

from aws_lambda_powertools import Logger
from pymongo.cursor import Cursor

from service.shared.models.enums import CollectionName
from service.shared.utils.mongo.connection import get_database
from service.shared.utils.mongo.expense.queries import mongo_get_expenses
from service.shared.utils.mongo.operations import _parse_id

logger = Logger()

# Reconciliation tolerance: 2% of calculated balance
RECONCILIATION_THRESHOLD = 0.02


def mongo_get_balances() -> Cursor:
    """Get all balance records sorted by record_time descending."""
    db = get_database()
    collection = db[CollectionName.Balance]
    return collection.find({}).sort('record_time', -1)


def mongo_get_previous_balance(record_time: datetime) -> dict | None:
    """Find the most recent balance whose record_time is strictly before *record_time*."""
    db = get_database()
    collection = db[CollectionName.Balance]
    return collection.find_one(
        {'record_time': {'$lt': record_time}},
        sort=[('record_time', -1)],
    )


def mongo_update_balance_reconciled(
    balance_id: str,
    reconciled: bool,
    cad_off: float,
    rmb_off: float,
    last_balance_date: date | None = None,
) -> None:
    """Set reconciled, cad_off_amount, rmb_off_amount, and last_balance_date on a balance document."""
    doc_id = _parse_id(balance_id)
    db = get_database()
    collection = db[CollectionName.Balance]
    update_fields: dict = {
        'reconciled': reconciled,
        'cad_off_amount': cad_off,
        'rmb_off_amount': rmb_off,
    }
    if last_balance_date is not None:
        update_fields['last_balance_date'] = datetime.combine(last_balance_date, datetime.min.time())
    collection.update_one(
        {'_id': doc_id},
        {'$set': update_fields},
    )
    logger.info(
        'Updated balance reconciliation',
        extra={'balance_id': balance_id, 'reconciled': reconciled},
    )


def mongo_reconcile_balance(balance_doc: dict) -> tuple[bool, float, float]:
    """Reconcile a balance against expense transactions.

    Compares the balance's cad_balance/rmb_balance against the sum of
    credit/debit transactions in the expense collection since the previous
    balance record.

    Returns:
        (reconciled, cad_off_amount, rmb_off_amount)
    """
    record_time = balance_doc['record_time']
    cad_balance = balance_doc['cad_balance']
    rmb_balance = balance_doc['rmb_balance']
    balance_id = str(balance_doc['_id'])

    previous = mongo_get_previous_balance(record_time)

    # No previous balance → skip reconciliation
    if previous is None:
        mongo_update_balance_reconciled(balance_id, False, cad_balance, rmb_balance)
        return (False, cad_balance, rmb_balance)

    prev_time = previous['record_time']

    if record_time - prev_time > timedelta(days=365):
        # More than a year gap – treat as no previous
        mongo_update_balance_reconciled(balance_id, False, cad_balance, rmb_balance)
        return (False, cad_balance, rmb_balance)

    # Query expenses between previous record_time and this record_time
    cursor = mongo_get_expenses(
        CollectionName.Expense,
        start_date=prev_time,
        end_date=record_time,
    )

    # Accumulate credits and debits by currency
    cad_credits = 0.0
    cad_debits = 0.0
    rmb_credits = 0.0
    rmb_debits = 0.0

    for doc in cursor:
        amount = doc.get('amount')
        currency = doc.get('currency')
        txn_type = doc.get('transaction_type')

        if currency == 'CAD':
            if txn_type == 'Credit':
                cad_credits += amount
            else:
                cad_debits += amount
        elif currency == 'RMB':
            if txn_type == 'Credit':
                rmb_credits += amount
            else:
                rmb_debits += amount

    prev_cad = previous.get('cad_balance', 0.0)
    prev_rmb = previous.get('rmb_balance', 0.0)

    cad_calculated_balance = prev_cad + cad_credits - cad_debits
    rmb_calculated_balance = prev_rmb + rmb_credits - rmb_debits

    cad_off = round(cad_balance - cad_calculated_balance, 2)
    rmb_off = round(rmb_balance - rmb_calculated_balance, 2)

    # Check 2% threshold on CAD only
    denominator = max(abs(cad_calculated_balance), 1.0)
    reconciled = abs(cad_off) / denominator <= RECONCILIATION_THRESHOLD

    mongo_update_balance_reconciled(balance_id, reconciled, cad_off, rmb_off, last_balance_date=prev_time)
    return (reconciled, cad_off, rmb_off)
