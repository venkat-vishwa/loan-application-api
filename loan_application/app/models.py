"""
models.py
---------
SQLAlchemy ORM models that map to the Oracle Database tables.

Oracle-specific adjustments vs. the original MySQL version:
  - Sequences are used for auto-incrementing PKs (Oracle standard; SQLAlchemy
    handles this automatically when autoincrement=True with Oracle dialect).
  - SAEnum is rendered as VARCHAR2 on Oracle because Oracle has no native ENUM
    type; the CHECK constraint is handled at the application layer.
  - String lengths map to VARCHAR2 on Oracle (e.g. String(50) → VARCHAR2(50)).
  - DECIMAL maps to Oracle NUMBER(p, s) transparently via SQLAlchemy.
"""
from sqlalchemy import (
    Column, Integer, String, Date, DECIMAL, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class LoanStatus(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(10), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    monthly_income = Column(DECIMAL(15, 2), nullable=False)

    loans = relationship("Loan", back_populates="customer")


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False)
    tenure_months = Column(Integer, nullable=False)
    interest_rate = Column(DECIMAL(5, 2), nullable=False)
    emi = Column(DECIMAL(15, 2), nullable=True)
    status = Column(
        SAEnum(LoanStatus, create_constraint=True, name="loan_status_enum"),
        nullable=False,
    )
    rejection_reason = Column(String(255), nullable=True)
    applied_on = Column(Date, nullable=False)

    customer = relationship("Customer", back_populates="loans")
