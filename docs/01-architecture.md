# Architecture Overview

## System Context

homeapp is a serverless personal finance tracking backend built on AWS Lambda. It provides REST APIs for logging expenses and retrieving financial summaries, with a monthly batch process for data aggregation and archival.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Client App    │────▶│  API Gateway     │────▶│  Lambda (API)   │
│  (Future/Web)   │     │  (HTTP API)      │     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   EventBridge   │────▶│  Lambda (Batch)  │────▶│  MongoDB Atlas  │
│   (Scheduler)   │     │                  │     │                 │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   S3 Bucket     │
                        │  (Parquet)      │
                        └─────────────────┘
```

---

## Lambda Functions

| Function | Purpose | Trigger |
|----------|---------|---------|
| `lambda-home-api` | REST API (expenses, reports) | API Gateway HTTP API |
| `lambda-home-batch` | Monthly aggregation & S3 archival | EventBridge (1st of month, Toronto ET) |

---

## Shared Code

Both Lambda functions share:
- MongoDB connection management
- Pydantic data models
- Configuration & environment handling
- Utility functions

---

## AWS Services

| Service | Usage |
|---------|-------|
| **Lambda** | Compute for API and batch processing |
| **API Gateway (HTTP API)** | REST API (rate: 5/sec, quota: 100/day) |
| **EventBridge Scheduler** | Monthly batch trigger |
| **S3** | Parquet storage for transaction archival |
| **Lambda Layer** | Shared dependencies |

---

## External Services

| Service | Usage |
|---------|-------|
| **MongoDB Atlas** | Primary database (database: `homeapp`) |

---

## Project Structure

```
LambdaApps/
├── service/
│   ├── api/                    # API Lambda
│   │   ├── handler.py          # Entry point
│   │   └── routes/
│   │       ├── expenses.py     # POST /expenses
│   │       └── report.py       # GET /report/expense
│   │
│   ├── batch/                  # Batch Lambda
│   │   └── handler.py          # Entry point
│   │
│   ├── shared/                 # Shared code
│   │   ├── config.py           # Configuration
│   │   ├── database.py         # MongoDB connection
│   │   └── models/             # Pydantic models
│   │
│   └── utils/                  # Utilities
│
├── tests/                      # pytest tests
├── Docs/                       # Documentation
├── .github/workflows/          # CI/CD
├── pyproject.toml              # Dependencies (uv)
└── build_lambda_layer.sh       # Layer build script
```

---

## Data Flows

### Expense Logging

1. Client → POST /expenses with JSON
2. API Gateway → lambda-home-api
3. Validate via Pydantic
4. Insert to MongoDB `expenses` collection
5. Return 201 with expense_id

### Report Query

1. Client → GET /report/expense with query params
2. API Gateway → lambda-home-api
3. Query MongoDB `reports` collection
4. Return aggregated data

### Monthly Batch

1. EventBridge triggers lambda-home-batch (1st of month, 00:00 Toronto ET)
2. Fetch previous month's expenses
3. Aggregate: total expense, category breakdown, total earning
4. Upsert to MongoDB `reports` collection
5. Export to S3: `transactions/{YYYY}/{YYYY-MM}.parquet`

---

## Security

- MongoDB connection string in Lambda environment (encrypted)
- S3 bucket with server-side encryption
- Lambda execution role with least-privilege
- API Gateway extensible with auth (future)

---

## Scalability

- Lambda auto-scales with request volume
- MongoDB Atlas handles connection pooling
- S3 provides unlimited archive storage
