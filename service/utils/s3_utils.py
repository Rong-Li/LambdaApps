"""S3 utility functions for exporting data."""

from io import BytesIO

import boto3
import polars as pl
from aws_lambda_powertools import Logger

from service.shared.config import get_s3_settings

logger = Logger()


def get_s3_client():
    """Get S3 client."""
    return boto3.client('s3')


def prepare_transactions_for_export(expenses: list[dict], investments: list[dict]) -> list[dict]:
    """Prepare transactions for Parquet export."""
    records = []

    for expense in expenses:
        records.append(
            {
                'id': str(expense.get('_id', '')),
                'type': 'expense',
                'amount': expense.get('amount'),
                'category': expense.get('category'),
                'transaction_type': expense.get('transaction_type'),
                'created_at': expense.get('created_at'),
                'ticker': None,
                'asset_class': None,
                'quantity': None,
            }
        )

    for investment in investments:
        records.append(
            {
                'id': str(investment.get('_id', '')),
                'type': 'investment',
                'amount': investment.get('price', 0) * investment.get('quantity', 0),
                'category': None,
                'transaction_type': investment.get('transaction_type'),
                'date': investment.get('transaction_date'),
                'description': None,
                'ticker': investment.get('ticker'),
                'asset_class': investment.get('asset_class'),
                'quantity': investment.get('quantity'),
                'created_at': investment.get('created_at'),
            }
        )

    return records


def export_transactions_to_s3(
    expenses: list[dict],
    investments: list[dict],
    year: str,
    month: str,
) -> None:
    """Export monthly transactions to S3 as a single Parquet file."""
    settings = get_s3_settings()

    # Combine all transactions for the month
    records = prepare_transactions_for_export(expenses, investments)

    if not records:
        logger.info('No transactions to export')
        return

    # Convert to Polars DataFrame and write to Parquet
    df = pl.DataFrame(records)

    # Write to buffer
    buffer = BytesIO()
    df.write_parquet(buffer)
    buffer.seek(0)

    # Upload to S3 as single monthly file
    s3_key = f'transactions/{year}/{year}-{month}.parquet'
    s3_client = get_s3_client()

    s3_client.put_object(
        Bucket=settings.s3_bucket_name,
        Key=s3_key,
        Body=buffer.getvalue(),
    )

    logger.info(f'Exported {len(records)} transactions to s3://{settings.s3_bucket_name}/{s3_key}')
