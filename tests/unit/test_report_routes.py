"""Report snapshots must retain categories and support month selection without live services."""

from datetime import date
from unittest.mock import MagicMock

import pytest
from service.api.routes import report
from service.shared.models.report import CategoryBreakdownResponse


@pytest.fixture
def report_source(monkeypatch):
    class Today(date):
        @classmethod
        def today(cls):
            return cls(2026, 3, 10)

    monkeypatch.setattr(report, 'date', Today)
    database = MagicMock()
    monkeypatch.setattr(report, 'get_database', lambda: database)
    if hasattr(report._get_reports_map, 'cache_clear'):
        report._get_reports_map.cache_clear()
    return database.reports.find.return_value.sort


def test_current_month_and_month_menu_retain_investment_housing_and_refunds(report_source):
    report_source.return_value = [
        {
            'month': '2026-03',
            'expense_debit': 1600,
            'expense_credit': 50,
            'earning_credit': 5000,
            'debit_by_category': {'Groceries': 100, 'Investment': 500, 'Housing': 1000},
            'credit_by_category': {'Investment': 50, 'Salary': 5000},
            'count_by_category': {'Groceries': 1, 'Investment': 2, 'Housing': 1, 'Salary': 1},
        },
    ]

    body = report.get_category_breakdown().body

    assert body['current_month'] == {
        'month': '2026-03',
        'net_expense': 1550,
        'net_by_category': {'Groceries': 100, 'Investment': 450, 'Housing': 1000},
        'count_by_category': {'Groceries': 1, 'Investment': 2, 'Housing': 1},
    }
    assert [snapshot['month'] for snapshot in body['current_year_months']] == ['2026-01', '2026-02', '2026-03']
    assert body['current_year_months'][2] == body['current_month']
    assert body['current_year']['net_expense'] == 1550
    assert CategoryBreakdownResponse.model_validate(body).current_month.month == '2026-03'


def test_missing_month_is_explicitly_empty_and_legacy_snapshots_remain(report_source):
    report_source.return_value = [
        {'month': '2026-02', 'expense_debit': 200, 'debit_by_category': {'Groceries': 200}, 'count_by_category': {'Groceries': 2}},
        {'month': '2025-12', 'expense_debit': 300, 'debit_by_category': {'Housing': 300}, 'count_by_category': {'Housing': 1}},
    ]

    body = report.get_category_breakdown().body

    assert body['current_month'] == {
        'month': '2026-03',
        'net_expense': 0,
        'net_by_category': {},
        'count_by_category': {},
    }
    assert body['current_year_months'][0] == {
        'month': '2026-01',
        'net_expense': 0,
        'net_by_category': {},
        'count_by_category': {},
    }
    assert body['last_month']['month'] == '2026-02'
    assert body['last_month']['net_expense'] == 200
    assert body['current_year']['net_expense'] == 200
    assert body['last_year']['net_expense'] == 300


def test_january_has_one_selectable_month_and_previous_december_stays_last_month(report_source, monkeypatch):
    class January(date):
        @classmethod
        def today(cls):
            return cls(2027, 1, 1)

    monkeypatch.setattr(report, 'date', January)
    report_source.return_value = [{'month': '2026-12', 'expense_debit': 80}]

    body = report.get_category_breakdown().body

    assert [snapshot['month'] for snapshot in body['current_year_months']] == ['2027-01']
    assert body['current_month']['net_expense'] == 0
    assert body['last_month']['month'] == '2026-12'
    assert body['last_year']['net_expense'] == 80


def test_next_request_observes_updated_report_instead_of_process_lifetime_cache(report_source):
    report_source.return_value = [{'month': '2026-02', 'expense_debit': 100}]
    first = report.get_category_breakdown().body
    report_source.return_value = [{'month': '2026-02', 'expense_debit': 200}]
    second = report.get_category_breakdown().body

    assert first['current_year']['net_expense'] == 100
    assert second['current_year']['net_expense'] == 200
