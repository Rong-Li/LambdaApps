"""MongoDB database connection manager."""

from datetime import datetime
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
from service.shared.models.enums import Category, CollectionName, TransactionType
from service.shared.models.expense import Expense

logger = Logger()

# Map collection names to their index definitions
COLLECTION_INDEXES = {
    CollectionName.Expense: Expense.indexes,
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
    ensure_indexes_flag: bool = False,
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

    indexes = COLLECTION_INDEXES.get(collection_name)
    if ensure_indexes_flag and indexes:
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
