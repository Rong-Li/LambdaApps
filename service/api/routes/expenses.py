"""Expense routes for the API."""

from aws_lambda_powertools.event_handler import Response
from aws_lambda_powertools.event_handler.api_gateway import Router
from aws_lambda_powertools.utilities.parser import parse
from pydantic import ValidationError

from service.shared.database import mongo_delete_expense, mongo_get_expenses, mongo_insert, mongo_update_expense
from service.shared.models import Expense, ExpenseCreateResponse, ExpenseInput, GetExpenseParams
from service.shared.models.enums import Category, CollectionName, Currency, TransactionType

router = Router()


@router.get('/')
def get_expenses() -> Response:
    """List expenses in a date range with optional filters.

    GET /expense?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&category=...&transaction_type=Credit|Debit
        &has_receipt=true|false&min_amount=...&max_amount=...
    """
    params = router.current_event.query_string_parameters or {}

    try:
        query_params: GetExpenseParams = parse(model=GetExpenseParams, event=params)
    except ValidationError as e:
        return Response(
            status_code=422,
            content_type='application/json',
            body={'detail': e.errors()},
        )

    cursor = mongo_get_expenses(
        CollectionName.Expense,
        start_date=query_params.start_datetime,
        end_date=query_params.end_datetime,
        category=query_params.category.value if query_params.category else None,
        transaction_type=query_params.transaction_type,
        currency=query_params.currency,
        has_receipt=query_params.has_receipt,
        min_amount=query_params.min_amount,
        max_amount=query_params.max_amount,
    )

    items = [
        Expense(
            _id=str(doc['_id']),
            amount=doc['amount'],
            category=Category(doc['category']),
            transaction_type=TransactionType(doc['transaction_type']),
            currency=Currency(doc.get('currency', Currency.CAD)),
            created_at=doc['created_at'],
            merchant=doc.get('merchant'),
            description=doc.get('description'),
            receipt_id=doc.get('receipt_id'),
            recurring_payment=doc.get('recurring_payment', False),
        )
        for doc in cursor
    ]

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

    data = expense_data.model_dump()
    result = mongo_insert(data, CollectionName.Expense)

    response = ExpenseCreateResponse(expense_id=str(result.inserted_id))
    return Response(
        status_code=201,
        content_type='application/json',
        body=response.model_dump(),
    )


@router.put('/<id>')
def update_expense(id: str) -> Response:
    """Update an existing expense by id.

    PUT /expense/{id}
    Body: amount, category, transaction_type, created_at, merchant?, description?
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

    update_doc = expense_data.model_dump()
    result = mongo_update_expense(CollectionName.Expense, id, update_doc)

    if result is None:
        return Response(
            status_code=404,
            content_type='application/json',
            body={'detail': 'Expense not found'},
        )

    updated = Expense(
        _id=id,
        amount=expense_data.amount,
        category=expense_data.category,
        transaction_type=expense_data.transaction_type,
        currency=expense_data.currency,
        created_at=expense_data.created_at,
        merchant=expense_data.merchant,
        description=expense_data.description,
        receipt_id=None,
        recurring_payment=expense_data.recurring_payment,
    )
    return Response(
        status_code=200,
        content_type='application/json',
        body=updated.model_dump(mode='json'),
    )


@router.delete('/<id>')
def delete_expense(id: str) -> Response:
    """Delete an expense by id.

    DELETE /expense/{id}
    """
    result = mongo_delete_expense(CollectionName.Expense, id)

    if result is None:
        return Response(
            status_code=404,
            content_type='application/json',
            body={'detail': 'Expense not found'},
        )

    return Response(status_code=204, content_type='application/json', body='')


if __name__ == '__main__':
    from datetime import datetime

    from service.shared.models.enums import Category, TransactionType

    # --- Test POST /expense ---
    test_expense = ExpenseInput(
        amount=42.50,
        category=Category.Groceries,
        transaction_type=TransactionType.Debit,
        currency=Currency.CAD,
        created_at=datetime.now(),
    )
    mock_event = type('Event', (), {'json_body': test_expense.model_dump(mode='json')})()
    router.current_event = mock_event

    print('\nPOST /expense')
    print(f'Body: {test_expense.model_dump(mode="json")}')
    result = create_expense()
    print(f'Status: {result.status_code}')
    print(f'Body: {result.body}')

    # --- Test GET /expense ---
    mock_event = type('Event', (), {'query_string_parameters': {'start_date': '2026-01-01', 'end_date': '2026-01-31'}})()
    router.current_event = mock_event

    print('GET /expense?start_date=2026-01-01&end_date=2026-01-31')
    response = get_expenses()
    print(f'Status: {response.status_code}')
    print(f'Count: {len(response.body)}')
    for i, exp in enumerate(response.body[:5]):
        print(f'  [{i}] {exp}')
    if len(response.body) > 5:
        print(f'  ... and {len(response.body) - 5} more')

    # --- Test PUT /expense/{id} ---
    test_update_id = '697e8068033459f3d1ea907c'
    test_update_body = {
        'amount': 99.99,
        'category': Category.Shopping.value,
        'transaction_type': TransactionType.Debit.value,
        'currency': 'CAD',
        'created_at': datetime.now().isoformat(),
        'merchant': 'Updated Store',
        'description': 'Updated expense description',
        'recurring_payment': True,
    }
    mock_event = type('Event', (), {'json_body': test_update_body})()
    router.current_event = mock_event

    print('\nPUT /expense/{id}')
    print(f'Id: {test_update_id}')
    print(f'Body: {test_update_body}')
    result = update_expense(test_update_id)
    print(f'Status: {result.status_code}')
    print(f'Body: {result.body}')

    # --- Test DELETE /expense/{id} ---
    test_delete_id = '697e8068033459f3d1ea907c'
    mock_event = type('Event', (), {})()
    router.current_event = mock_event

    print('\nDELETE /expense/{id}')
    print(f'Id: {test_delete_id}')
    result = delete_expense(test_delete_id)
    print(f'Status: {result.status_code}')
    print(f'Body: {result.body}')
