"""Unit tests for mongo expense queries."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from service.shared.models.enums import CollectionName, TransactionType


class TestMongoGetExpenses:
    """Tests for mongo_get_expenses."""

    @patch('service.shared.utils.mongo.expense.queries.get_database')
    def test_mongo_get_expenses_builds_date_query(self, mock_get_database):
        """Test query includes created_at date range."""
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_collection.find.return_value.sort.return_value = mock_cursor
        mock_get_database.return_value = {CollectionName.Expense: mock_collection}

        from service.shared.utils.mongo.expense.queries import mongo_get_expenses

        start = datetime(2026, 1, 1, 0, 0, 0)
        end = datetime(2026, 1, 31, 23, 59, 59, 999999)

        result = mongo_get_expenses(
            CollectionName.Expense,
            start_date=start,
            end_date=end,
        )

        assert result is mock_cursor
        mock_collection.find.assert_called_once_with(
            {'created_at': {'$gte': start, '$lte': end}},
        )
        mock_collection.find.return_value.sort.assert_called_once_with('created_at', -1)

    @patch('service.shared.utils.mongo.expense.queries.get_database')
    def test_mongo_get_expenses_with_category(self, mock_get_database):
        """Test query includes category when provided."""
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_collection.find.return_value.sort.return_value = mock_cursor
        mock_get_database.return_value = {CollectionName.Expense: mock_collection}

        from service.shared.utils.mongo.expense.queries import mongo_get_expenses

        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31, 23, 59, 59, 999999)

        mongo_get_expenses(
            CollectionName.Expense,
            start_date=start,
            end_date=end,
            category='Groceries',
        )

        mock_collection.find.assert_called_once_with(
            {
                'created_at': {'$gte': start, '$lte': end},
                'category': 'Groceries',
            },
        )

    @patch('service.shared.utils.mongo.expense.queries.get_database')
    def test_mongo_get_expenses_with_transaction_type(self, mock_get_database):
        """Test query includes transaction_type when provided."""
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_collection.find.return_value.sort.return_value = mock_cursor
        mock_get_database.return_value = {CollectionName.Expense: mock_collection}

        from service.shared.utils.mongo.expense.queries import mongo_get_expenses

        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31, 23, 59, 59, 999999)

        mongo_get_expenses(
            CollectionName.Expense,
            start_date=start,
            end_date=end,
            transaction_type=TransactionType.Debit,
        )

        mock_collection.find.assert_called_once_with(
            {
                'created_at': {'$gte': start, '$lte': end},
                'transaction_type': 'Debit',
            },
        )

    @patch('service.shared.utils.mongo.expense.queries.get_database')
    def test_mongo_get_expenses_with_all_filters(self, mock_get_database):
        """Test query includes category and transaction_type when both provided."""
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_collection.find.return_value.sort.return_value = mock_cursor
        mock_get_database.return_value = {CollectionName.Expense: mock_collection}

        from service.shared.utils.mongo.expense.queries import mongo_get_expenses

        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31, 23, 59, 59, 999999)

        mongo_get_expenses(
            CollectionName.Expense,
            start_date=start,
            end_date=end,
            category='EatOut',
            transaction_type=TransactionType.Credit,
        )

        mock_collection.find.assert_called_once_with(
            {
                'created_at': {'$gte': start, '$lte': end},
                'category': 'EatOut',
                'transaction_type': 'Credit',
            },
        )
