"""MongoDB connection and index management."""

from functools import lru_cache

from aws_lambda_powertools import Logger
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from service.shared.config import get_mongo_settings
from service.shared.models.enums import CollectionName
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
    existing_indexes = {idx['name'] for idx in collection.list_indexes()}
    missing_indexes = [idx for idx in indexes if idx.document['name'] not in existing_indexes]

    if missing_indexes:
        collection.create_indexes(missing_indexes)
        logger.info(
            f'Created indexes for {collection.name}',
            extra={'indexes': [idx.document['name'] for idx in missing_indexes]},
        )
