"""
schemas.py
----------
Pydantic models used for request validation and response serialization.
All validation logic that Pydantic can handle lives here.
"""
import re
from datetime import date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from app.models import LoanStatus

VALID_TENURES = {12, 24, 36, 48, 60}


# ─── Customer Schemas ───────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    date_of_birth: date
    monthly_income: Decimal

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not (3 <= len(v) <= 50):
            raise ValueError("must be between 3 and 50 characters")
        if not re.fullmatch(r"[A-Za-z ]+", v):
            raise ValueError("must contain only letters and spaces")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"\d{10}", v):
            raise ValueError("must contain exactly 10 digits")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("cannot be a future date")
        return v

    @field_validator("monthly_income")
    @classmethod
    def validate_income(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("must be greater than zero")
        return v

    model_config = {"json_schema_extra": {"example": {
        "name": "Priya Raman",
        "email": "priya@example.com",
        "phone": "1234567890",
        "date_of_birth": "1998-04-15",
        "monthly_income": 45000,
    }}}


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    date_of_birth: date
    monthly_income: Decimal

    model_config = {"from_attributes": True}


# ─── Loan Schemas ────────────────────────────────────────────────────────────

class LoanCreate(BaseModel):
    customer_id: int
    amount: Decimal
    tenure_months: int

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("must be a positive integer")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if not (Decimal("10000") <= v <= Decimal("5000000")):
            raise ValueError("must be between 10,000 and 5,000,000 inclusive")
        return v

    @field_validator("tenure_months")
    @classmethod
    def validate_tenure(cls, v: int) -> int:
        if v not in VALID_TENURES:
            raise ValueError("must be one of 12, 24, 36, 48, or 60")
        return v

    model_config = {"json_schema_extra": {"example": {
        "customer_id": 1,
        "amount": 300000,
        "tenure_months": 36,
    }}}


class LoanResponse(BaseModel):
    id: int
    customer_id: int
    amount: Decimal
    tenure_months: int
    interest_rate: Decimal
    emi: Optional[Decimal]
    status: LoanStatus
    rejection_reason: Optional[str]
    applied_on: date

    model_config = {"from_attributes": True}


# ─── Summary Schema ──────────────────────────────────────────────────────────

class CustomerSummary(BaseModel):
    customer_id: int
    customer_name: str
    total_applications: int
    approved_count: int
    rejected_count: int
    total_approved_amount: Decimal
    total_monthly_emi: Decimal
    emi_to_income_ratio: Decimal
    risk_band: str


# ─── Error Schemas ───────────────────────────────────────────────────────────

class ValidationDetail(BaseModel):
    field: str
    message: str


class ValidationErrorResponse(BaseModel):
    error: str = "VALIDATION_FAILED"
    details: List[ValidationDetail]
