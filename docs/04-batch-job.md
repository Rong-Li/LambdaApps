# Monthly Batch Job Specification

## Overview

The batch job runs on the **1st of each month** to:
1. Aggregate the previous month's transactions into a summary report
2. Archive all monthly transactions to S3 in Parquet format

---

## Trigger Configuration

### EventBridge Scheduler

| Property | Value |
|----------|-------|
| **Schedule Expression** | `cron(0 0 1 * ? *)` |
| **Timezone** | `America/Toronto` (Eastern Time) |
| **Description** | Runs at 00:00 Toronto ET on the 1st of every month |

### Lambda Configuration

| Property | Value |
|----------|-------|
| **Function Name** | `lambda-home-batch` |
| **Timeout** | 5 minutes (300 seconds) |
| **Memory** | 512 MB |
| **Runtime** | Python 3.14 |

---

## Processing Steps

### Step 1: Determine Target Month

Calculate the first and last day of the previous month based on current date.

**Example:** If today is 2026-02-01 → Target: 2026-01-01 to 2026-01-31

### Step 2: Fetch Raw Transactions

Query MongoDB `expenses` collection for all transactions within the target month's date range.

### Step 3: Aggregate Data

Calculate monthly summary:
- **total_expense**: Sum of all `Debit` transaction amounts
- **total_earning**: Sum of all `Credit` transaction amounts
- **expense_by_category**: Sum grouped by category (Debit only)

### Step 4: Upsert to Reports Collection

Store aggregated data in `reports` collection:
- Use `month` (YYYY-MM) as unique key
- Upsert to handle re-runs safely
- Update `updated_at` timestamp

### Step 5: Export to S3 (Parquet)

Export concatenated monthly transactions as a single Parquet file:
- Combine all expenses (and future investments)
- Write to S3 with path: `transactions/{YYYY}/{YYYY-MM}.parquet`

---

## S3 Storage Structure

### Path Convention

```
s3://{bucket-name}/transactions/{YYYY}/{YYYY-MM}.parquet
```

### Example

```
s3://homeapp-archive/
└── transactions/
    └── 2026/
        ├── 2026-01.parquet
        ├── 2026-02.parquet
        └── 2026-03.parquet
```

### Parquet Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | STRING | MongoDB ObjectId as string |
| `type` | STRING | "expense" or "investment" |
| `amount` | DOUBLE | Transaction amount |
| `category` | STRING | Category (for expenses) |
| `transaction_type` | STRING | Credit/Debit or Buy/Sell |
| `date` | DATE | Transaction date |
| `description` | STRING | Optional description |
| `ticker` | STRING | Ticker symbol (for investments) |
| `asset_class` | STRING | Asset class (for investments) |
| `quantity` | DOUBLE | Quantity (for investments) |
| `created_at` | TIMESTAMP | Record creation time |

---

## Error Handling

### Retry Strategy

| Scenario | Action |
|----------|--------|
| MongoDB connection failure | Retry 3 times with exponential backoff |
| S3 upload failure | Retry 3 times, log failed files |
| Partial failure | Log error, continue with remaining operations |

### Idempotency

The batch job is designed to be **idempotent**:
- Report upsert uses `month` as unique key
- S3 uploads overwrite existing files for the same month
- Safe to re-run if previous execution failed

### Alerting

On failure:
1. Lambda logs error to CloudWatch
2. CloudWatch Alarm triggers on ERROR log pattern
3. (Optional) SNS notification to admin email

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MONGODB_URI` | MongoDB Atlas connection string |
| `MONGODB_DATABASE` | Database name (e.g., "homeapp") |
| `S3_BUCKET_NAME` | Archive bucket name |
| `AWS_REGION` | AWS region |

---

## Expected Output

### Success Response

| Field | Description |
|-------|-------------|
| `statusCode` | 200 |
| `month` | Processed month (YYYY-MM) |
| `expenses_processed` | Count of expenses aggregated |
| `total_expense` | Aggregated expense total |
| `total_earning` | Aggregated earning total |

---

## Monitoring

### CloudWatch Metrics

| Metric | Description |
|--------|-------------|
| `Invocations` | Number of batch executions |
| `Duration` | Execution time |
| `Errors` | Failed executions |

### Custom Metrics (Optional)

| Metric | Description |
|--------|-------------|
| `ExpensesProcessed` | Count of expenses aggregated |
| `S3FileUploaded` | Monthly Parquet file created |
| `ReportUpsertDuration` | Time to upsert report |
