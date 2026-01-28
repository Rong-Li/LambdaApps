"""Tests for batch job logic."""

from datetime import date
from unittest.mock import patch

from service.batch.handler import aggregate_expenses, get_previous_month, upsert_report


class TestGetPreviousMonth:
    """Tests for previous month calculation."""

    @patch('service.batch.handler.date')
    def test_february_first(self, mock_date):
        """Test calculation on Feb 1st returns January."""
        mock_date.today.return_value = date(2026, 2, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        start, end = get_previous_month()

        assert start == date(2026, 1, 1)
        assert end == date(2026, 1, 31)

    @patch('service.batch.handler.date')
    def test_january_first(self, mock_date):
        """Test calculation on Jan 1st returns December."""
        mock_date.today.return_value = date(2026, 1, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        start, end = get_previous_month()

        assert start == date(2025, 12, 1)
        assert end == date(2025, 12, 31)


class TestAggregateExpenses:
    """Tests for expense aggregation logic."""

    def test_aggregate_basic(self, multiple_expenses):
        """Test basic aggregation."""
        result = aggregate_expenses(multiple_expenses)

        assert result['total_expense'] == 180.0  # 100 + 50 + 30
        assert result['total_earning'] == 5000.0
        assert result['expense_by_category']['Groceries'] == 150.0
        assert result['expense_by_category']['EatOut'] == 30.0

    def test_aggregate_empty_list(self):
        """Test aggregation with no expenses."""
        result = aggregate_expenses([])

        assert result['total_expense'] == 0.0
        assert result['total_earning'] == 0.0
        assert result['expense_by_category'] == {}

    def test_aggregate_only_credits(self):
        """Test aggregation with only credit transactions."""
        expenses = [
            {'amount': 1000.0, 'category': None, 'transaction_type': 'Credit'},
            {'amount': 500.0, 'category': None, 'transaction_type': 'Credit'},
        ]

        result = aggregate_expenses(expenses)

        assert result['total_expense'] == 0.0
        assert result['total_earning'] == 1500.0


class TestUpsertReport:
    """Tests for report upserting."""

    def test_upsert_new_report(self, mock_db):
        """Test creating a new report."""
        aggregated = {
            'total_expense': 1000.0,
            'total_earning': 5000.0,
            'expense_by_category': {'Groceries': 500.0, 'EatOut': 500.0},
        }

        upsert_report(mock_db, '2026-01', aggregated)

        mock_db.reports.update_one.assert_called_once()
        call_args = mock_db.reports.update_one.call_args
        assert call_args[0][0] == {'month': '2026-01'}
        assert call_args[1]['upsert'] is True
