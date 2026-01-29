# Final Specification: Personal Finance Tracker (homeapp)

> **Status:** Finalized  
> **Last Updated:** 2026-01-28  
> **Related Docs:** [Architecture](./01-architecture.md) | [API Spec](./02-api-specification.md) | [Data Models](./03-data-models.md) | [Batch Job](./04-batch-job.md) | [Deployment](./05-deployment.md)

---

## 1. Project Overview

A serverless backend designed for high extensibility, allowing for the logging of expenses and investments, with a dedicated **monthly** batch process for data aggregation and archival.

---

## 2. Technical Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.14+ (managed by `uv`) |
| **API Framework** | AWS Lambda Powertools (`APIGatewayRestResolver`) |
| **API Gateway** | AWS HTTP API |
| **Data Validation** | Pydantic v2 |
| **Database** | MongoDB Atlas (PyMongo - Synchronous) |
| **Storage** | S3 (Parquet archives via Polars) |
| **Scheduler** | EventBridge Scheduler |
| **Lambda Layers** | API layer (powertools, pydantic, pymongo), Batch layer (+ polars) |
| **CI/CD** | GitHub Actions (zip-and-upload deployment) |
| **Testing** | pytest |

---

## 3. Detailed Requirements

### 3.1 REST API Features

#### Expense Endpoint: `POST /expense`

- Accepts JSON matching the `Expense` model
- Validates input via Pydantic
- Returns `201 Created` on success

**Expense Model:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount` | float | ✅ | Positive transaction amount |
| `category` | Enum | ✅ | See category list below |
| `transaction_type` | Enum | ✅ | `Credit` (income) or `Debit` (expense) |
| `date` | date | ✅ | Transaction date (ISO 8601) |
| `description` | string | ❌ | Optional description |

**Category Enum Values:**
- `Groceries`
- `EatOut`
- `Transportation`
- `Mortgage`
- `Utilities`
- `Shopping`
- `Gas`
- `Insurance`

#### Report Endpoint: `GET /report/expense`

- Retrieves aggregated data from the `reports` collection
- Query parameters:
  - `start_date` (required): Start of date range
  - `end_date` (required): End of date range
  - `category` (optional): Filter by category; if omitted, returns all categories

#### Investment Endpoint (Future): `POST /investments`

- Designed to log asset purchases
- Fields (planned): Ticker, Asset Class, Price, Quantity, Transaction Type, Transaction Date, Broker/Account

---

### 3.2 Monthly Batch Job

**Trigger:** EventBridge Scheduler - runs on the **1st of each month** at 00:00 **Toronto ET**

**Logic:**
1. Fetch all raw entries from the **previous month**
2. Perform aggregations:
   - Total expense (sum of all Debit transactions)
   - Expense by category (breakdown)
   - Total earning (sum of all Credit transactions)
3. Upsert the result into the `reports` collection with structure:
   - `month`: YYYY-MM format
   - `total_expense`: float
   - `total_earning`: float
   - `expense_by_category`: dict
4. Export **concatenated monthly transactions** to S3 as a single **Parquet** file:
   - Path: `s3://bucket/transactions/{YYYY}/{YYYY-MM}.parquet`
   - Includes both expenses and investments (future)

**Benefits:**
- API performance remains high (queries pre-aggregated data)
- Historical data preserved in cost-effective S3 storage
- Parquet format enables analytics tooling integration

---

## 4. MongoDB Collections

| Collection | Purpose |
|------------|---------|
| `expenses` | Raw expense/earning transactions |
| `investments` | Raw investment transactions (future) |
| `reports` | Monthly aggregated summaries |

---

## 5. Environment Variables

| Variable | Lambda | Description |
|----------|--------|-------------|
| `MONGODB_URI` | API, Batch | MongoDB Atlas connection string |
| `MONGODB_DATABASE` | API, Batch | Database name |
| `S3_BUCKET_NAME` | Batch | Archive bucket for Parquet files |

---

## 6. Lambda Functions

| Function | Description |
|----------|-------------|
| `lambda-home-api` | API Lambda (POST /expense, GET /report/expense) |
| `lambda-home-batch` | Batch Lambda (monthly aggregation + S3 export) |

## 7. Project Structure

See [01-architecture.md](./01-architecture.md) for complete project structure.

```
service/
├── api/           # API Lambda (POST /expense, GET /report/expense)
├── batch/         # Batch Lambda (monthly aggregation + S3 export)
├── shared/        # Shared code (models, database, config)
└── utils/         # Utility functions
```
