"""Expense collection queries."""

from datetime import datetime

from aws_lambda_powertools import Logger
from pymongo.cursor import Cursor

from service.shared.models.enums import Category, CollectionName, Currency, TransactionType
from service.shared.utils.mongo.connection import get_database

logger = Logger()


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
        currency: Optional currency filter (None = all)
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
