"""MongoDB utility package — re-exports for convenient importing."""

from service.shared.utils.mongo.connection import (
    COLLECTION_INDEXES,
    ensure_indexes,
    get_client,
    get_database,
)
from service.shared.utils.mongo.operations import (
    mongo_delete,
    mongo_insert,
    mongo_update,
)
from service.shared.utils.mongo.balance.queries import (
    RECONCILIATION_THRESHOLD,
    mongo_get_balances,
    mongo_get_previous_balance,
    mongo_reconcile_balance,
    mongo_update_balance_reconciled,
)
from service.shared.utils.mongo.cash.queries import (
    mongo_get_cash_balance,
    mongo_get_cash_transactions,
    mongo_reset_cash,
    mongo_update_cash_balance_and_add_transaction,
)
from service.shared.utils.mongo.expense.queries import mongo_get_expenses
from service.shared.utils.mongo.payment_schedule.queries import (
    mongo_get_payment_schedule_by_id,
    mongo_get_payment_schedules,
)

__all__ = [
    # connection
    'COLLECTION_INDEXES',
    'ensure_indexes',
    'get_client',
    'get_database',
    # generic operations
    'mongo_delete',
    'mongo_insert',
    'mongo_update',
    # balance
    'RECONCILIATION_THRESHOLD',
    'mongo_get_balances',
    'mongo_get_previous_balance',
    'mongo_reconcile_balance',
    'mongo_update_balance_reconciled',
    # cash
    'mongo_get_cash_balance',
    'mongo_get_cash_transactions',
    'mongo_reset_cash',
    'mongo_update_cash_balance_and_add_transaction',
    # expense
    'mongo_get_expenses',
    # payment_schedule
    'mongo_get_payment_schedule_by_id',
    'mongo_get_payment_schedules',
]
