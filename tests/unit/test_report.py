"""Tests for Report model."""

from service.shared.models import Report


class TestReport:
    """Tests for Report model."""

    def test_report_net_calculation(self):
        """Test net is calculated correctly."""
        report = Report(
            month='2026-01',
            total_expense=1000.0,
            total_earning=5000.0,
            expense_by_category={'Groceries': 500.0, 'EatOut': 500.0},
        )

        assert report.net == 4000.0

    def test_report_zero_net(self):
        """Test net when expense equals earning."""
        report = Report(
            month='2026-01',
            total_expense=1000.0,
            total_earning=1000.0,
            expense_by_category={'Groceries': 1000.0},
        )

        assert report.net == 0.0

    def test_report_negative_net(self):
        """Test net when expense exceeds earning."""
        report = Report(
            month='2026-01',
            total_expense=2000.0,
            total_earning=1000.0,
            expense_by_category={'Groceries': 2000.0},
        )

        assert report.net == -1000.0
