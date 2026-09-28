"""
utils.py
--------
Shared helper functions for raising standardised HTTP error responses.
Import from here in routers so error formats stay consistent.
"""
from fastapi import HTTPException
from typing import List, Dict


def bad_request(error: str, details: List[Dict]) -> HTTPException:
    """Return a 400 HTTPException with the standard validation error body."""
    return HTTPException(
        status_code=400,
        detail={"error": error, "details": details},
    )


def not_found(entity: str, entity_id: int) -> HTTPException:
    """Return a 404 HTTPException."""
    return HTTPException(
        status_code=404,
        detail={
            "error": "NOT_FOUND",
            "message": f"{entity} with id {entity_id} not found",
        },
    )


def duplicate_email_error() -> HTTPException:
    """Return a 409 HTTPException for duplicate email."""
    return HTTPException(
        status_code=409,
        detail={"error": "DUPLICATE_EMAIL"},
    )


def internal_error() -> HTTPException:
    """Return a 500 HTTPException without exposing internals."""
    return HTTPException(
        status_code=500,
        detail={"error": "INTERNAL_ERROR"},
    )


def validate_positive_id(value: int, field: str) -> None:
    """Raise 400 if `value` is not a positive integer."""
    if value <= 0:
        raise bad_request(
            "VALIDATION_FAILED",
            [{"field": field, "message": "must be a positive integer"}],
        )
