"""MongoDB database connection manager."""

from datetime import date, datetime
from functools import lru_cache

from aws_lambda_powertools import Logger
from bson.errors import InvalidId
from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.database import Database
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from service.shared.config import get_mongo_settings
from service.shared.models.enums import Category, CollectionName, Currency, TransactionType
from service.shared.models.expense import Expense
from service.shared.models.payment_schedule import PaymentSchedule
from service.shared.models.cash import CashTransaction

logger = Logger()

# Map collection names to their index definitions
COLLECTION_INDEXES = {
    CollectionName.Expense: Expense.indexes,
    CollectionName.PaymentSchedule: PaymentSchedule.indexes,
    CollectionName.Cash: CashTransaction.indexes,
}


@lru_cache
def get_client() -> MongoClient:
    """Get cached MongoDB client instance."""
    settings = get_mongo_settings()
    return MongoClient(settings.mongo_uri)


def get_database() -> Database:
    """Get MongoDB database instance."""
    settings = get_mongo_settings()
    client = get_client()
    return client[settings.database]


def ensure_indexes(collection: Collection, indexes: list) -> None:
    """Ensure indexes exist for a collection by checking MongoDB.

    Args:
        collection: PyMongo collection instance
        indexes: List of IndexModel definitions to ensure
    """
    # Get existing index names from MongoDB
    existing_indexes = {idx['name'] for idx in collection.list_indexes()}

    # Filter to only indexes that don't exist yet
    missing_indexes = [idx for idx in indexes if idx.document['name'] not in existing_indexes]

    if missing_indexes:
        collection.create_indexes(missing_indexes)
        logger.info(f'Created indexes for {collection.name}', extra={'indexes': [idx.document['name'] for idx in missing_indexes]})


def mongo_insert(
    document: dict,
    collection_name: CollectionName,
) -> InsertOneResult:
    """Insert a document into a MongoDB collection and log the result.

    Args:
        document: Dict to insert (should be validated before calling)
        collection_name: Name of the collection
        ensure_indexes_flag: If True, ensure indexes exist before insert (default: True)

    Returns:
        InsertOneResult from MongoDB
    """
    db = get_database()
    collection = db[collection_name]

    settings = get_mongo_settings()
    indexes = COLLECTION_INDEXES.get(collection_name)
    if settings.check_create_index and indexes:
        ensure_indexes(collection, indexes)

    result = collection.insert_one(document)

    if result.acknowledged:
        logger.info(f'Successfully inserted 1 record into {collection_name}', extra={'inserted_id': str(result.inserted_id)})
    else:
        logger.warning(f'Insert not acknowledged for {collection_name}')

    return result


def mongo_get_expenses(
    collection_name: CollectionName,
    start_date: datetime,
    end_date: datetime,
    category: Category | None = None,
    transaction_type: TransactionType | None = None,
    currency: Currency | None = None,
    has_receipt: bool | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
) -> Cursor:
    """Get expenses in a date range with optional filters.

    Args:
        collection_name: Name of the collection
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)
        category: Optional category filter (None = all)
        transaction_type: Optional Credit or Debit (None = all)
        has_receipt: If True, only expenses with receipt_id; if False, only without (None = all)
        min_amount: Minimum amount filter (inclusive, None = no min)
        max_amount: Maximum amount filter (inclusive, None = no max)

    Returns:
        Cursor over matching documents
    """
    query: dict = {'created_at': {'$gte': start_date, '$lte': end_date}}
    if category is not None:
        query['category'] = category
    if transaction_type is not None:
        query['transaction_type'] = transaction_type.value
    if currency is not None:
        query['currency'] = currency.value
    if has_receipt is True:
        query['receipt_id'] = {'$exists': True, '$ne': None}
    elif has_receipt is False:
        query['$or'] = [{'receipt_id': {'$exists': False}}, {'receipt_id': None}]
    if min_amount is not None or max_amount is not None:
        query['amount'] = {}
        if min_amount is not None:
            query['amount']['$gte'] = min_amount
        if max_amount is not None:
            query['amount']['$lte'] = max_amount

    db = get_database()
    collection = db[collection_name]
    return collection.find(query).sort('created_at', -1)


def _parse_expense_id(expense_id: str):
    """Convert expense_id string to ObjectId if valid 24-char hex, else return as-is."""
    if len(expense_id) == 24:
        try:
            return ObjectId(expense_id)
        except InvalidId:
            pass
    return expense_id


def mongo_update_expense(
    collection_name: CollectionName,
    expense_id: str,
    update_doc: dict,
) -> UpdateResult | None:
    """Update a single expense by id.

    Only the fields in update_doc are set; other fields (e.g. receipt_id) are
    left unchanged.

    Args:
        collection_name: Name of the collection
        expense_id: Expense document id (ObjectId string or string id)
        update_doc: Document fields to set (validated dict, no _id)

    Returns:
        UpdateResult if a document was matched and updated, None if not found
    """
    doc_id = _parse_expense_id(expense_id)
    # Never update receipt_id; leave it unchanged on the document
    update_doc = {k: v for k, v in update_doc.items() if k != 'receipt_id'}
    db = get_database()
    collection = db[collection_name]
    result = collection.update_one(
        {'_id': doc_id},
        {'$set': update_doc},
    )
    if result.matched_count == 0:
        return None
    logger.info(
        f'Updated expense in {collection_name}',
        extra={'expense_id': expense_id},
    )
    return result


def mongo_delete_expense(
    collection_name: CollectionName,
    expense_id: str,
) -> DeleteResult | None:
    """Delete a single expense by id.

    Args:
        collection_name: Name of the collection
        expense_id: Expense document id (ObjectId string or string id)

    Returns:
        DeleteResult if a document was deleted, None if not found
    """
    doc_id = _parse_expense_id(expense_id)
    db = get_database()
    collection = db[collection_name]
    result = collection.delete_one({'_id': doc_id})
    if result.deleted_count == 0:
        return None
    logger.info(
        f'Deleted expense from {collection_name}',
        extra={'expense_id': expense_id},
    )
    return result


def mongo_get_payment_schedules(
    collection_name: CollectionName,
) -> Cursor:
    """Get all payment schedules.

    Args:
        collection_name: Name of the collection

    Returns:
        Cursor over matching documents, sorted by created_at (newest first)
    """
    db = get_database()
    collection = db[collection_name]
    return collection.find({}).sort('created_at', -1)


def mongo_get_payment_schedule_by_id(
    collection_name: CollectionName,
    schedule_id: str,
) -> dict | None:
    """Get a single payment schedule by id.

    Args:
        collection_name: Name of the collection
        schedule_id: Schedule document id

    Returns:
        Document dict if found, None otherwise
    """
    doc_id = _parse_expense_id(schedule_id)
    db = get_database()
    collection = db[collection_name]
    return collection.find_one({'_id': doc_id})


def mongo_update_payment_schedule(
    collection_name: CollectionName,
    schedule_id: str,
    update_doc: dict,
) -> UpdateResult | None:
    """Update a single payment schedule by id.

    Args:
        collection_name: Name of the collection
        schedule_id: Schedule document id
        update_doc: Document fields to set

    Returns:
        UpdateResult if matched, None if not found
    """
    doc_id = _parse_expense_id(schedule_id)
    db = get_database()
    collection = db[collection_name]
    result = collection.update_one(
        {'_id': doc_id},
        {'$set': update_doc},
    )
    if result.matched_count == 0:
        return None
    logger.info(
        f'Updated payment schedule in {collection_name}',
        extra={'schedule_id': schedule_id},
    )
    return result


def mongo_delete_payment_schedule(
    collection_name: CollectionName,
    schedule_id: str,
) -> DeleteResult | None:
    """Delete a single payment schedule by id.

    Args:
        collection_name: Name of the collection
        schedule_id: Schedule document id

    Returns:
        DeleteResult if deleted, None if not found
    """
    doc_id = _parse_expense_id(schedule_id)
    db = get_database()
    collection = db[collection_name]
    result = collection.delete_one({'_id': doc_id})
    if result.deleted_count == 0:
        return None
    logger.info(
        f'Deleted payment schedule from {collection_name}',
        extra={'schedule_id': schedule_id},
    )
    return result


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


# ---------------------------------------------------------------------------
# Balance helpers
# ---------------------------------------------------------------------------

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


def mongo_delete_balance(balance_id: str) -> DeleteResult | None:
    """Delete a single balance by id.

    Returns:
        DeleteResult if a document was deleted, None if not found
    """
    doc_id = _parse_expense_id(balance_id)
    db = get_database()
    collection = db[CollectionName.Balance]
    result = collection.delete_one({'_id': doc_id})
    if result.deleted_count == 0:
        return None
    logger.info('Deleted balance', extra={'balance_id': balance_id})
    return result


def mongo_update_balance_reconciled(
    balance_id: str,
    reconciled: bool,
    cad_off: float,
    rmb_off: float,
    last_balance_date: date | None = None,
) -> None:
    """Set reconciled, cad_off_amount, rmb_off_amount, and last_balance_date on a balance document."""
    doc_id = _parse_expense_id(balance_id)
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
    from datetime import timedelta

    record_time = balance_doc['record_time']

    cad_balance = balance_doc['cad_balance']
    rmb_balance = balance_doc['rmb_balance']
    balance_id = str(balance_doc['_id'])

    previous = mongo_get_previous_balance(record_time)

    # No previous balance or previous is more than 1 year old → skip recon
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

