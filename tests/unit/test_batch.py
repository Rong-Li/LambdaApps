"""Tests for batch job logic."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch
from service.shared.models.report import Report

from service.batch.daily_aggregation import _aggregate, run_daily_aggregation
from service.batch.monthly_reaggregation import _get_past_months, run_monthly_reaggregation
from service.batch.recurring_payments import is_schedule_due, run_recurring_payments
from service.batch.handler import handler


class TestAggregate:
    """Tests for the _aggregate helper in daily_aggregation."""

    def test_aggregate_basic(self, multiple_expenses):
        """Test basic aggregation produces correct Report fields."""
        result = _aggregate(multiple_expenses, '2026-01')

        # total_debit = 100 + 50 + 30 = 180
        assert result.total_debit == 180.0
        # total_credit = 5000
        assert result.total_credit == 5000.0

        # expense categories: Groceries (150 debit), EatOut (30 debit)
        assert result.expense_debit == 180.0
        assert result.expense_credit == 0.0

        # Salary credit = 5000
        assert result.earning_credit == 5000.0
        assert result.earning_debit == 0.0

        # Per-category breakdowns
        assert result.debit_by_category['Groceries'] == 150.0
        assert result.debit_by_category['EatOut'] == 30.0
        assert result.count_by_category['Groceries'] == 2
        assert result.count_by_category['EatOut'] == 1

    def test_aggregate_empty_list(self):
        """Test aggregation with no expenses."""
        result = _aggregate([], '2026-01')

        assert result.total_debit == 0.0
        assert result.total_credit == 0.0
        assert result.expense_debit == 0.0
        assert result.earning_credit == 0.0
        assert result.debit_by_category == {}

    def test_aggregate_only_credits(self):
        """Test aggregation with only salary credits."""
        expenses = [
            {'amount': 1000.0, 'category': 'Salary', 'transaction_type': 'Credit'},
            {'amount': 500.0, 'category': 'Salary', 'transaction_type': 'Credit'},
        ]

        result = _aggregate(expenses, '2026-01')

        assert result.total_debit == 0.0
        assert result.total_credit == 1500.0
        assert result.earning_credit == 1500.0
        assert result.expense_debit == 0.0


class TestGetPastMonths:
    """Tests for _get_past_months in monthly_reaggregation."""

    @patch('service.batch.monthly_reaggregation.date')
    def test_returns_correct_months(self, mock_date):
        mock_date.today.return_value = date(2026, 3, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        months = _get_past_months(3)

        assert len(months) == 3
        # Should be Feb, Jan, Dec (going backward)
        assert months[0] == (date(2026, 2, 1), date(2026, 2, 28))
        assert months[1] == (date(2026, 1, 1), date(2026, 1, 31))
        assert months[2] == (date(2025, 12, 1), date(2025, 12, 31))


class TestDailyAggregation:
    """Tests for run_daily_aggregation."""

    @patch('service.batch.daily_aggregation._upsert_report')
    @patch('service.batch.daily_aggregation._aggregate')
    @patch('service.batch.daily_aggregation.mongo_get_expenses')
    @patch('service.batch.daily_aggregation.get_database')
    def test_skips_when_no_transactions(self, mock_get_db, mock_fetch, mock_agg, mock_upsert):
        mock_fetch.return_value = []

        result = run_daily_aggregation()

        assert result['skipped'] is True
        mock_agg.assert_not_called()
        mock_upsert.assert_not_called()

    @patch('service.batch.daily_aggregation._upsert_report')
    @patch('service.batch.daily_aggregation._aggregate')
    @patch('service.batch.daily_aggregation.mongo_get_expenses')
    @patch('service.batch.daily_aggregation.get_database')
    def test_processes_when_transactions_exist(self, mock_get_db, mock_fetch, mock_agg, mock_upsert):
        mock_fetch.return_value = [{'amount': 100.0}]
        mock_agg.return_value = Report(month='2026-01', total_debit=100.0)

        result = run_daily_aggregation()

        assert result['skipped'] is False
        assert result['expenses_processed'] == 1
        mock_agg.assert_called_once()
        mock_upsert.assert_called_once()


class TestBatchHandler:
    """Tests for the unified batch handler pipeline."""

    @patch('service.batch.handler.date')
    @patch('service.batch.handler.run_monthly_reaggregation')
    @patch('service.batch.handler.run_daily_aggregation')
    @patch('service.batch.handler.run_recurring_payments')
    def test_handler_runs_reaggregation_on_first_of_month(self, mock_recurring, mock_daily, mock_monthly, mock_date):
        mock_date.today.return_value = date(2026, 1, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        mock_recurring.return_value = {'success': True}
        mock_daily.return_value = {'success': True}
        mock_monthly.return_value = {'success': True}

        result = handler({}, MagicMock())

        assert result['statusCode'] == 200
        mock_recurring.assert_called_once()
        mock_daily.assert_called_once()
        mock_monthly.assert_called_once()
        assert result['body']['monthly_reaggregation']['success'] is True

    @patch('service.batch.handler.date')
    @patch('service.batch.handler.run_monthly_reaggregation')
    @patch('service.batch.handler.run_daily_aggregation')
    @patch('service.batch.handler.run_recurring_payments')
    def test_handler_skips_reaggregation_not_on_first(self, mock_recurring, mock_daily, mock_monthly, mock_date):
        mock_date.today.return_value = date(2026, 1, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        result = handler({}, MagicMock())

        assert result['statusCode'] == 200
        mock_recurring.assert_called_once()
        mock_daily.assert_called_once()
        mock_monthly.assert_not_called()
        assert result['body']['monthly_reaggregation']['skipped'] is True
        assert result['body']['monthly_reaggregation']['reason'] == 'not_first_of_month'


class TestIsScheduleDue:
    """Tests for schedule due date checking."""

    def test_monthly_schedule_due(self):
        schedule = {
            'frequency': 'Monthly',
            'start_date': date(2026, 1, 15),
            'end_date': date(2027, 1, 15),
            'monthly_dates': [15],
        }
        assert is_schedule_due(schedule, date(2026, 2, 15)) is True

    def test_monthly_schedule_not_due(self):
        schedule = {
            'frequency': 'Monthly',
            'start_date': date(2026, 1, 15),
            'end_date': date(2027, 1, 15),
            'monthly_dates': [15],
        }
        assert is_schedule_due(schedule, date(2026, 2, 14)) is False