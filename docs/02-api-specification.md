# API Specification

## Base Configuration

| Property | Value |
|----------|-------|
| **API Type** | AWS API Gateway HTTP API |
| **Base URL** | `https://{api-id}.execute-api.{region}.amazonaws.com` |
| **Content-Type** | `application/json` |
| **Rate Limit** | 5 requests per second |
| **Daily Quota** | 100 requests per day |

---

## Endpoints

### POST /expense

Log a new expense or earning transaction.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount` | float | ✅ | Transaction amount (positive) |
| `category` | enum | ✅ | See category values below |
| `transaction_type` | enum | ✅ | `Credit` or `Debit` |
| `created_at` | string | ✅ | ISO 8601 datetime (`YYYY-MM-DDTHH:MM:SS`) |
| `recurring_payment` | boolean | ❌ | Whether this is a recurring payment (default: false) |

#### Category Values

`Groceries`, `EatOut`, `Transportation`, `Mortgage`, `Utilities`, `Shopping`, `Gas`, `Insurance`

#### Transaction Type Values

| Value | Meaning |
|-------|---------|
| `Credit` | Income / Earning |
| `Debit` | Expense / Spending |

#### Responses

| Status | Description |
|--------|-------------|
| `201 Created` | Expense created, returns `expense_id` |
| `422 Unprocessable Entity` | Validation error |

---

### GET /expense

List expenses in a date range with optional filters.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_date` | string | ✅ | Start date (`YYYY-MM-DD`) |
| `end_date` | string | ✅ | End date (`YYYY-MM-DD`) |
| `category` | enum | ❌ | Filter by category (omit for all) |
| `transaction_type` | enum | ❌ | `Credit` or `Debit` (omit for all) |
| `has_receipt` | boolean | ❌ | `true` for expenses with receipt, `false` for without (omit for all) |
| `min_amount` | float | ❌ | Minimum amount filter (inclusive) |
| `max_amount` | float | ❌ | Maximum amount filter (inclusive) |

#### Response

Array of expense objects (same shape as Expense):

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Expense id |
| `amount` | float | Amount |
| `category` | string | Category value |
| `transaction_type` | string | `Credit` or `Debit` |
| `created_at` | string | ISO 8601 datetime |
| `recurring_payment` | boolean | Whether this is a recurring payment |

#### Responses

| Status | Description |
|--------|-------------|
| `200 OK` | List of expenses (newest first) |
| `422 Unprocessable Entity` | Invalid date format, range, category, transaction_type, has_receipt, or amount values |

---

### PUT /expense/{id}

Update an existing expense by id.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Expense id (MongoDB ObjectId or string id) |

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount` | float | ✅ | Transaction amount (positive) |
| `category` | enum | ✅ | See category values below |
| `transaction_type` | enum | ✅ | `Credit` or `Debit` |
| `created_at` | string | ✅ | ISO 8601 datetime (`YYYY-MM-DDTHH:MM:SS` or with Z) |
| `merchant` | string | ❌ | Merchant name |
| `description` | string | ❌ | Description |
| `recurring_payment` | boolean | ❌ | Whether this is a recurring payment (default: false) |

#### Responses

| Status | Description |
|--------|-------------|
| `200 OK` | Expense updated, returns updated expense object |
| `404 Not Found` | Expense not found |
| `422 Unprocessable Entity` | Validation error |

---

### DELETE /expense/{id}

Delete an expense by id.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Expense id (MongoDB ObjectId or string id) |

#### Responses

| Status | Description |
|--------|-------------|
| `204 No Content` | Expense deleted |
| `404 Not Found` | Expense not found |

---

### GET /report/expense

Retrieve aggregated financial summary.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_date` | string | ✅ | Start date (`YYYY-MM-DD`) |
| `end_date` | string | ✅ | End date (`YYYY-MM-DD`) |
| `category` | enum | ❌ | Filter by category (omit for all) |

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `start_date` | string | Query start date |
| `end_date` | string | Query end date |
| `category_filter` | string | Applied category filter (or null) |
| `reports` | array | List of monthly reports |

#### Report Object

| Field | Type | Description |
|-------|------|-------------|
| `month` | string | Month (YYYY-MM) |
| `total_expense` | float | Sum of Debit transactions |
| `total_earning` | float | Sum of Credit transactions |
| `net` | float | total_earning - total_expense |
| `expense_by_category` | object | Breakdown by category |

#### Responses

| Status | Description |
|--------|-------------|
| `200 OK` | Returns reports (may be empty array) |
| `422 Unprocessable Entity` | Invalid date format or range |

---

### POST /investments (Future)

Log an investment transaction.

#### Request Body (Planned)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ticker` | string | ✅ | Stock/asset symbol |
| `asset_class` | enum | ✅ | Type of asset |
| `price` | float | ✅ | Price per unit |
| `quantity` | float | ✅ | Number of units |
| `transaction_type` | enum | ✅ | `Buy` or `Sell` |
| `transaction_date` | string | ✅ | Date (`YYYY-MM-DD`) |
| `broker_account` | string | ❌ | Broker identifier |

---

## Error Responses

### Format

| Field | Type | Description |
|-------|------|-------------|
| `statusCode` | int | HTTP status code |
| `message` | string | Error description |

### Status Codes

| Code | Meaning |
|------|---------|
| `200` | OK |
| `201` | Created |
| `400` | Bad Request |
| `422` | Validation Error |
| `500` | Internal Server Error |
