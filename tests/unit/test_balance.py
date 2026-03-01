"""Tests for balance API routes."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

from bson import ObjectId

from service.api.routes.balance import create_balance, delete_balance, get_balances, reconcile_latest, router
from service.shared.models.enums import CollectionName


class TestGetBalances:
    """Tests for GET /balance endpoint."""

    @patch('service.api.routes.balance.mongo_get_balances')
    def test_get_balances_success(self, mock_get_balances):
        """Test GET /balance returns sorted balances."""
        mock_get_balances.return_value = iter([
            {
                '_id': '507f1f77bcf86cd799439011',
                'cad_balance': 5000.0,
                'rmb_balance': 10000.0,
                'record_time': datetime(2026, 2, 1),
                'note': 'February balance',
                'reconciled': True,
                'cad_off_amount': 10.5,
                'rmb_off_amount': -20.0,
            },
            {
                '_id': '507f1f77bcf86cd799439012',
                'cad_balance': 4500.0,
                'rmb_balance': 9000.0,
                'record_time': datetime(2026, 1, 1),
                'note': None,
                'reconciled': False,
                'cad_off_amount': None,
                'rmb_off_amount': None,
            },
        ])

        response = get_balances()

        assert response.status_code == 200
        assert len(response.body) == 2
        assert response.body[0]['cad_balance'] == 5000.0
        assert response.body[0]['reconciled'] is True
        assert response.body[0]['cad_off_amount'] == 10.5
        assert response.body[1]['cad_balance'] == 4500.0
        assert response.body[1]['reconciled'] is False

    @patch('service.api.routes.balance.mongo_get_balances')
    def test_get_balances_empty(self, mock_get_balances):
        """Test GET /balance returns empty list when no balances."""
        mock_get_balances.return_value = iter([])

        response = get_balances()

        assert response.status_code == 200
        assert response.body == []


class TestCreateBalance:
    """Tests for POST /balance endpoint."""

    @patch('service.api.routes.balance.get_database')
    @patch('service.api.routes.balance.mongo_reconcile_balance')
    @patch('service.api.routes.balance.mongo_insert')
    def test_create_balance_reconciled(self, mock_insert, mock_reconcile, mock_get_db):
        """Test POST /balance with successful reconciliation returns 201."""
        inserted_id = ObjectId()
        mock_result = MagicMock()
        mock_result.inserted_id = inserted_id
        mock_insert.return_value = mock_result

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=MagicMock())
        mock_db.__getitem__.return_value.find_one.return_value = {
            '_id': inserted_id,
            'cad_balance': 5000.0,
            'rmb_balance': 10000.0,
            'record_time': datetime(2026, 2, 1),
        }
        mock_get_db.return_value = mock_db

        mock_reconcile.return_value = (True, 10.5, -20.0)

        mock_event = MagicMock()
        mock_event.json_body = {
            'cad_balance': 5000.0,
            'rmb_balance': 10000.0,
            'record_time': '2026-02-01',
        }
        router.current_event = mock_event

        response = create_balance()

        assert response.status_code == 201
        assert response.body['reconciled'] is True
        assert response.body['cad_off_amount'] == 10.5
        assert response.body['rmb_off_amount'] == -20.0
        assert response.body['balance_id'] == str(inserted_id)
        mock_insert.assert_called_once()

    @patch('service.api.routes.balance.get_database')
    @patch('service.api.routes.balance.mongo_reconcile_balance')
    @patch('service.api.routes.balance.mongo_insert')
    def test_create_balance_not_reconciled(self, mock_insert, mock_reconcile, mock_get_db):
        """Test POST /balance with failed reconciliation returns 202."""
        inserted_id = ObjectId()
        mock_result = MagicMock()
        mock_result.inserted_id = inserted_id
        mock_insert.return_value = mock_result

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=MagicMock())
        mock_db.__getitem__.return_value.find_one.return_value = {
            '_id': inserted_id,
            'cad_balance': 5000.0,
            'rmb_balance': 10000.0,
            'record_time': datetime(2026, 2, 1),
        }
        mock_get_db.return_value = mock_db

        mock_reconcile.return_value = (False, 500.0, 100.0)

        mock_event = MagicMock()
        mock_event.json_body = {
            'cad_balance': 5000.0,
            'rmb_balance': 10000.0,
            'record_time': '2026-02-01',
        }
        router.current_event = mock_event

        response = create_balance()

        assert response.status_code == 202
        assert response.body['reconciled'] is False
        assert response.body['cad_off_amount'] == 500.0

    def test_create_balance_invalid_data(self):
        """Test POST /balance with missing fields returns 422."""
        mock_event = MagicMock()
        mock_event.json_body = {
            'cad_balance': 5000.0,
            # missing rmb_balance and record_time
        }
        router.current_event = mock_event

        response = create_balance()

        assert response.status_code == 422


class TestDeleteBalance:
    """Tests for DELETE /balance/{id} endpoint."""

    @patch('service.api.routes.balance.mongo_delete')
    def test_delete_balance_success(self, mock_delete):
        """Test successful delete returns 204."""
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_delete.return_value = mock_result

        response = delete_balance('507f1f77bcf86cd799439011')

        assert response.status_code == 204
        mock_delete.assert_called_once_with(CollectionName.Balance, '507f1f77bcf86cd799439011')

    @patch('service.api.routes.balance.mongo_delete')
    def test_delete_balance_not_found(self, mock_delete):
        """Test delete with non-existent id returns 404."""
        mock_delete.return_value = None

        response = delete_balance('nonexistent-id')

        assert response.status_code == 404
        assert response.body['detail'] == 'Balance not found'


class TestReconcileLatest:
    """Tests for POST /balance/reconcile endpoint."""

    @patch('service.api.routes.balance.mongo_reconcile_balance')
    @patch('service.api.routes.balance.get_database')
    def test_reconcile_success(self, mock_get_db, mock_reconcile):
        """Test reconcile with successful result returns 201."""
        balance_id = ObjectId()
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {
            '_id': balance_id,
            'cad_balance': 5000.0,
            'rmb_balance': 10000.0,
            'record_time': datetime(2026, 2, 1),
            'reconciled': False,
        }
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        mock_reconcile.return_value = (True, 5.0, -10.0)

        response = reconcile_latest()

        assert response.status_code == 201
        assert response.body['reconciled'] is True
        assert response.body['cad_off_amount'] == 5.0
        assert response.body['rmb_off_amount'] == -10.0
        assert response.body['balance_id'] == str(balance_id)

    @patch('service.api.routes.balance.mongo_reconcile_balance')
    @patch('service.api.routes.balance.get_database')
    def test_reconcile_failure(self, mock_get_db, mock_reconcile):
        """Test reconcile with failed result returns 202."""
        balance_id = ObjectId()
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {
            '_id': balance_id,
            'cad_balance': 5000.0,
            'rmb_balance': 10000.0,
            'record_time': datetime(2026, 2, 1),
            'reconciled': False,
        }
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        mock_reconcile.return_value = (False, 300.0, 50.0)

        response = reconcile_latest()

        assert response.status_code == 202
        assert response.body['reconciled'] is False

    @patch('service.api.routes.balance.get_database')
    def test_reconcile_no_unreconciled(self, mock_get_db):
        """Test reconcile when no unreconciled balance returns 404."""
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        response = reconcile_latest()

        assert response.status_code == 404
        assert response.body['detail'] == 'No unreconciled balance found'
