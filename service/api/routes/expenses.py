"""Expense routes for the API."""

from aws_lambda_powertools.event_handler import Response
from aws_lambda_powertools.event_handler.api_gateway import Router
from pydantic import ValidationError

from service.shared.database import mongo_insert
from service.shared.models import ExpenseCreateResponse, ExpenseInput
from service.shared.models.enums import CollectionName

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

    result = mongo_insert(expense_data.model_dump(mode='json'), CollectionName.Expense)

    response = ExpenseCreateResponse(expense_id=str(result.inserted_id))
    return Response(
        status_code=201,
        content_type='application/json',
        body=response.model_dump(),
    )


if __name__ == '__main__':
    from datetime import datetime

    from service.shared.models.enums import Category, TransactionType

    # Create test expense data
    test_expense = ExpenseInput(
        amount=42.50,
        category=Category.Groceries,
        transaction_type=TransactionType.Debit,
        created_at=datetime.now(),
    )

    print(f'Inserting test expense: {test_expense.model_dump(mode="json")}')

    # Insert into MongoDB
    result = mongo_insert(test_expense.model_dump(mode='json'), CollectionName.Expense)

    print('Inserted successfully!')
    print(f'Inserted ID: {result.inserted_id}')
