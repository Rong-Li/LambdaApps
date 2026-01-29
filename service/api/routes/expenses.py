"""Expense routes for the API."""

from datetime import date, datetime, time

from aws_lambda_powertools.event_handler import Response
from aws_lambda_powertools.event_handler.api_gateway import Router
from pydantic import ValidationError

from service.shared.database import mongo_get_expenses, mongo_insert
from service.shared.models import Expense, ExpenseCreateResponse, ExpenseInput
from service.shared.models.enums import Category, CollectionName, TransactionType

router = Router()


@router.get('/')
def get_expenses() -> Response:
    """List expenses in a date range with optional filters.

    GET /expense?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&category=...&transaction_type=Credit|Debit
    """
    params = router.current_event.query_string_parameters or {}

    start_date_str = params.get('start_date')
    end_date_str = params.get('end_date')

    if not start_date_str or not end_date_str:
        return Response(
            status_code=422,
            content_type='application/json',
            body={'detail': 'start_date and end_date are required'},
        )

    try:
        start_d = date.fromisoformat(start_date_str)
        end_d = date.fromisoformat(end_date_str)
    except ValueError:
        return Response(
            status_code=422,
            content_type='application/json',
            body={'detail': 'Invalid date format. Use YYYY-MM-DD'},
        )

    if end_d < start_d:
        return Response(
            status_code=422,
            content_type='application/json',
            body={'detail': 'end_date must be on or after start_date'},
        )

    start_date = datetime.combine(start_d, time.min)
    end_date = datetime.combine(end_d, time.max)

    category_param = params.get('category')
    category = None
    if category_param:
        try:
            category = Category(category_param).value
        except ValueError:
            return Response(
                status_code=422,
                content_type='application/json',
                body={'detail': f'Invalid category: {category_param}'},
            )

    transaction_type_param = params.get('transaction_type')
    transaction_type: TransactionType | None = None
    if transaction_type_param:
        try:
            transaction_type = TransactionType(transaction_type_param)
        except ValueError:
            return Response(
                status_code=422,
                content_type='application/json',
                body={'detail': f'Invalid transaction_type: {transaction_type_param}. Use Credit or Debit'},
            )

    cursor = mongo_get_expenses(
        CollectionName.Expense,
        start_date=start_date,
        end_date=end_date,
        category=category,
        transaction_type=transaction_type,
    )

    items = []
    for doc in cursor:
        items.append(
            Expense(
                _id=str(doc['_id']),
                amount=doc['amount'],
                category=Category(doc['category']),
                transaction_type=TransactionType(doc['transaction_type']),
                created_at=doc['created_at'],
            ),
        )

    return Response(
        status_code=200,
        content_type='application/json',
        body=[item.model_dump(mode='json') for item in items],
    )


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
