# homeapp

Personal Finance Tracker - Serverless backend for expense tracking and reporting.

## Overview

A serverless backend built on AWS Lambda for logging expenses and investments, with monthly batch processing for data aggregation and archival.

## Tech Stack

- **Language**: Python 3.14+ (managed by `uv`)
- **API Framework**: AWS Lambda Powertools
- **Data Validation**: Pydantic v2
- **Database**: MongoDB Atlas (PyMongo)
- **Storage**: S3 (Parquet archives via Polars)
- **CI/CD**: GitHub Actions (OIDC)

## Project Structure

```
├── service/
│   ├── api/          # API Lambda (POST /expense, GET /report/expense)
│   ├── batch/        # Batch Lambda (monthly aggregation + S3 export)
│   ├── shared/       # Shared models, config, database
│   └── utils/        # Utility functions
├── tests/            # pytest test suite
├── docs/             # Documentation
└── pyproject.toml    # Dependencies (uv)
```

## Lambda Functions

| Function | Layer | Purpose |
|----------|-------|---------|
| `HomeApp-LambdaFunction-APIs` | `homeapp-api-layer` | REST API for expenses and reports |
| `HomeApp-LambdaFunction-Batch` | `homeapp-batch-layer` | Monthly aggregation (1st of month, Toronto ET) |

## API Endpoints

- `POST /expense` - Log expense/earning transaction
- `GET /report/expense` - Get aggregated reports

## Development

### Setup

```bash
# Install dependencies
uv sync --dev

# Set environment variables
export MONGODB_URI="mongodb+srv://..."
export MONGODB_DATABASE="homeapp"
export S3_BUCKET_NAME="homeapp-archive"
```

### Run Tests

```bash
uv run pytest
```

### Run Linter

```bash
uv run ruff check service/
```

## Documentation

See [docs/](./docs/) for detailed documentation:

- [Architecture](./docs/01-architecture.md)
- [API Specification](./docs/02-api-specification.md)
- [Data Models](./docs/03-data-models.md)
- [Batch Job](./docs/04-batch-job.md)
- [Deployment](./docs/05-deployment.md)
- [Testing](./docs/06-testing.md)
