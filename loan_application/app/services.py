"""
services.py
-----------
Business logic layer: eligibility checks, interest rate assignment,
EMI calculation, and loan summary computation.
No direct DB calls here – those go in crud.py.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app import crud, models


# ─── Loan Eligibility & Calculation ─────────────────────────────────────────

RATE_BY_TENURE = {
    12: Decimal("10.00"),
    24: Decimal("11.00"),
    36: Decimal("12.00"),
    48: Decimal("13.00"),
    60: Decimal("13.00"),
}

MAX_ACTIVE_LOANS = 2
MAX_INCOME_MULTIPLIER = Decimal("20")
MIN_AGE = 21
MAX_AGE = 60


def _calculate_age(dob: date, as_of: date) -> int:
    """Return age in full years as of as_of date."""
    age = as_of.year - dob.year
    # Subtract 1 if birthday hasn't occurred yet this year
    if (as_of.month, as_of.day) < (dob.month, dob.day):
        age -= 1
    return age


def _calculate_emi(principal: Decimal, annual_rate: Decimal, tenure_months: int) -> Decimal:
    """
    Standard reducing-balance EMI formula:
        EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    where r = annual_rate / 12 / 100
    """
    r = annual_rate / Decimal("12") / Decimal("100")
    n = tenure_months
    factor = (1 + r) ** n
    emi = principal * r * factor / (factor - 1)
    return emi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def evaluate_loan(
    db: Session,
    customer: models.Customer,
    amount: Decimal,
    tenure_months: int,
) -> Tuple[str, Optional[str], Decimal, Optional[Decimal]]:
    """
    Evaluate loan eligibility for the given customer.

    Returns a tuple of:
        (status, rejection_reason, interest_rate, emi)

    status is "APPROVED" or "REJECTED".
    rejection_reason is None when approved.
    emi is None when rejected.
    """
    today = date.today()
    interest_rate = RATE_BY_TENURE[tenure_months]

    # 1. Age check
    age = _calculate_age(customer.date_of_birth, today)
    if not (MIN_AGE <= age <= MAX_AGE):
        return (
            "REJECTED",
            "age must be between 21 and 60",
            interest_rate,
            None,
        )

    # 2. Income check
    max_allowed = customer.monthly_income * MAX_INCOME_MULTIPLIER
    if amount > max_allowed:
        return (
            "REJECTED",
            "requested amount exceeds 20x monthly income",
            interest_rate,
            None,
        )

    # 3. Active loan count check
    active_count = crud.count_approved_loans(db, customer.id)
    if active_count >= MAX_ACTIVE_LOANS:
        return (
            "REJECTED",
            "the customer already has 2 active loans",
            interest_rate,
            None,
        )

    # All checks passed → APPROVED
    emi = _calculate_emi(amount, interest_rate, tenure_months)
    return ("APPROVED", None, interest_rate, emi)


# ─── Loan Summary Computation ────────────────────────────────────────────────

def compute_summary(db: Session, customer: models.Customer) -> dict:
    """Build the full loan summary dict for a customer."""
    all_loans = crud.get_loans_by_customer(db, customer.id)

    total_applications = len(all_loans)
    approved = [l for l in all_loans if l.status == models.LoanStatus.APPROVED]
    rejected = [l for l in all_loans if l.status == models.LoanStatus.REJECTED]

    approved_count = len(approved)
    rejected_count = len(rejected)

    total_approved_amount = sum(
        (l.amount for l in approved), Decimal("0")
    )
    total_monthly_emi = sum(
        (l.emi for l in approved if l.emi is not None), Decimal("0")
    )

    income = customer.monthly_income
    if income and income > 0:
        ratio = (total_monthly_emi / income * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        ratio = Decimal("0.00")

    if ratio < 30:
        risk_band = "LOW"
    elif ratio <= 50:
        risk_band = "MEDIUM"
    else:
        risk_band = "HIGH"

    return {
        "customer_id": customer.id,
        "customer_name": customer.name,
        "total_applications": total_applications,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "total_approved_amount": total_approved_amount.quantize(Decimal("0.01")),
        "total_monthly_emi": total_monthly_emi.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        "emi_to_income_ratio": ratio,
        "risk_band": risk_band,
    }
