"""Cash routes for the API."""

from datetime import datetime, timezone

from aws_lambda_powertools.event_handler import Response
from aws_lambda_powertools.event_handler.api_gateway import Router
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from service.shared.database import (
    mongo_get_cash_balance,
    mongo_get_cash_transactions,
    mongo_reset_cash,
    mongo_update_cash_balance_and_add_transaction,
)
from service.shared.models import CashBalance, CashResponse, CashTransaction, TransactionType
from service.shared.models.types import PositiveAmount

router = Router()


class CashTransactionInput(BaseModel):
    """Schema for creating a new cash transaction."""

    amount: PositiveAmount
    type: TransactionType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(populate_by_name=True)


@router.get('/')
def get_cash() -> Response:
    """Get the current cash balance and transaction history.

    GET /cash
    """
    balance_doc = mongo_get_cash_balance()
    cursor = mongo_get_cash_transactions()

    balance = CashBalance(
        balance=balance_doc['balance'],
        last_updated_date=balance_doc['last_updated_date'],
    )

    transactions = [
        CashTransaction(
            amount=doc['amount'],
            type=TransactionType(doc['type']),
            timestamp=doc['timestamp'],
        )
        for doc in cursor
    ]

    response = CashResponse(balance=balance, transactions=transactions)
    return Response(
        status_code=200,
        content_type='application/json',
        body=response.model_dump(mode='json'),
    )


@router.post('/')
def add_cash_transaction() -> Response:
    """Update balance and add a new cash transaction.

    POST /cash
    Body: amount, type, timestamp?
    """
    try:
        body = router.current_event.json_body
        txn_data = CashTransactionInput(**body)
    except (ValidationError, TypeError, ValueError) as e:
        return Response(
            status_code=422,
            content_type='application/json',
            body={'detail': str(e)},
        )

    mongo_update_cash_balance_and_add_transaction(
        amount=txn_data.amount,
        transaction_type=txn_data.type,
        timestamp=txn_data.timestamp,
    )

    return Response(
        status_code=201,
        content_type='application/json',
        body={'message': 'Transaction added and balance updated'},
    )


@router.delete('/')
def reset_cash() -> Response:
    """Reset the cash balance to 0 and delete all transaction history.

    DELETE /cash
    """
    mongo_reset_cash()
    return Response(
        status_code=200,
        content_type='application/json',
        body={'message': 'Cash data reset successfully'},
    )
