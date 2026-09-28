"""
main.py
-------
FastAPI application factory.
Registers routers and global exception handlers.
"""
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

import app.database as _database
from app.database import Base
from app.routers import customers, loans


# ─── Lifespan: create tables on startup (skipped during tests via DB override) ─
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Use _database.engine so tests can monkey-patch it to SQLite
    Base.metadata.create_all(bind=_database.engine)
    yield


# ─── Application ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Loan Application Management API",
    description=(
        "A REST API for registering customers and managing loan applications. "
        "Built with FastAPI, SQLAlchemy, and Oracle Database."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Global Exception Handlers ───────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    """
    Override FastAPI's default 422 response.
    Collect ALL field errors and return HTTP 400 in the standard format.
    """
    details = []
    for error in exc.errors():
        # loc is a tuple like ('body', 'email'); skip 'body' prefix
        loc = error.get("loc", ())
        field = str(loc[-1]) if len(loc) > 1 else str(loc[0]) if loc else "unknown"
        msg = error.get("msg", "invalid value")
        # Clean up Pydantic's prefixed messages like "Value error, ..."
        msg = msg.replace("Value error, ", "").replace("value is not a valid email address", "must be a valid email address")
        details.append({"field": field, "message": msg})

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "VALIDATION_FAILED", "details": details},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return a safe 500 response."""
    # Let HTTPException pass through (FastAPI handles it separately)
    from fastapi.exceptions import HTTPException
    if isinstance(exc, HTTPException):
        raise exc
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR"},
    )


from fastapi.exceptions import HTTPException as _HTTPException

@app.exception_handler(_HTTPException)
async def http_exception_handler(request: Request, exc: _HTTPException):
    """
    Return the HTTPException detail dict directly as the JSON body.
    FastAPI's default handler wraps it in {"detail": ...}, which we don't want.
    """
    detail = exc.detail
    # If detail is already a dict (our custom format), return it directly
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
    # Fallback for any plain-string details
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(detail)},
    )


async def _body_is_empty_or_invalid(request: Request) -> bool:
    """Return True when the request body is missing or not valid JSON."""
    body = await request.body()
    if not body:
        return True
    try:
        json.loads(body)
        return False
    except json.JSONDecodeError:
        return True


@app.middleware("http")
async def check_json_body(request: Request, call_next):
    """
    For POST requests that expect a JSON body, reject empty or malformed
    JSON early with HTTP 400 INVALID_REQUEST.
    """
    if request.method == "POST" and "application/json" in request.headers.get(
        "content-type", ""
    ):
        body = await request.body()
        if not body:
            return JSONResponse(
                status_code=400,
                content={"error": "INVALID_REQUEST"},
            )
        try:
            json.loads(body)
        except json.JSONDecodeError:
            return JSONResponse(
                status_code=400,
                content={"error": "INVALID_REQUEST"},
            )
    return await call_next(request)


# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(customers.router)
app.include_router(loans.router)


# ─── Health check ────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
