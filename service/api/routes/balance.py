"""Balance routes for the API."""

from aws_lambda_powertools.event_handler import Response
from aws_lambda_powertools.event_handler.api_gateway import Router
from pydantic import ValidationError

from service.shared.database import (
    get_database,
    mongo_delete_balance,
    mongo_get_balances,
    mongo_insert,
    mongo_reconcile_balance,
)
from service.shared.models.balance import Balance, BalanceInput, BalanceResponse
from service.shared.models.enums import CollectionName

router = Router()


@router.get('/')
def get_balances() -> Response:
    """List all balance records sorted by record_time descending.

    GET /balance
    """
    cursor = mongo_get_balances()

    items = [
        Balance(
            _id=str(doc['_id']),
            cad_balance=doc['cad_balance'],
            rmb_balance=doc['rmb_balance'],
            record_time=doc['record_time'],
            note=doc.get('note'),
            reconciled=doc.get('reconciled', False),
            cad_off_amount=doc.get('cad_off_amount'),
            rmb_off_amount=doc.get('rmb_off_amount'),
            last_balance_date=doc.get('last_balance_date'),
        )
        for doc in cursor
    ]

    return Response(
        status_code=200,
        content_type='application/json',
        body=[item.model_dump(mode='json', exclude={'last_balance_date'}) for item in items],
    )


@router.post('/')
def create_balance() -> Response:
    """Create a new balance record and auto-reconcile.

    POST /balance
    Body: cad_balance, rmb_balance, record_time, note?

    Returns 201 if reconciled (or no previous balance), 202 if off > 2%.
    """
    try:
        body = router.current_event.json_body
        balance_data = BalanceInput(**body)
    except (ValidationError, TypeError, ValueError) as e:
        return Response(
            status_code=422,
            content_type='application/json',
            body={'detail': str(e)},
        )

    data = balance_data.model_dump()
    result = mongo_insert(data, CollectionName.Balance)
    balance_id = str(result.inserted_id)

    # Fetch the inserted document for reconciliation
    db = get_database()
    balance_doc = db[CollectionName.Balance].find_one({'_id': result.inserted_id})

    reconciled, cad_off, rmb_off = mongo_reconcile_balance(balance_doc)

    status_code = 201 if reconciled else 202
    message = 'Balance reconciled successfully' if reconciled else 'Balance created but reconciliation failed'

    response = BalanceResponse(
        message=message,
        balance_id=balance_id,
        reconciled=reconciled,
        cad_off_amount=cad_off,
        rmb_off_amount=rmb_off,
    )
    return Response(
        status_code=status_code,
        content_type='application/json',
        body=response.model_dump(),
    )


@router.delete('/<id>')
def delete_balance(id: str) -> Response:
    """Delete a balance record by id.

    DELETE /balance/{id}
    """
    result = mongo_delete_balance(id)

    if result is None:
        return Response(
            status_code=404,
            content_type='application/json',
            body={'detail': 'Balance not found'},
        )

    return Response(status_code=204, content_type='application/json', body='')


@router.post('/reconcile')
def reconcile_latest() -> Response:
    """Reconcile the latest unreconciled balance.

    POST /balance/reconcile
    """
    db = get_database()
    collection = db[CollectionName.Balance]

    # Find the latest unreconciled balance
    balance_doc = collection.find_one(
        {'reconciled': False},
        sort=[('record_time', -1)],
    )

    if balance_doc is None:
        return Response(
            status_code=404,
            content_type='application/json',
            body={'detail': 'No unreconciled balance found'},
        )

    reconciled, cad_off, rmb_off = mongo_reconcile_balance(balance_doc)

    status_code = 201 if reconciled else 202
    message = 'Balance reconciled successfully' if reconciled else 'Reconciliation failed'

    response = BalanceResponse(
        message=message,
        balance_id=str(balance_doc['_id']),
        reconciled=reconciled,
        cad_off_amount=cad_off,
        rmb_off_amount=rmb_off,
    )
    return Response(
        status_code=status_code,
        content_type='application/json',
        body=response.model_dump(),
    )
