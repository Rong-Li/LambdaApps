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
        'currency': 'CAD',
        'created_at': '2026-01-28T14:30:00',
        'postal_code': 'M5V 2H1',
    }


@pytest.fixture
def sample_expense_document():
    """Expense as stored in MongoDB."""
    return {
        '_id': '507f1f77bcf86cd799439011',
        'amount': 45.99,
        'category': 'Groceries',
        'transaction_type': 'Debit',
        'currency': 'CAD',
        'created_at': datetime(2026, 1, 28),
        'postal_code': 'M5V 2H1',
        'recurring_payment': False,
    }


@pytest.fixture
def sample_report_document():
    """Report as stored in MongoDB."""
    return {
        '_id': '507f1f77bcf86cd799439012',
        'month': '2026-01',
        'total_debit': 2450.75,
        'total_credit': 5000.00,
        'expense_debit': 2450.75,
        'expense_credit': 0.0,
        'earning_debit': 0.0,
        'earning_credit': 5000.00,
        'debit_by_category': {
            'Groceries': 450.00,
            'Dine Out': 200.50,
            'Transportation': 150.00,
            'Housing': 1250.00,
            'Utilities': 180.25,
            'Shopping': 120.00,
            'Car': 100.00,
        },
        'credit_by_category': {
            'Salary': 5000.00,
        },
        'count_by_category': {
            'Groceries': 10,
            'Dine Out': 5,
            'Transportation': 3,
            'Housing': 2,
            'Utilities': 2,
            'Shopping': 4,
            'Car': 3,
            'Salary': 1,
        },
    }


@pytest.fixture
def multiple_expenses():
    """List of expenses for aggregation testing."""
    return [
        {'amount': 100.0, 'category': 'Groceries', 'transaction_type': 'Debit', 'created_at': datetime(2026, 1, 15)},
        {'amount': 50.0, 'category': 'Groceries', 'transaction_type': 'Debit', 'created_at': datetime(2026, 1, 16)},
        {'amount': 30.0, 'category': 'Dine Out', 'transaction_type': 'Debit', 'created_at': datetime(2026, 1, 17)},
        {'amount': 5000.0, 'category': 'Salary', 'transaction_type': 'Credit', 'created_at': datetime(2026, 1, 1)},
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
