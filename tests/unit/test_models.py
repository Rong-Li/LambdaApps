"""Tests for Pydantic models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from service.shared.models import Category, Currency, ExpenseInput, TransactionType


class TestExpenseInput:
    """Tests for ExpenseInput model validation."""

    def test_valid_expense(self, sample_expense_data):
        """Test creating a valid expense."""
        expense = ExpenseInput(**sample_expense_data)

        assert expense.amount == 45.99
        assert expense.category == Category.Groceries
        assert expense.transaction_type == TransactionType.Debit
        assert expense.currency == Currency.CAD
        assert expense.created_at == datetime(2026, 1, 28, 14, 30, 0)

    def test_amount_must_be_positive(self):
        """Test that amount must be greater than 0."""
        with pytest.raises(ValidationError) as exc_info:
            ExpenseInput(
                amount=-10.0,
                category='Groceries',
                transaction_type='Debit',
                created_at='2026-01-28T10:00:00',
            )

        assert 'greater than 0' in str(exc_info.value).lower()

    def test_amount_rounded_to_two_decimals(self):
        """Test that amount is rounded to 2 decimal places."""
        expense = ExpenseInput(
            amount=45.999,
            category='Groceries',
            transaction_type='Debit',
            created_at='2026-01-28T10:00:00',
        )

        assert expense.amount == 46.0

    def test_invalid_category(self):
        """Test that invalid category raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ExpenseInput(
                amount=50.0,
                category='INVALID_CATEGORY',
                transaction_type='Debit',
                created_at='2026-01-28T10:00:00',
            )

        assert 'category' in str(exc_info.value).lower()

    def test_invalid_datetime_format(self):
        """Test that invalid datetime format raises error."""
        with pytest.raises(ValidationError):
            ExpenseInput(
                amount=50.0,
                category='Groceries',
                transaction_type='Debit',
                created_at='28-01-2026',  # Wrong format
            )


class TestCategory:
    """Tests for Category enum."""

    def test_all_categories_exist(self):
        """Test all expected categories are defined."""
        expected = [
            'Groceries',
            'EatOut',
            'Transportation',
            'Mortgage',
            'Utilities',
            'Shopping',
            'Gas',
            'Insurance',
        ]

        for cat in expected:
            assert hasattr(Category, cat)

    def test_category_values(self):
        """Test category string values."""
        assert Category.Groceries.value == 'Groceries'
        assert Category.EatOut.value == 'EatOut'


class TestTransactionType:
    """Tests for TransactionType enum."""

    def test_credit_and_debit(self):
        """Test both transaction types exist."""
        assert TransactionType.Credit.value == 'Credit'
        assert TransactionType.Debit.value == 'Debit'


class TestCurrency:
    """Tests for Currency enum."""

    def test_values(self):
        """Test currency string values."""
        assert Currency.CAD.value == 'CAD'
        assert Currency.RMB.value == 'RMB'
