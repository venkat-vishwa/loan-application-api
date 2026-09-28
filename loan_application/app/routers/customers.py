"""
routers/customers.py
---------------------
Endpoints:
  POST   /api/customers          – Register a customer (API 1)
  GET    /api/customers/{id}     – Get a customer (API 2)
  GET    /api/customers/{id}/loans   – List customer loans (API 5)
  GET    /api/customers/{id}/summary – Customer loan summary (API 6)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List

from app.database import get_db
from app import crud, models, schemas, services
from app.utils import (
    bad_request,
    not_found,
    duplicate_email_error,
    internal_error,
    validate_positive_id,
)

router = APIRouter(prefix="/api/customers", tags=["Customers"])


# ─── API 1: Register a Customer ──────────────────────────────────────────────

@router.post("", status_code=201, response_model=schemas.CustomerResponse)
def register_customer(
    customer_in: schemas.CustomerCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new customer.
    Returns HTTP 201 on success.
    Returns HTTP 409 if email already exists.
    """
    try:
        saved = crud.create_customer(db, customer_in.model_dump())
    except IntegrityError:
        db.rollback()
        raise duplicate_email_error()
    except Exception:
        db.rollback()
        raise internal_error()

    return saved


# ─── API 2: Get a Customer ───────────────────────────────────────────────────

@router.get("/{id}", response_model=schemas.CustomerResponse)
def get_customer(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single customer by ID.
    Returns HTTP 400 for non-positive IDs and HTTP 404 if not found.
    """
    validate_positive_id(id, "id")
    customer = crud.get_customer_by_id(db, id)
    if not customer:
        raise not_found("Customer", id)
    return customer


# ─── API 5: List Customer Loans ──────────────────────────────────────────────

@router.get("/{id}/loans", response_model=List[schemas.LoanResponse])
def list_customer_loans(
    id: int,
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    List all loans for a customer, newest first.
    Supports optional ?status=APPROVED|REJECTED filter.
    Returns HTTP 400 for invalid status values.
    Returns HTTP 404 if the customer does not exist.
    """
    validate_positive_id(id, "id")

    # Validate the status query param when provided
    status_enum = None
    if status is not None:
        try:
            status_enum = models.LoanStatus(status.upper())
        except ValueError:
            raise bad_request(
                "VALIDATION_FAILED",
                [{"field": "status", "message": "must be APPROVED or REJECTED"}],
            )

    customer = crud.get_customer_by_id(db, id)
    if not customer:
        raise not_found("Customer", id)

    loans = crud.get_loans_by_customer(db, id, status_enum)
    return loans


# ─── API 6: Customer Loan Summary ────────────────────────────────────────────

@router.get("/{id}/summary", response_model=schemas.CustomerSummary)
def customer_summary(id: int, db: Session = Depends(get_db)):
    """
    Return aggregate loan statistics for a customer.
    Returns HTTP 404 if the customer does not exist.
    """
    validate_positive_id(id, "id")
    customer = crud.get_customer_by_id(db, id)
    if not customer:
        raise not_found("Customer", id)

    summary = services.compute_summary(db, customer)
    return summary
