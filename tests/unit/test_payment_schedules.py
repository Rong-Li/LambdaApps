"""Tests for payment schedule API routes."""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from service.api.routes.payment_schedules import (
    create_payment_schedule,
    delete_payment_schedule,
    get_payment_schedule,
    get_payment_schedules,
    router,
    update_payment_schedule,
)
from service.shared.models.enums import CollectionName


@pytest.fixture
def sample_payment_schedule_data():
    """Sample payment schedule input data."""
    return {
        'name': 'Netflix Subscription',
        'amount': 15.99,
        'category': 'Shopping',
        'frequency': 'Monthly',
        'monthly_dates': [1],
        'start_date': '2026-01-01',
    }


@pytest.fixture
def sample_payment_schedule_document():
    """Sample payment schedule MongoDB document."""
    return {
        '_id': '507f1f77bcf86cd799439011',
        'name': 'Netflix Subscription',
        'amount': 15.99,
        'currency': 'CAD',
        'transaction_type': 'Debit',
        'category': 'Shopping',
        'frequency': 'Monthly',
        'monthly_dates': [1],
        'start_date': date(2026, 1, 1),
        'end_date': None,
        'is_active': True,
        'merchant': 'Netflix',
        'description': 'Monthly subscription',
        'created_at': datetime(2026, 1, 1, tzinfo=timezone.utc),
        'updated_at': datetime(2026, 1, 1, tzinfo=timezone.utc),
    }


import pytest


class TestGetPaymentSchedules:
    """Tests for GET /payment-schedule endpoint."""

    @patch('service.api.routes.payment_schedules.mongo_get_payment_schedules')
    def test_get_payment_schedules_success(self, mock_mongo_get, sample_payment_schedule_document):
        """Test successful list returns 200 with schedule list."""
        mock_mongo_get.return_value = iter([sample_payment_schedule_document])

        mock_event = MagicMock()
        mock_event.query_string_parameters = {}
        router.current_event = mock_event

        response = get_payment_schedules()

        assert response.status_code == 200
        assert response.content_type == 'application/json'
        assert len(response.body) == 1
        assert response.body[0]['name'] == 'Netflix Subscription'
        assert response.body[0]['amount'] == 15.99
        mock_mongo_get.assert_called_once()

    @patch('service.api.routes.payment_schedules.mongo_get_payment_schedules')
    def test_get_payment_schedules_inactive(self, mock_mongo_get, sample_payment_schedule_document):
        """Test filtering by inactive schedules."""
        mock_mongo_get.return_value = iter([])

        mock_event = MagicMock()
        mock_event.query_string_parameters = {'is_active': 'false'}
        router.current_event = mock_event

        response = get_payment_schedules()

        assert response.status_code == 200
        mock_mongo_get.assert_called_once_with(
            CollectionName.PaymentSchedule,
            is_active=False,
        )


class TestGetPaymentSchedule:
    """Tests for GET /payment-schedule/{id} endpoint."""

    @patch('service.api.routes.payment_schedules.mongo_get_payment_schedule_by_id')
    def test_get_payment_schedule_success(self, mock_mongo_get, sample_payment_schedule_document):
        """Test successful get returns 200 with schedule."""
        mock_mongo_get.return_value = sample_payment_schedule_document

        response = get_payment_schedule('507f1f77bcf86cd799439011')

        assert response.status_code == 200
        assert response.body['name'] == 'Netflix Subscription'

    @patch('service.api.routes.payment_schedules.mongo_get_payment_schedule_by_id')
    def test_get_payment_schedule_not_found(self, mock_mongo_get):
        """Test not found returns 404."""
        mock_mongo_get.return_value = None

        response = get_payment_schedule('nonexistent')

        assert response.status_code == 404


class TestCreatePaymentSchedule:
    """Tests for POST /payment-schedule endpoint."""

    @patch('service.api.routes.payment_schedules.mongo_insert')
    def test_create_payment_schedule_success(self, mock_mongo_insert, sample_payment_schedule_data):
        """Test successful creation returns 201."""
        mock_result = MagicMock()
        mock_result.inserted_id = '507f1f77bcf86cd799439011'
        mock_mongo_insert.return_value = mock_result

        mock_event = MagicMock()
        mock_event.json_body = sample_payment_schedule_data
        router.current_event = mock_event

        response = create_payment_schedule()

        assert response.status_code == 201
        assert response.body['schedule_id'] == '507f1f77bcf86cd799439011'
        mock_mongo_insert.assert_called_once()

    def test_create_payment_schedule_invalid_frequency(self):
        """Test invalid frequency returns 422."""
        mock_event = MagicMock()
        mock_event.json_body = {
            'name': 'Test',
            'amount': 100,
            'category': 'Groceries',
            'frequency': 'Invalid',
            'start_date': '2026-01-01',
        }
        router.current_event = mock_event

        response = create_payment_schedule()

        assert response.status_code == 422


class TestUpdatePaymentSchedule:
    """Tests for PUT /payment-schedule/{id} endpoint."""

    @patch('service.api.routes.payment_schedules.mongo_get_payment_schedule_by_id')
    @patch('service.api.routes.payment_schedules.mongo_update_payment_schedule')
    def test_update_payment_schedule_success(
        self, mock_mongo_update, mock_mongo_get, sample_payment_schedule_data, sample_payment_schedule_document
    ):
        """Test successful update returns 200."""
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_mongo_update.return_value = mock_result
        mock_mongo_get.return_value = sample_payment_schedule_document

        mock_event = MagicMock()
        mock_event.json_body = sample_payment_schedule_data
        router.current_event = mock_event

        response = update_payment_schedule('507f1f77bcf86cd799439011')

        assert response.status_code == 200
        assert response.body['name'] == 'Netflix Subscription'

    @patch('service.api.routes.payment_schedules.mongo_update_payment_schedule')
    def test_update_payment_schedule_not_found(self, mock_mongo_update, sample_payment_schedule_data):
        """Test not found returns 404."""
        mock_mongo_update.return_value = None

        mock_event = MagicMock()
        mock_event.json_body = sample_payment_schedule_data
        router.current_event = mock_event

        response = update_payment_schedule('nonexistent')

        assert response.status_code == 404


class TestDeletePaymentSchedule:
    """Tests for DELETE /payment-schedule/{id} endpoint."""

    @patch('service.api.routes.payment_schedules.mongo_delete_payment_schedule')
    def test_delete_payment_schedule_success(self, mock_mongo_delete):
        """Test successful delete returns 204."""
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_mongo_delete.return_value = mock_result

        response = delete_payment_schedule('507f1f77bcf86cd799439011')

        assert response.status_code == 204

    @patch('service.api.routes.payment_schedules.mongo_delete_payment_schedule')
    def test_delete_payment_schedule_not_found(self, mock_mongo_delete):
        """Test not found returns 404."""
        mock_mongo_delete.return_value = None

        response = delete_payment_schedule('nonexistent')

        assert response.status_code == 404
