"""MongoDB database connection manager."""

from datetime import datetime
from functools import lru_cache

from aws_lambda_powertools import Logger
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.database import Database
from pymongo.results import InsertOneResult

from service.shared.config import get_mongo_settings
from service.shared.models.enums import CollectionName, TransactionType
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
    category: str | None = None,
    transaction_type: TransactionType | None = None,
) -> Cursor:
    """Get expenses in a date range with optional filters.

    Args:
        collection_name: Name of the collection
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)
        category: Optional category filter (None = all)
        transaction_type: Optional Credit or Debit (None = all)

    Returns:
        Cursor over matching documents
    """
    query: dict = {'created_at': {'$gte': start_date, '$lte': end_date}}
    if category is not None:
        query['category'] = category
    if transaction_type is not None:
        query['transaction_type'] = transaction_type.value

    db = get_database()
    collection = db[collection_name]
    return collection.find(query).sort('created_at', -1)
