"""
crud.py
-------
All direct database operations (Create, Read, Update, Delete).
These functions receive a SQLAlchemy Session and return ORM objects.
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from app import models


# ─── Customer CRUD ───────────────────────────────────────────────────────────

def create_customer(db: Session, customer_data: dict) -> models.Customer:
    """Insert a new customer row and return the saved ORM object."""
    customer = models.Customer(**customer_data)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def get_customer_by_id(db: Session, customer_id: int) -> Optional[models.Customer]:
    """Return the Customer with the given id, or None if not found."""
    return db.query(models.Customer).filter(models.Customer.id == customer_id).first()


def get_customer_by_email(db: Session, email: str) -> Optional[models.Customer]:
    """Return the Customer with the given email, or None."""
    return db.query(models.Customer).filter(models.Customer.email == email).first()


# ─── Loan CRUD ───────────────────────────────────────────────────────────────

def create_loan(db: Session, loan_data: dict) -> models.Loan:
    """Insert a new loan row and return the saved ORM object."""
    loan = models.Loan(**loan_data)
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


def get_loan_by_id(db: Session, loan_id: int) -> Optional[models.Loan]:
    """Return the Loan with the given id, or None."""
    return db.query(models.Loan).filter(models.Loan.id == loan_id).first()


def get_loans_by_customer(
    db: Session,
    customer_id: int,
    status: Optional[models.LoanStatus] = None,
) -> List[models.Loan]:
    """Return loans for a customer, newest first. Optionally filter by status."""
    query = (
        db.query(models.Loan)
        .filter(models.Loan.customer_id == customer_id)
        .order_by(desc(models.Loan.id))
    )
    if status is not None:
        query = query.filter(models.Loan.status == status)
    return query.all()


def count_approved_loans(db: Session, customer_id: int) -> int:
    """Count how many APPROVED loans the customer currently has."""
    return (
        db.query(models.Loan)
        .filter(
            models.Loan.customer_id == customer_id,
            models.Loan.status == models.LoanStatus.APPROVED,
        )
        .count()
    )
