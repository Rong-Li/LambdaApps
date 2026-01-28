# Data Models

## Overview

All data models are defined using **Pydantic v2** for validation and serialization. Models are shared between the API and batch Lambda functions.

---

## Enums

### Category

| Value | Description |
|-------|-------------|
| `Groceries` | Grocery shopping |
| `EatOut` | Restaurants, takeout |
| `Transportation` | Public transit, rideshare |
| `Mortgage` | Home mortgage payments |
| `Utilities` | Electric, water, internet |
| `Shopping` | General shopping |
| `Gas` | Fuel for vehicles |
| `Insurance` | Insurance premiums |

### TransactionType

| Value | Description |
|-------|-------------|
| `Credit` | Income / Earning |
| `Debit` | Expense / Spending |

---

## Expense Model

### Schema: `ExpenseInput`

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `amount` | PositiveAmount | ✅ | > 0, rounded to 2 decimals | Transaction amount |
| `category` | Category | ✅ | Valid enum value | Expense category |
| `transaction_type` | TransactionType | ✅ | Credit or Debit | Transaction type |
| `created_at` | datetime | ✅ | ISO 8601 datetime | Transaction timestamp |

### Schema: `Expense` (extends ExpenseInput)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | MongoDB ObjectId (aliased from `_id`) |

### MongoDB Collection: `expenses`

| Field | Type | Index | Description |
|-------|------|-------|-------------|
| `_id` | ObjectId | Primary | Auto-generated |
| `amount` | Double | - | Transaction amount |
| `category` | String | ✅ | Category enum value |
| `transaction_type` | String | ✅ | Credit or Debit |
| `created_at` | Date | ✅ | Transaction timestamp |

### Recommended Indexes

- `{ "created_at": 1 }`
- `{ "category": 1 }`
- `{ "transaction_type": 1 }`
- `{ "created_at": 1, "category": 1 }` (compound)

---

## Report Model

### Schema: `Report`

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `month` | string | ✅ | Format: YYYY-MM | Month identifier |
| `total_expense` | float | ✅ | >= 0 | Sum of all Debit transactions |
| `total_earning` | float | ✅ | >= 0 | Sum of all Credit transactions |
| `expense_by_category` | dict | ✅ | Category → float | Breakdown by category |

### Computed Property

- `net`: `total_earning - total_expense`

### MongoDB Collection: `reports`

| Field | Type | Index | Description |
|-------|------|-------|-------------|
| `_id` | ObjectId | Primary | Auto-generated |
| `month` | String | ✅ Unique | YYYY-MM format |
| `total_expense` | Double | - | Sum of Debit transactions |
| `total_earning` | Double | - | Sum of Credit transactions |
| `expense_by_category` | Object | - | Breakdown by category |
| `created_at` | Date | - | Record creation timestamp |
| `updated_at` | Date | - | Last update timestamp |

### Recommended Indexes

- `{ "month": 1 }` (unique)

---

## Investment Model (Future)

### Enums (Planned)

**AssetClass:** Stock, Etf, Bond, Crypto, MutualFund, Reit

**InvestmentTransactionType:** Buy, Sell

### Schema: `InvestmentCreate` (Planned)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ticker` | string | ✅ | Stock/asset symbol (1-10 chars) |
| `asset_class` | AssetClass | ✅ | Type of asset |
| `price` | float | ✅ | Price per unit (> 0) |
| `quantity` | float | ✅ | Number of units (> 0) |
| `transaction_type` | InvestmentTransactionType | ✅ | Buy or Sell |
| `transaction_date` | date | ✅ | Transaction date |
| `broker_account` | string | ❌ | Broker identifier (max 100 chars) |

### MongoDB Collection: `investments` (Planned)

| Field | Type | Index | Description |
|-------|------|-------|-------------|
| `_id` | ObjectId | Primary | Auto-generated |
| `ticker` | String | ✅ | Stock/asset symbol |
| `asset_class` | String | ✅ | Asset classification |
| `price` | Double | - | Price per unit |
| `quantity` | Double | - | Number of units |
| `transaction_type` | String | - | Buy or Sell |
| `transaction_date` | Date | ✅ | Transaction date |
| `broker_account` | String | - | Broker identifier |
| `created_at` | Date | - | Record creation timestamp |

---

## API Response Models

### ExpenseCreateResponse

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | "Expense created successfully" |
| `expense_id` | string | MongoDB ObjectId |

### ReportExpenseResponse

| Field | Type | Description |
|-------|------|-------------|
| `start_date` | date | Query start date |
| `end_date` | date | Query end date |
| `category_filter` | Category | Optional category filter |
| `reports` | List[Report] | List of monthly reports |
| `message` | string | Optional status message |

### ErrorResponse

| Field | Type | Description |
|-------|------|-------------|
| `statusCode` | int | HTTP status code |
| `message` | string | Error description |
