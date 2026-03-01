"""Report routes for the API."""

import calendar
from datetime import date, timedelta
from functools import lru_cache


from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import Response
from aws_lambda_powertools.event_handler.api_gateway import Router

from service.shared.utils.mongo import get_database
from service.shared.models.enums import Category, CategoryExpense
from service.shared.models.report import Report
from service.shared.utils.date_utils import get_month_lookback_start

logger = Logger()
router = Router()

VALID_MONTHS = {6, 12, 18, 24}
MAX_LOOKBACK_MONTHS = 24


@lru_cache
def _get_reports_map() -> dict[str, Report]:
    """Fetch all reports for the last 24 months and return as {month: Report}.

    This serves as the single data source for both endpoints,
    avoiding redundant DB queries within the same Lambda invocation.
    """
    today = date.today()
    start_month = get_month_lookback_start(today, MAX_LOOKBACK_MONTHS).strftime('%Y-%m')
    end_month = today.strftime('%Y-%m')

    db = get_database()
    cursor = db.reports.find(
        {'month': {'$gte': start_month, '$lte': end_month}}
    ).sort('month', 1)

    return {doc['month']: Report(**doc) for doc in cursor}


# --------------- Compute helpers ---------------


def _compute_net_expense(report: Report) -> float:
    """Compute net_expense = expense_debit - expense_credit."""
    return report.expense_debit - report.expense_credit


def _compute_net_earning(report: Report) -> float:
    """Compute net_earning = earning_credit - earning_debit."""
    return report.earning_credit - report.earning_debit


def _compute_net_by_category(report: Report) -> dict[str, float]:
    """Compute per-category net (debit - credit), expense categories only."""
    debit_by_cat = report.debit_by_category
    credit_by_cat = report.credit_by_category
    all_cats = set(debit_by_cat.keys()) | set(credit_by_cat.keys())
    result = {}
    for cat in all_cats:
        if cat in CategoryExpense.values():
            net = debit_by_cat.get(cat, 0.0) - credit_by_cat.get(cat, 0.0)
            if net != 0.0:
                result[cat] = net
    return result


def _compute_category_net(report: Report, category: str) -> float:
    """Compute net for a single category from debit_by_category - credit_by_category."""
    debit = report.debit_by_category.get(category, 0.0)
    credit = report.credit_by_category.get(category, 0.0)
    return debit - credit


def _aggregate_reports(reports: list[Report]) -> dict | None:
    """Aggregate a list of Report objects into combined net/category totals.

    Returns None if the list is empty.
    """
    if not reports:
        return None

    total_net_expense = 0.0
    agg_net_by_cat: dict[str, float] = {}
    agg_count_by_cat: dict[str, int] = {}

    for r in reports:
        total_net_expense += _compute_net_expense(r)
        for cat, val in _compute_net_by_category(r).items():
            agg_net_by_cat[cat] = agg_net_by_cat.get(cat, 0.0) + val
        for cat, cnt in r.count_by_category.items():
            if cat in CategoryExpense.values():
                agg_count_by_cat[cat] = agg_count_by_cat.get(cat, 0) + cnt

    return {
        'net_expense': total_net_expense,
        'net_by_category': agg_net_by_cat,
        'count_by_category': agg_count_by_cat,
    }


# --------------- Endpoints ---------------


@router.get('/trend')
def get_spending_trend() -> Response:
    """Get spending trend for bar chart.

    GET /report/trend?months=6&category=Groceries
    """
    params = router.current_event.query_string_parameters or {}

    # Parse months param
    months = 6
    months_str = params.get('months')
    if months_str:
        try:
            months = int(months_str)
        except ValueError:
            pass
    if months not in VALID_MONTHS:
        months = 6

    # Parse optional category filter
    category_filter = params.get('category')
    if category_filter and category_filter not in Category._value2member_map_:
        return Response(
            status_code=422,
            content_type='application/json',
            body={'detail': f'Invalid category: {category_filter}'},
        )

    today = date.today()
    current_month_str = today.strftime('%Y-%m')
    start_month_str = get_month_lookback_start(today, months).strftime('%Y-%m')

    reports_map = _get_reports_map()

    # Build current month and trend
    current_month_report = None
    trend = []

    for month_key, r in reports_map.items():
        if month_key < start_month_str:
            continue

        if category_filter:
            value = _compute_category_net(r, category_filter)
        else:
            value = _compute_net_expense(r)

        if month_key == current_month_str:
            _, days_in_month = calendar.monthrange(today.year, today.month)
            current_month_report = {
                'month': current_month_str,
                'net_expense': value,
                'days_remaining': days_in_month - today.day,
            }
        else:
            trend.append({'month': month_key, 'net_expense': value})

    # Default current month if no report exists yet
    if current_month_report is None:
        _, days_in_month = calendar.monthrange(today.year, today.month)
        current_month_report = {
            'month': current_month_str,
            'net_expense': 0.0,
            'days_remaining': days_in_month - today.day,
        }

    # Get previous month's earning
    prev_month_earning = 0.0
    prev_month_str = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
    prev_report = reports_map.get(prev_month_str)
    if prev_report:
        prev_month_earning = _compute_net_earning(prev_report)

    response = {
        'months_requested': months,
        'category_filter': category_filter,
        'current_month': current_month_report,
        'previous_month_earning': prev_month_earning,
        'trend': trend,
    }

    return Response(
        status_code=200,
        content_type='application/json',
        body=response,
    )


@router.get('/category-breakdown')
def get_category_breakdown() -> Response:
    """Get category breakdown for donut chart.

    GET /report/category-breakdown

    Returns three fixed snapshots: last_month, current_year, last_year.
    Excludes earning-specific categories.
    """
    today = date.today()
    current_year = today.year

    reports_map = _get_reports_map()

    # --- Last month snapshot ---
    prev_month_str = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
    last_month_data = None

    prev_report = reports_map.get(prev_month_str)
    if prev_report:
        net_by_cat = _compute_net_by_category(prev_report)
        count_by_cat = {k: v for k, v in prev_report.count_by_category.items()
                        if k in CategoryExpense.values()}
        last_month_data = {
            'month': prev_month_str,
            'net_expense': _compute_net_expense(prev_report),
            'net_by_category': net_by_cat,
            'count_by_category': count_by_cat,
        }

    # --- Current year snapshot ---
    year_start = f'{current_year}-01'
    year_end = today.strftime('%Y-%m')
    year_reports = [r for m, r in reports_map.items() if year_start <= m <= year_end]

    agg = _aggregate_reports(year_reports)
    current_year_data = None
    if agg:
        current_year_data = {'year': str(current_year), **agg}

    # --- Last year snapshot ---
    last_year = current_year - 1
    ly_start = f'{last_year}-01'
    ly_end = f'{last_year}-12'
    ly_reports = [r for m, r in reports_map.items() if ly_start <= m <= ly_end]

    agg = _aggregate_reports(ly_reports)
    last_year_data = None
    if agg:
        last_year_data = {'year': str(last_year), **agg}

    response = {
        'last_month': last_month_data,
        'current_year': current_year_data,
        'last_year': last_year_data,
    }

    return Response(
        status_code=200,
        content_type='application/json',
        body=response,
    )
