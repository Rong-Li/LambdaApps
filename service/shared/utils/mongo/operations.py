"""Generic MongoDB CRUD operations shared across collections."""

from aws_lambda_powertools import Logger
from bson.errors import InvalidId
from bson.objectid import ObjectId
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from service.shared.config import get_mongo_settings
from service.shared.models.enums import CollectionName
from service.shared.utils.mongo.connection import COLLECTION_INDEXES, ensure_indexes, get_database

logger = Logger()


def _parse_id(doc_id: str):
    """Convert a string id to ObjectId if it is a valid 24-char hex, else return as-is."""
    if len(doc_id) == 24:
        try:
            return ObjectId(doc_id)
        except InvalidId:
            pass
    return doc_id


def mongo_insert(
    document: dict,
    collection_name: CollectionName,
) -> InsertOneResult:
    """Insert a document into a MongoDB collection and log the result.

    Args:
        document: Dict to insert (should be validated before calling)
        collection_name: Name of the collection

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
        logger.info(
            f'Successfully inserted 1 record into {collection_name}',
            extra={'inserted_id': str(result.inserted_id)},
        )
    else:
        logger.warning(f'Insert not acknowledged for {collection_name}')

    return result


def mongo_update(
    collection_name: CollectionName,
    doc_id: str,
    update_doc: dict,
) -> UpdateResult | None:
    """Update a single document by id.

    Only the fields in update_doc are set; other fields are left unchanged.

    Args:
        collection_name: Name of the collection
        doc_id: Document id (ObjectId string or string id)
        update_doc: Document fields to set (validated dict, no _id)

    Returns:
        UpdateResult if a document was matched and updated, None if not found
    """
    parsed_id = _parse_id(doc_id)
    db = get_database()
    collection = db[collection_name]
    result = collection.update_one(
        {'_id': parsed_id},
        {'$set': update_doc},
    )
    if result.matched_count == 0:
        return None
    logger.info(
        f'Updated document in {collection_name}',
        extra={'doc_id': doc_id},
    )
    return result


def mongo_delete(
    collection_name: CollectionName,
    doc_id: str,
) -> DeleteResult | None:
    """Delete a single document by id.

    Args:
        collection_name: Name of the collection
        doc_id: Document id (ObjectId string or string id)

    Returns:
        DeleteResult if a document was deleted, None if not found
    """
    parsed_id = _parse_id(doc_id)
    db = get_database()
    collection = db[collection_name]
    result = collection.delete_one({'_id': parsed_id})
    if result.deleted_count == 0:
        return None
    logger.info(
        f'Deleted document from {collection_name}',
        extra={'doc_id': doc_id},
    )
    return result
