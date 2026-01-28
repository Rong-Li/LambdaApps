"""Report routes for the API."""

from datetime import date

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import Response
from aws_lambda_powertools.event_handler.api_gateway import Router

from service.shared.database import get_database
from service.shared.models import Report, ReportExpenseResponse
from service.shared.models.enums import Category

logger = Logger()
router = Router()


@router.get('/expense')
def get_expense_report() -> Response:
    """Get expense report summary.

    GET /report/expense?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&category=Category
    """
    params = router.current_event.query_string_parameters or {}

    # Validate required parameters
    start_date_str = params.get('start_date')
    end_date_str = params.get('end_date')

    if not start_date_str or not end_date_str:
        return Response(
            status_code=422,
            content_type='application/json',
            body={'detail': 'start_date and end_date are required'},
        )

    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
    except ValueError:
        return Response(
            status_code=422,
            content_type='application/json',
            body={'detail': 'Invalid date format. Use YYYY-MM-DD'},
        )

    if end_date < start_date:
        return Response(
            status_code=422,
            content_type='application/json',
            body={'detail': 'end_date must be after start_date'},
        )

    # Optional category filter
    category_filter = params.get('category')
    if category_filter:
        try:
            Category(category_filter)
        except ValueError:
            return Response(
                status_code=422,
                content_type='application/json',
                body={'detail': f'Invalid category: {category_filter}'},
            )

    db = get_database()

    # Build month range from dates
    start_month = start_date.strftime('%Y-%m')
    end_month = end_date.strftime('%Y-%m')

    query = {'month': {'$gte': start_month, '$lte': end_month}}

    reports_cursor = db.reports.find(query).sort('month', 1)

    reports = []
    for doc in reports_cursor:
        expense_by_category = doc.get('expense_by_category', {})

        # Apply category filter if specified
        if category_filter:
            filtered_amount = expense_by_category.get(category_filter, 0.0)
            reports.append(
                Report(
                    month=doc['month'],
                    total_expense=filtered_amount,
                    total_earning=0.0,
                    expense_by_category={category_filter: filtered_amount},
                )
            )
        else:
            reports.append(
                Report(
                    month=doc['month'],
                    total_expense=doc['total_expense'],
                    total_earning=doc['total_earning'],
                    expense_by_category=expense_by_category,
                )
            )

    response = ReportExpenseResponse(
        start_date=start_date,
        end_date=end_date,
        category_filter=category_filter,
        reports=reports,
        message='No reports found for the specified date range' if not reports else None,
    )

    return Response(
        status_code=200,
        content_type='application/json',
        body=response.model_dump(mode='json'),
    )
