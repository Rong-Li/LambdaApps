"""Tests for Report model."""

from service.shared.models import Report


class TestReport:
    """Tests for Report model."""

    def test_report_model_creation(self):
        """Test Report can be created with new fields."""
        report = Report(
            month='2026-01',
            total_debit=1000.0,
            total_credit=5000.0,
            expense_debit=1000.0,
            expense_credit=0.0,
            earning_debit=0.0,
            earning_credit=5000.0,
            debit_by_category={'Groceries': 500.0, 'EatOut': 500.0},
            credit_by_category={'Salary': 5000.0},
            count_by_category={'Groceries': 5, 'EatOut': 3, 'Salary': 1},
        )

        assert report.total_debit == 1000.0
        assert report.total_credit == 5000.0
        assert report.expense_debit == 1000.0
        assert report.earning_credit == 5000.0

    def test_report_defaults(self):
        """Test Report defaults to zero/empty values."""
        report = Report(month='2026-01')

        assert report.total_debit == 0.0
        assert report.total_credit == 0.0
        assert report.expense_debit == 0.0
        assert report.debit_by_category == {}
        assert report.count_by_category == {}

    def test_report_month_validation(self):
        """Test month field accepts YYYY-MM format."""
        report = Report(month='2026-01')
        assert report.month == '2026-01'
