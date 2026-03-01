"""Cash collection queries."""

from datetime import date, datetime

from aws_lambda_powertools import Logger
from pymongo.cursor import Cursor

from service.shared.models.enums import CollectionName, TransactionType
from service.shared.utils.mongo.connection import get_database
from service.shared.utils.mongo.operations import mongo_insert

logger = Logger()


def mongo_get_cash_balance() -> dict:
    """Get the cash balance document, or create one if it doesn't exist."""
    db = get_database()
    collection = db[CollectionName.Cash]
    balance_doc = collection.find_one({'record_type': 'balance'})
    if not balance_doc:
        balance_doc = {
            'record_type': 'balance',
            'balance': 0.0,
            'last_updated_date': datetime.combine(date.today(), datetime.min.time()),
        }
        mongo_insert(balance_doc, CollectionName.Cash)
    return balance_doc


def mongo_get_cash_transactions(limit: int = 50) -> Cursor:
    """Get the most recent cash transactions."""
    db = get_database()
    collection = db[CollectionName.Cash]
    return collection.find({'record_type': 'transaction'}).sort('timestamp', -1).limit(limit)


def mongo_update_cash_balance_and_add_transaction(
    amount: float,
    transaction_type: TransactionType,
    timestamp: datetime,
) -> None:
    """Update balance and add a transaction document."""
    db = get_database()
    collection = db[CollectionName.Cash]

    # 1. Update balance
    change = amount if transaction_type == TransactionType.Credit else -amount
    collection.update_one(
        {'record_type': 'balance'},
        {
            '$inc': {'balance': change},
            '$set': {'last_updated_date': datetime.combine(date.today(), datetime.min.time())},
        },
        upsert=True,
    )

    # 2. Add transaction
    transaction_doc = {
        'record_type': 'transaction',
        'amount': amount,
        'type': transaction_type.value,
        'timestamp': timestamp,
    }
    mongo_insert(transaction_doc, CollectionName.Cash)


def mongo_reset_cash() -> None:
    """Delete all transactions and reset balance to 0."""
    db = get_database()
    collection = db[CollectionName.Cash]

    # Delete all transactions
    collection.delete_many({'record_type': 'transaction'})

    # Reset balance
    collection.update_one(
        {'record_type': 'balance'},
        {
            '$set': {
                'balance': 0.0,
                'last_updated_date': datetime.combine(date.today(), datetime.min.time()),
            },
        },
        upsert=True,
    )
