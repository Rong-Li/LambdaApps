# Testing Guide

## Overview

homeapp uses **pytest** for unit and integration testing.

---

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── unit/
│   ├── __init__.py
│   ├── test_models.py       # Pydantic model tests
│   ├── test_expenses.py     # Expense route tests
│   ├── test_report.py       # Report route tests
│   └── test_batch.py        # Batch job logic tests
└── integration/
    ├── __init__.py
    └── test_database.py     # MongoDB integration tests
```

---

## Running Tests

| Command | Description |
|---------|-------------|
| `uv run pytest` | Run all tests |
| `uv run pytest -v` | Verbose output |
| `uv run pytest tests/unit/` | Unit tests only |
| `uv run pytest tests/unit/test_models.py` | Specific file |
| `uv run pytest -m integration` | Integration tests only |
| `uv run pytest -m "not slow"` | Skip slow tests |

---

## Test Coverage

### Running Coverage

```bash
uv run pytest --cov=service --cov-report=html --cov-report=term-missing
```

### Target Coverage

**80%+** code coverage

---

## Test Categories

### Unit Tests

#### Model Tests (`test_models.py`)

| Test | Description |
|------|-------------|
| Valid expense creation | All required fields, valid values |
| Amount must be positive | Reject negative amounts |
| Amount rounding | Round to 2 decimal places |
| Invalid category | Reject unknown category values |
| Invalid datetime format | Reject non-ISO datetime formats |
| Category enum values | All 8 categories exist |
| Transaction type values | Credit and Debit exist |

#### Expense Route Tests (`test_expenses.py`)

| Test | Description |
|------|-------------|
| Create expense success | Returns 201 with expense_id |
| Invalid amount | Returns 422 for negative amount |
| Invalid category | Returns 422 for unknown category |
| Missing required field | Returns 422 for incomplete data |
| Amount rounding | Verifies amount rounded to 2 decimals |

#### Report Route Tests (`test_report.py`)

| Test | Description |
|------|-------------|
| Get report success | Returns 200 with reports array |
| Category filter | Filters by specified category |
| Missing dates | Returns 422 when dates missing |
| Invalid date range | Returns error when end < start |

#### Batch Job Tests (`test_batch.py`)

| Test | Description |
|------|-------------|
| Previous month calculation | Correct start/end dates |
| Aggregation basic | Correct totals and category breakdown |
| Aggregation empty list | Handles no expenses |
| Aggregation credits only | Handles income-only month |
| Report upsert | Creates/updates report correctly |
| Handler success | Full batch execution flow |

### Integration Tests

#### Database Tests (`test_database.py`)

| Test | Description |
|------|-------------|
| Insert and retrieve expense | MongoDB CRUD operations |
| Query by date range | Date filtering works |
| Upsert report | Idempotent report updates |

---

## Fixtures

### Sample Data

| Fixture | Description |
|---------|-------------|
| `sample_expense_data` | Valid expense request JSON |
| `sample_expense_document` | Expense as stored in MongoDB |
| `sample_report_document` | Report as stored in MongoDB |
| `multiple_expenses` | List for aggregation testing |

### Mocks

| Fixture | Description |
|---------|-------------|
| `mock_db` | Mock MongoDB database |
| `mock_s3_client` | Mock S3 client |
| `api_gateway_event` | Factory for API Gateway events |
| `lambda_context` | Mock Lambda context |

---

## Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.integration` | Integration tests (require external services) |
| `@pytest.mark.slow` | Slow-running tests |

---

## Required Dev Dependencies

| Package | Purpose |
|---------|---------|
| `pytest>=8.0.0` | Test framework |
| `pytest-cov>=4.1.0` | Coverage reporting |
| `freezegun>=1.2.0` | Time mocking |
| `pytest-mock>=3.12.0` | Mock utilities |

---

## CI Integration

Tests run automatically in GitHub Actions on every push:
- PR blocked if tests fail
- Coverage report in Actions summary

---

## Environment Variables for Integration Tests

| Variable | Description |
|----------|-------------|
| `MONGODB_TEST_URI` | Test database connection string |

Test database: `homeapp_test` (dropped after tests)
