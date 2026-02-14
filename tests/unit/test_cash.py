"""Tests for cash API routes."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from service.api.routes.cash import add_cash_transaction, get_cash, reset_cash, router
from service.shared.models import TransactionType


class TestCashRoutes:
    """Tests for cash API endpoints."""

    @patch('service.api.routes.cash.mongo_get_cash_balance')
    @patch('service.api.routes.cash.mongo_get_cash_transactions')
    def test_get_cash_success(self, mock_get_txns, mock_get_balance):
        """Test GET /cash returns balance and transactions."""
        now = datetime.now()
        mock_get_balance.return_value = {
            'balance': 150.0,
            'last_updated_date': now.date(),
        }
        mock_get_txns.return_value = iter([
            {'amount': 100.0, 'type': 'Credit', 'timestamp': now},
            {'amount': 50.0, 'type': 'Debit', 'timestamp': now},
        ])

        response = get_cash()

        assert response.status_code == 200
        assert response.body['balance']['balance'] == 150.0
        assert len(response.body['transactions']) == 2
        assert response.body['transactions'][0]['amount'] == 100.0
        assert response.body['transactions'][0]['type'] == 'Credit'

    @patch('service.api.routes.cash.mongo_update_cash_balance_and_add_transaction')
    def test_add_cash_transaction_success(self, mock_update):
        """Test POST /cash successfully adds transaction."""
        mock_event = MagicMock()
        mock_event.json_body = {
            'amount': 25.0,
            'type': 'Credit',
        }
        router.current_event = mock_event

        response = add_cash_transaction()

        assert response.status_code == 201
        assert response.body['message'] == 'Transaction added and balance updated'
        mock_update.assert_called_once()
        args = mock_update.call_args[1]
        assert args['amount'] == 25.0
        assert args['transaction_type'] == TransactionType.Credit

    @patch('service.api.routes.cash.mongo_update_cash_balance_and_add_transaction')
    def test_add_cash_transaction_invalid_data(self, mock_update):
        """Test POST /cash with invalid data returns 422."""
        mock_event = MagicMock()
        mock_event.json_body = {
            'amount': -10.0,  # Invalid amount
            'type': 'Credit',
        }
        router.current_event = mock_event

        response = add_cash_transaction()

        assert response.status_code == 422
        mock_update.assert_not_called()

    @patch('service.api.routes.cash.mongo_reset_cash')
    def test_reset_cash_success(self, mock_reset):
        """Test DELETE /cash successfully resets data."""
        response = reset_cash()

        assert response.status_code == 200
        assert response.body['message'] == 'Cash data reset successfully'
        mock_reset.assert_called_once()
