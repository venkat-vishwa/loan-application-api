"""
database.py
-----------
Sets up the SQLAlchemy engine and session factory.
Reads database connection details from environment variables via .env.
Connects to Oracle Database using the python-oracledb driver (thin mode).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "loan_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "1521")
DB_SERVICE_NAME = os.getenv("DB_SERVICE_NAME", "FREEPDB1")

# oracle+oracledb uses the python-oracledb driver in thin mode (no Oracle Client needed).
# The service name is supplied via the ?service_name= query parameter.
DATABASE_URL = (
    f"oracle+oracledb://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/?service_name={DB_SERVICE_NAME}"
)

# echo=False keeps SQL out of logs (never expose SQL to clients)
engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that yields a DB session and always closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
