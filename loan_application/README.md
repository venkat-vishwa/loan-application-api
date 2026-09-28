# Loan Application Management REST API

A beginner-friendly REST API built with **FastAPI**, **SQLAlchemy**, and **MySQL** for registering customers and managing loan applications. Designed to be clean, modular, and easy to explain in a technical interview.

---

## Features

- Register customers with full validation
- Apply for loans with automated eligibility checks
- Auto-calculated interest rates and EMI (reducing-balance formula)
- Loan summary with risk band computation
- All errors returned as structured JSON (never raw tracebacks)
- In-memory SQLite test database (no MySQL needed for tests)

---

## Project Structure

```
loan_application/
├── app/
│   ├── __init__.py
│   ├── main.py        # FastAPI app, exception handlers, middleware
│   ├── database.py    # SQLAlchemy engine & session
│   ├── models.py      # ORM table definitions
│   ├── schemas.py     # Pydantic request/response models
│   ├── crud.py        # Database operations
│   ├── services.py    # Business logic (eligibility, EMI)
│   ├── utils.py       # Shared HTTP error helpers
│   └── routers/
│       ├── __init__.py
│       ├── customers.py  # APIs 1, 2, 5, 6
│       └── loans.py      # APIs 3, 4
├── tests/
│   ├── __init__.py
│   ├── conftest.py       # Fixtures (SQLite in-memory DB)
│   ├── test_customers.py
│   └── test_loans.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Prerequisites

- Python 3.11 or newer
- MySQL 8.0 or newer (for running the server; not needed for tests)
- `uv` (recommended) or `pip` for package management

---

## Setup Instructions (Windows)

### 1. Clone or navigate to the project directory

```powershell
cd n:\interview\loan_application
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Or with `uv`:
```powershell
uv venv
.venv\Scripts\activate
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

Or with `uv`:
```powershell
uv pip install -r requirements.txt
```

---

## MySQL Setup

### Install MySQL

Download MySQL Community Server from https://dev.mysql.com/downloads/mysql/ and install it.

### Create the database and user

Log in to MySQL as root:

```bash
mysql -u root -p
```

Run these SQL commands:

```sql
CREATE DATABASE loan_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Optional: create a dedicated user (recommended for production)
CREATE USER 'loan_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON loan_db.* TO 'loan_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

---

## Environment Configuration

Copy the example file and fill in your credentials:

```powershell
copy .env.example .env
```

Edit `.env`:

```env
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=loan_db
```

> **Never commit `.env` to version control.** It is already in `.gitignore`.

The tables are created automatically when you start the server.

---

## Running the Server

```powershell
cd n:\interview\loan_application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: http://localhost:8000

### Interactive API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc:       http://localhost:8000/redoc

---

## API Reference

### API 1 – Register a Customer

```
POST /api/customers
Content-Type: application/json

{
  "name": "Priya Raman",
  "email": "priya@example.com",
  "phone": "1234567890",
  "date_of_birth": "1998-04-15",
  "monthly_income": 45000
}
```

Response `201`:
```json
{
  "id": 1,
  "name": "Priya Raman",
  "email": "priya@example.com",
  "phone": "1234567890",
  "date_of_birth": "1998-04-15",
  "monthly_income": 45000
}
```

---

### API 2 – Get a Customer

```
GET /api/customers/{id}
```

Response `200`: same format as above.  
Response `404` if not found.

---

### API 3 – Apply for a Loan

```
POST /api/loans
Content-Type: application/json

{
  "customer_id": 1,
  "amount": 300000,
  "tenure_months": 36
}
```

Response `201` (approved):
```json
{
  "id": 7,
  "customer_id": 1,
  "amount": 300000,
  "tenure_months": 36,
  "interest_rate": 12.0,
  "emi": 9964.29,
  "status": "APPROVED",
  "rejection_reason": null,
  "applied_on": "2026-09-28"
}
```

Response `201` (rejected):
```json
{
  "id": 8,
  "customer_id": 1,
  "amount": 5000000,
  "tenure_months": 36,
  "interest_rate": 12.0,
  "emi": null,
  "status": "REJECTED",
  "rejection_reason": "requested amount exceeds 20x monthly income",
  "applied_on": "2026-09-28"
}
```

**Eligibility rules checked in order:**
1. Age must be 21–60
2. Amount ≤ 20× monthly income
3. Fewer than 2 existing approved loans

**Interest rates by tenure:**

| Tenure (months) | Annual Rate |
|-----------------|-------------|
| 12              | 10%         |
| 24              | 11%         |
| 36              | 12%         |
| 48              | 13%         |
| 60              | 13%         |

---

### API 4 – Get a Loan

```
GET /api/loans/{id}
```

---

### API 5 – List Customer Loans

```
GET /api/customers/{id}/loans
GET /api/customers/{id}/loans?status=APPROVED
GET /api/customers/{id}/loans?status=REJECTED
```

Returns newest-first array. Empty array `[]` if no loans match.

---

### API 6 – Customer Loan Summary

```
GET /api/customers/{id}/summary
```

Response `200`:
```json
{
  "customer_id": 1,
  "customer_name": "Priya Raman",
  "total_applications": 3,
  "approved_count": 2,
  "rejected_count": 1,
  "total_approved_amount": 500000,
  "total_monthly_emi": 15420.55,
  "emi_to_income_ratio": 34.27,
  "risk_band": "MEDIUM"
}
```

**Risk bands:**
- `LOW` – ratio < 30
- `MEDIUM` – ratio 30–50
- `HIGH` – ratio > 50

---

## Error Response Format

```json
{
  "error": "VALIDATION_FAILED",
  "details": [
    { "field": "email", "message": "must be a valid email address" }
  ]
}
```

| HTTP Status | `error` value       | Cause                         |
|-------------|---------------------|-------------------------------|
| 400         | `VALIDATION_FAILED` | Field validation failures     |
| 400         | `INVALID_REQUEST`   | Empty body or malformed JSON  |
| 404         | `NOT_FOUND`         | Resource doesn't exist        |
| 409         | `DUPLICATE_EMAIL`   | Email already registered      |
| 500         | `INTERNAL_ERROR`    | Unexpected server error       |

---

## Running Tests

Tests use an in-memory SQLite database. **No MySQL connection is required.**

```powershell
cd n:\interview\loan_application
pytest tests/ -v
```

---

## Git Setup & GitHub Push

```powershell
cd n:\interview\loan_application
git init
git add .
git commit -m "Initial commit: Loan Application Management API"

# Create repo on GitHub, then:
git remote add origin https://github.com/<your-username>/loan-application-api.git
git branch -M main
git push -u origin main
```

> ⚠️ Make sure `.env` is **never** committed. Verify with `git status`.

---

## Technology Stack

| Component        | Library / Tool       |
|------------------|----------------------|
| Web framework    | FastAPI              |
| ASGI server      | Uvicorn              |
| ORM              | SQLAlchemy 2.x       |
| Database         | MySQL + PyMySQL      |
| Validation       | Pydantic v2          |
| Testing          | pytest + httpx       |
| Config           | python-dotenv        |
