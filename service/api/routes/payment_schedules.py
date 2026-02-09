"""Payment schedule routes for the API."""

from datetime import datetime, timezone

from aws_lambda_powertools.event_handler import Response
from aws_lambda_powertools.event_handler.api_gateway import Router
from pydantic import ValidationError

from service.shared.database import (
    mongo_delete_payment_schedule,
    mongo_get_payment_schedule_by_id,
    mongo_get_payment_schedules,
    mongo_insert,
    mongo_update_payment_schedule,
)
from service.shared.models import PaymentSchedule, PaymentScheduleCreateResponse, PaymentScheduleInput
from service.shared.models.enums import Category, CollectionName, Currency, Frequency, TransactionType

router = Router()


@router.get('/')
def get_payment_schedules() -> Response:
    """List payment schedules.

    GET /payment-schedule?is_active=true|false
    """
    params = router.current_event.query_string_parameters or {}
    is_active_param = params.get('is_active')

    is_active: bool | None = True  # Default to active only
    if is_active_param is not None:
        if is_active_param.lower() == 'false':
            is_active = False
        elif is_active_param.lower() == 'all':
            is_active = None

    cursor = mongo_get_payment_schedules(
        CollectionName.PaymentSchedule,
        is_active=is_active,
    )

    items = [
        PaymentSchedule(
            _id=str(doc['_id']),
            name=doc['name'],
            amount=doc['amount'],
            currency=Currency(doc.get('currency', Currency.CAD)),
            transaction_type=TransactionType(doc.get('transaction_type', TransactionType.Debit)),
            category=Category(doc['category']),
            merchant=doc.get('merchant'),
            description=doc.get('description'),
            frequency=Frequency(doc['frequency']),
            monthly_dates=doc.get('monthly_dates'),
            start_date=doc['start_date'],
            end_date=doc.get('end_date'),
            is_active=doc.get('is_active', True),
            created_at=doc.get('created_at', datetime.now(timezone.utc)),
            updated_at=doc.get('updated_at', datetime.now(timezone.utc)),
        )
        for doc in cursor
    ]

    return Response(
        status_code=200,
        content_type='application/json',
        body=[item.model_dump(mode='json') for item in items],
    )


@router.get('/<id>')
def get_payment_schedule(id: str) -> Response:
    """Get a single payment schedule by id.

    GET /payment-schedule/{id}
    """
    doc = mongo_get_payment_schedule_by_id(CollectionName.PaymentSchedule, id)

    if doc is None:
        return Response(
            status_code=404,
            content_type='application/json',
            body={'detail': 'Payment schedule not found'},
        )

    schedule = PaymentSchedule(
        _id=str(doc['_id']),
        name=doc['name'],
        amount=doc['amount'],
        currency=Currency(doc.get('currency', Currency.CAD)),
        transaction_type=TransactionType(doc.get('transaction_type', TransactionType.Debit)),
        category=Category(doc['category']),
        merchant=doc.get('merchant'),
        description=doc.get('description'),
        frequency=Frequency(doc['frequency']),
        monthly_dates=doc.get('monthly_dates'),
        start_date=doc['start_date'],
        end_date=doc.get('end_date'),
        is_active=doc.get('is_active', True),
        created_at=doc.get('created_at', datetime.now(timezone.utc)),
        updated_at=doc.get('updated_at', datetime.now(timezone.utc)),
    )

    return Response(
        status_code=200,
        content_type='application/json',
        body=schedule.model_dump(mode='json'),
    )


@router.post('/')
def create_payment_schedule() -> Response:
    """Create a new payment schedule.

    POST /payment-schedule
    """
    try:
        body = router.current_event.json_body
        schedule_data = PaymentScheduleInput(**body)
    except ValidationError as e:
        return Response(
            status_code=422,
            content_type='application/json',
            body={'detail': e.errors()},
        )

    now = datetime.now(timezone.utc)
    data = schedule_data.model_dump()
    data['created_at'] = now
    data['updated_at'] = now

    result = mongo_insert(data, CollectionName.PaymentSchedule)

    response = PaymentScheduleCreateResponse(schedule_id=str(result.inserted_id))
    return Response(
        status_code=201,
        content_type='application/json',
        body=response.model_dump(),
    )


@router.put('/<id>')
def update_payment_schedule(id: str) -> Response:
    """Update an existing payment schedule by id.

    PUT /payment-schedule/{id}
    """
    try:
        body = router.current_event.json_body
        schedule_data = PaymentScheduleInput(**body)
    except ValidationError as e:
        return Response(
            status_code=422,
            content_type='application/json',
            body={'detail': e.errors()},
        )

    update_doc = schedule_data.model_dump()
    update_doc['updated_at'] = datetime.now(timezone.utc)

    result = mongo_update_payment_schedule(CollectionName.PaymentSchedule, id, update_doc)

    if result is None:
        return Response(
            status_code=404,
            content_type='application/json',
            body={'detail': 'Payment schedule not found'},
        )

    # Fetch updated document
    doc = mongo_get_payment_schedule_by_id(CollectionName.PaymentSchedule, id)
    updated = PaymentSchedule(
        _id=id,
        name=schedule_data.name,
        amount=schedule_data.amount,
        currency=schedule_data.currency,
        transaction_type=schedule_data.transaction_type,
        category=schedule_data.category,
        merchant=schedule_data.merchant,
        description=schedule_data.description,
        frequency=schedule_data.frequency,
        monthly_dates=schedule_data.monthly_dates,
        start_date=schedule_data.start_date,
        end_date=schedule_data.end_date,
        is_active=schedule_data.is_active,
        created_at=doc.get('created_at', datetime.now(timezone.utc)) if doc else datetime.now(timezone.utc),
        updated_at=update_doc['updated_at'],
    )

    return Response(
        status_code=200,
        content_type='application/json',
        body=updated.model_dump(mode='json'),
    )


@router.delete('/<id>')
def delete_payment_schedule(id: str) -> Response:
    """Delete a payment schedule by id.

    DELETE /payment-schedule/{id}
    """
    result = mongo_delete_payment_schedule(CollectionName.PaymentSchedule, id)

    if result is None:
        return Response(
            status_code=404,
            content_type='application/json',
            body={'detail': 'Payment schedule not found'},
        )

    return Response(status_code=204, content_type='application/json', body='')
