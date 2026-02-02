"""Shared pytest fixtures for homeapp tests."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def sample_expense_data():
    """Valid expense request data."""
    return {
        'amount': 45.99,
        'category': 'Groceries',
        'transaction_type': 'Debit',
        'created_at': '2026-01-28T14:30:00',
    }


@pytest.fixture
def sample_expense_document():
    """Expense as stored in MongoDB."""
    return {
        '_id': '507f1f77bcf86cd799439011',
        'amount': 45.99,
        'category': 'Groceries',
        'transaction_type': 'Debit',
        'created_at': datetime(2026, 1, 28),
        'recurring_payment': False,
    }


@pytest.fixture
def sample_report_document():
    """Report as stored in MongoDB."""
    return {
        '_id': '507f1f77bcf86cd799439012',
        'month': '2026-01',
        'total_expense': 2450.75,
        'total_earning': 5000.00,
        'expense_by_category': {
            'Groceries': 450.00,
            'EatOut': 200.50,
            'Transportation': 150.00,
            'Mortgage': 1200.00,
            'Utilities': 180.25,
            'Shopping': 120.00,
            'Gas': 100.00,
            'Insurance': 50.00,
        },
        'created_at': datetime(2026, 2, 1, 0, 5, 0),
        'updated_at': datetime(2026, 2, 1, 0, 5, 0),
    }


@pytest.fixture
def multiple_expenses():
    """List of expenses for aggregation testing."""
    return [
        {'amount': 100.0, 'category': 'Groceries', 'transaction_type': 'Debit', 'created_at': datetime(2026, 1, 15)},
        {'amount': 50.0, 'category': 'Groceries', 'transaction_type': 'Debit', 'created_at': datetime(2026, 1, 16)},
        {'amount': 30.0, 'category': 'EatOut', 'transaction_type': 'Debit', 'created_at': datetime(2026, 1, 17)},
        {'amount': 5000.0, 'category': None, 'transaction_type': 'Credit', 'created_at': datetime(2026, 1, 1)},
    ]


@pytest.fixture
def mock_db():
    """Mock MongoDB database."""
    db = MagicMock()
    db.expenses = MagicMock()
    db.reports = MagicMock()
    return db


@pytest.fixture
def api_gateway_event():
    """Factory for API Gateway HTTP API events."""

    def _create_event(
        method: str = 'GET',
        path: str = '/',
        body: str | None = None,
        query_params: dict | None = None,
    ):
        return {
            'version': '2.0',
            'routeKey': f'{method} {path}',
            'rawPath': path,
            'rawQueryString': '',
            'headers': {'content-type': 'application/json'},
            'queryStringParameters': query_params or {},
            'requestContext': {
                'http': {'method': method, 'path': path},
                'requestId': 'test-request-id',
            },
            'body': body,
            'isBase64Encoded': False,
        }

    return _create_event


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    context = MagicMock()
    context.function_name = 'test-function'
    context.memory_limit_in_mb = 128
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789:function:test'
    context.aws_request_id = 'test-request-id'
    return context
