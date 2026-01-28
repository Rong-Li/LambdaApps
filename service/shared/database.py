"""MongoDB database connection manager."""

from functools import lru_cache

from aws_lambda_powertools import Logger
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.results import InsertOneResult

from service.shared.config import get_mongo_settings

logger = Logger()


@lru_cache
def get_client() -> MongoClient:
    """Get cached MongoDB client instance."""
    settings = get_mongo_settings()
    return MongoClient(settings.mongodb_uri)


def get_database() -> Database:
    """Get MongoDB database instance."""
    settings = get_mongo_settings()
    client = get_client()
    return client[settings.mongodb_database]


def mongo_insert(document: dict, collection_name: str) -> InsertOneResult:
    """Insert a document into a MongoDB collection and log the result.

    Args:
        document: Dict to insert (should be validated before calling)
        collection_name: Name of the collection

    Returns:
        InsertOneResult from MongoDB
    """
    db = get_database()
    result = db[collection_name].insert_one(document)

    if result.acknowledged:
        logger.info(f'Successfully inserted 1 record into {collection_name}', extra={'inserted_id': str(result.inserted_id)})
    else:
        logger.warning(f'Insert not acknowledged for {collection_name}')

    return result
