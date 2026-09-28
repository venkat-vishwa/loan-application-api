"""
routers/loans.py
----------------
Endpoints:
  POST /api/loans       – Apply for a loan (API 3)
  GET  /api/loans/{id}  – Get a loan (API 4)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date

from app.database import get_db
from app import crud, models, schemas, services
from app.utils import (
    not_found,
    internal_error,
    validate_positive_id,
)

router = APIRouter(prefix="/api/loans", tags=["Loans"])


# ─── API 3: Apply for a Loan ─────────────────────────────────────────────────

@router.post("", status_code=201, response_model=schemas.LoanResponse)
def apply_loan(loan_in: schemas.LoanCreate, db: Session = Depends(get_db)):
    """
    Apply for a loan.
    Validates request, checks customer existence, runs eligibility rules,
    and saves the application (APPROVED or REJECTED) to the database.
    Returns HTTP 201 in both cases.
    Returns HTTP 404 if the customer does not exist.
    """
    # Check customer exists AFTER field validation (Pydantic ran first)
    customer = crud.get_customer_by_id(db, loan_in.customer_id)
    if not customer:
        raise not_found("Customer", loan_in.customer_id)

    status, rejection_reason, interest_rate, emi = services.evaluate_loan(
        db, customer, loan_in.amount, loan_in.tenure_months
    )

    loan_data = {
        "customer_id": loan_in.customer_id,
        "amount": loan_in.amount,
        "tenure_months": loan_in.tenure_months,
        "interest_rate": interest_rate,
        "emi": emi,
        "status": models.LoanStatus(status),
        "rejection_reason": rejection_reason,
        "applied_on": date.today(),
    }

    try:
        saved = crud.create_loan(db, loan_data)
    except Exception:
        db.rollback()
        raise internal_error()

    return saved


# ─── API 4: Get a Loan ───────────────────────────────────────────────────────

@router.get("/{id}", response_model=schemas.LoanResponse)
def get_loan(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single loan by ID.
    Returns HTTP 400 for non-positive IDs and HTTP 404 if not found.
    """
    validate_positive_id(id, "id")
    loan = crud.get_loan_by_id(db, id)
    if not loan:
        raise not_found("Loan", id)
    return loan
