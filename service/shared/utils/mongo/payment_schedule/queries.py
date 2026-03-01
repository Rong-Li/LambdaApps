"""Payment schedule collection queries."""

from aws_lambda_powertools import Logger
from pymongo.cursor import Cursor

from service.shared.models.enums import CollectionName
from service.shared.utils.mongo.connection import get_database
from service.shared.utils.mongo.operations import _parse_id

logger = Logger()


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
    doc_id = _parse_id(schedule_id)
    db = get_database()
    collection = db[collection_name]
    return collection.find_one({'_id': doc_id})
