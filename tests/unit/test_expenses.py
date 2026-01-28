"""Tests for expenses API route."""

from unittest.mock import MagicMock, patch

from service.api.routes.expenses import create_expense, router


class TestCreateExpense:
    """Tests for POST /expense endpoint."""

    @patch('service.api.routes.expenses.mongo_insert')
    def test_create_expense_success(self, mock_mongo_insert, sample_expense_data):
        """Test successful expense creation returns 201."""
        mock_result = MagicMock()
        mock_result.inserted_id = '507f1f77bcf86cd799439011'
        mock_mongo_insert.return_value = mock_result

        mock_event = MagicMock()
        mock_event.json_body = sample_expense_data
        router.current_event = mock_event

        response = create_expense()

        assert response.status_code == 201
        assert response.content_type == 'application/json'
        assert response.body['expense_id'] == '507f1f77bcf86cd799439011'
        mock_mongo_insert.assert_called_once()

    @patch('service.api.routes.expenses.mongo_insert')
    def test_create_expense_invalid_amount(self, mock_mongo_insert):
        """Test invalid amount returns 422."""
        mock_event = MagicMock()
        mock_event.json_body = {
            'amount': -10.0,
            'category': 'Groceries',
            'transaction_type': 'Debit',
            'created_at': '2026-01-28T10:00:00',
        }
        router.current_event = mock_event

        response = create_expense()

        assert response.status_code == 422
        assert response.content_type == 'application/json'
        assert 'detail' in response.body
        mock_mongo_insert.assert_not_called()

    @patch('service.api.routes.expenses.mongo_insert')
    def test_create_expense_invalid_category(self, mock_mongo_insert):
        """Test invalid category returns 422."""
        mock_event = MagicMock()
        mock_event.json_body = {
            'amount': 50.0,
            'category': 'InvalidCategory',
            'transaction_type': 'Debit',
            'created_at': '2026-01-28T10:00:00',
        }
        router.current_event = mock_event

        response = create_expense()

        assert response.status_code == 422
        assert 'detail' in response.body
        mock_mongo_insert.assert_not_called()

    @patch('service.api.routes.expenses.mongo_insert')
    def test_create_expense_missing_field(self, mock_mongo_insert):
        """Test missing required field returns 422."""
        mock_event = MagicMock()
        mock_event.json_body = {
            'amount': 50.0,
            'category': 'Groceries',
            # missing transaction_type and created_at
        }
        router.current_event = mock_event

        response = create_expense()

        assert response.status_code == 422
        assert 'detail' in response.body
        mock_mongo_insert.assert_not_called()

    @patch('service.api.routes.expenses.mongo_insert')
    def test_create_expense_amount_rounded(self, mock_mongo_insert, sample_expense_data):
        """Test that expense amount is rounded to 2 decimals."""
        mock_result = MagicMock()
        mock_result.inserted_id = '507f1f77bcf86cd799439011'
        mock_mongo_insert.return_value = mock_result

        sample_expense_data['amount'] = 45.999
        mock_event = MagicMock()
        mock_event.json_body = sample_expense_data
        router.current_event = mock_event

        response = create_expense()

        assert response.status_code == 201
        call_args = mock_mongo_insert.call_args[0][0]
        assert call_args['amount'] == 46.0
