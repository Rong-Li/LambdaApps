"""Tests for expenses API route."""

from unittest.mock import MagicMock, patch

from service.api.routes.expenses import create_expense, delete_expense, get_expenses, router, update_expense
from service.shared.models.enums import CollectionName


class TestGetExpenses:
    """Tests for GET /expense endpoint."""

    @patch('service.api.routes.expenses.mongo_get_expenses')
    def test_get_expenses_success(self, mock_mongo_get_expenses, sample_expense_document):
        """Test successful list returns 200 with expense list."""
        mock_cursor = iter([sample_expense_document])
        mock_mongo_get_expenses.return_value = mock_cursor

        mock_event = MagicMock()
        mock_event.query_string_parameters = {
            'start_date': '2026-01-01',
            'end_date': '2026-01-31',
        }
        router.current_event = mock_event

        response = get_expenses()

        assert response.status_code == 200
        assert response.content_type == 'application/json'
        assert len(response.body) == 1
        assert response.body[0]['id'] == sample_expense_document['_id']
        assert response.body[0]['amount'] == sample_expense_document['amount']
        assert response.body[0]['category'] == sample_expense_document['category']
        assert response.body[0]['transaction_type'] == sample_expense_document['transaction_type']
        assert response.body[0]['currency'] == sample_expense_document['currency']
        assert response.body[0]['postal_code'] == sample_expense_document['postal_code']
        mock_mongo_get_expenses.assert_called_once()

    @patch('service.api.routes.expenses.mongo_get_expenses')
    def test_get_expenses_with_filters(self, mock_mongo_get_expenses, sample_expense_document):
        """Test list with category and transaction_type filters."""
        mock_mongo_get_expenses.return_value = iter([sample_expense_document])

        mock_event = MagicMock()
        mock_event.query_string_parameters = {
            'start_date': '2026-01-01',
            'end_date': '2026-01-31',
            'category': 'Groceries',
            'transaction_type': 'Debit',
        }
        router.current_event = mock_event

        response = get_expenses()

        assert response.status_code == 200
        assert len(response.body) == 1
        call_kwargs = mock_mongo_get_expenses.call_args[1]
        assert call_kwargs['category'] == 'Groceries'
        assert call_kwargs['transaction_type'].value == 'Debit'
        assert call_kwargs['currency'] is None

    @patch('service.api.routes.expenses.mongo_get_expenses')
    def test_get_expenses_empty_list(self, mock_mongo_get_expenses):
        """Test list returns 200 with empty array when no expenses."""
        mock_mongo_get_expenses.return_value = iter([])

        mock_event = MagicMock()
        mock_event.query_string_parameters = {'start_date': '2026-01-01', 'end_date': '2026-01-31'}
        router.current_event = mock_event

        response = get_expenses()

        assert response.status_code == 200
        assert response.body == []

    @patch('service.api.routes.expenses.mongo_get_expenses')
    def test_get_expenses_missing_dates(self, mock_mongo_get_expenses):
        """Test missing start_date or end_date returns 422."""
        mock_event = MagicMock()
        mock_event.query_string_parameters = {'start_date': '2026-01-01'}
        router.current_event = mock_event

        response = get_expenses()

        assert response.status_code == 422
        detail = response.body['detail']
        assert any(e.get('loc') == ('end_date',) and e.get('type') == 'missing' for e in detail)
        mock_mongo_get_expenses.assert_not_called()

    @patch('service.api.routes.expenses.mongo_get_expenses')
    def test_get_expenses_invalid_date_format(self, mock_mongo_get_expenses):
        """Test invalid date format returns 422."""
        mock_event = MagicMock()
        mock_event.query_string_parameters = {
            'start_date': '2026-01-01',
            'end_date': 'not-a-date',
        }
        router.current_event = mock_event

        response = get_expenses()

        assert response.status_code == 422
        detail = response.body['detail']
        assert any('date' in e.get('msg', '').lower() for e in detail)
        mock_mongo_get_expenses.assert_not_called()

    @patch('service.api.routes.expenses.mongo_get_expenses')
    def test_get_expenses_end_before_start(self, mock_mongo_get_expenses):
        """Test end_date before start_date returns 422."""
        mock_event = MagicMock()
        mock_event.query_string_parameters = {
            'start_date': '2026-01-31',
            'end_date': '2026-01-01',
        }
        router.current_event = mock_event

        response = get_expenses()

        assert response.status_code == 422
        detail = response.body['detail']
        assert any('end_date must be on or after start_date' in e.get('msg', '') for e in detail)
        mock_mongo_get_expenses.assert_not_called()

    @patch('service.api.routes.expenses.mongo_get_expenses')
    def test_get_expenses_invalid_category(self, mock_mongo_get_expenses):
        """Test invalid category returns 422."""
        mock_event = MagicMock()
        mock_event.query_string_parameters = {
            'start_date': '2026-01-01',
            'end_date': '2026-01-31',
            'category': 'InvalidCategory',
        }
        router.current_event = mock_event

        response = get_expenses()

        assert response.status_code == 422
        detail = response.body['detail']
        assert any(e.get('loc') == ('category',) for e in detail)
        mock_mongo_get_expenses.assert_not_called()

    @patch('service.api.routes.expenses.mongo_get_expenses')
    def test_get_expenses_invalid_transaction_type(self, mock_mongo_get_expenses):
        """Test invalid transaction_type returns 422."""
        mock_event = MagicMock()
        mock_event.query_string_parameters = {
            'start_date': '2026-01-01',
            'end_date': '2026-01-31',
            'transaction_type': 'Invalid',
        }
        router.current_event = mock_event

        response = get_expenses()

        assert response.status_code == 422
        detail = response.body['detail']
        assert any(e.get('loc') == ('transaction_type',) for e in detail)
        mock_mongo_get_expenses.assert_not_called()

    @patch('service.api.routes.expenses.mongo_get_expenses')
    def test_get_expenses_with_currency_filter(self, mock_mongo_get_expenses, sample_expense_document):
        """Test list with currency filter."""
        mock_mongo_get_expenses.return_value = iter([sample_expense_document])

        mock_event = MagicMock()
        mock_event.query_string_parameters = {
            'start_date': '2026-01-01',
            'end_date': '2026-01-31',
            'currency': 'RMB',
        }
        router.current_event = mock_event

        response = get_expenses()

        assert response.status_code == 200
        call_kwargs = mock_mongo_get_expenses.call_args[1]
        assert call_kwargs['currency'].value == 'RMB'


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


class TestUpdateExpense:
    """Tests for PUT /expense/{id} endpoint."""

    @patch('service.api.routes.expenses.mongo_update_expense')
    def test_update_expense_success(self, mock_mongo_update):
        """Test successful expense update returns 200 with updated expense."""
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_mongo_update.return_value = mock_result

        expense_id = '507f1f77bcf86cd799439011'
        body = {
            'amount': 90.00,
            'category': 'Groceries',
            'transaction_type': 'Debit',
            'currency': 'CAD',
            'postal_code': 'M5V 2H1',
            'created_at': '2026-01-30T14:30:00',
            'merchant': 'Costco',
            'description': 'Weekly groceries - updated',
        }
        mock_event = MagicMock()
        mock_event.json_body = body
        router.current_event = mock_event

        response = update_expense(expense_id)

        assert response.status_code == 200
        assert response.content_type == 'application/json'
        assert response.body['id'] == expense_id
        assert response.body['amount'] == 90.00
        assert response.body['currency'] == 'CAD'
        assert response.body['postal_code'] == 'M5V 2H1'
        assert response.body['merchant'] == 'Costco'
        assert response.body['description'] == 'Weekly groceries - updated'
        mock_mongo_update.assert_called_once()
        call_args = mock_mongo_update.call_args[0]
        assert call_args[0] == CollectionName.Expense
        assert call_args[1] == expense_id
        update_doc = call_args[2]
        assert update_doc['amount'] == 90.00
        assert update_doc['merchant'] == 'Costco'
        assert update_doc['description'] == 'Weekly groceries - updated'

    @patch('service.api.routes.expenses.mongo_update_expense')
    def test_update_expense_not_found(self, mock_mongo_update):
        """Test update with non-existent id returns 404."""
        mock_mongo_update.return_value = None

        mock_event = MagicMock()
        mock_event.json_body = {
            'amount': 90.00,
            'category': 'Groceries',
            'transaction_type': 'Debit',
            'created_at': '2026-01-30T14:30:00',
        }
        router.current_event = mock_event

        response = update_expense('nonexistent-id')

        assert response.status_code == 404
        assert response.body['detail'] == 'Expense not found'

    @patch('service.api.routes.expenses.mongo_update_expense')
    def test_update_expense_invalid_body(self, mock_mongo_update):
        """Test update with invalid body returns 422."""
        mock_event = MagicMock()
        mock_event.json_body = {
            'amount': -10.0,
            'category': 'Groceries',
            'transaction_type': 'Debit',
            'created_at': '2026-01-30T14:30:00',
        }
        router.current_event = mock_event

        response = update_expense('507f1f77bcf86cd799439011')

        assert response.status_code == 422
        assert 'detail' in response.body
        mock_mongo_update.assert_not_called()


class TestDeleteExpense:
    """Tests for DELETE /expense/{id} endpoint."""

    @patch('service.api.routes.expenses.mongo_delete_expense')
    def test_delete_expense_success(self, mock_mongo_delete):
        """Test successful delete returns 204."""
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_mongo_delete.return_value = mock_result

        response = delete_expense('507f1f77bcf86cd799439011')

        assert response.status_code == 204
        mock_mongo_delete.assert_called_once_with(CollectionName.Expense, '507f1f77bcf86cd799439011')

    @patch('service.api.routes.expenses.mongo_delete_expense')
    def test_delete_expense_not_found(self, mock_mongo_delete):
        """Test delete with non-existent id returns 404."""
        mock_mongo_delete.return_value = None

        response = delete_expense('nonexistent-id')

        assert response.status_code == 404
        assert response.body['detail'] == 'Expense not found'
