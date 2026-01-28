"""Expense routes for the API."""

from aws_lambda_powertools.event_handler import Response
from aws_lambda_powertools.event_handler.api_gateway import Router
from pydantic import ValidationError

from service.shared.database import mongo_insert
from service.shared.models import ExpenseCreateResponse, ExpenseInput

router = Router()


@router.post('/')
def create_expense() -> Response:
    """Create a new expense.

    POST /expense
    """
    try:
        body = router.current_event.json_body
        expense_data = ExpenseInput(**body)
    except ValidationError as e:
        return Response(
            status_code=422,
            content_type='application/json',
            body={'detail': e.errors()},
        )

    result = mongo_insert(expense_data.model_dump(mode='json'), 'expenses')

    response = ExpenseCreateResponse(expense_id=str(result.inserted_id))
    return Response(
        status_code=201,
        content_type='application/json',
        body=response.model_dump(),
    )
