"""
Configuration module to load db url from the .env file

"""

#dataclass is a decorator that automatically generates special methods like __init__() and __repr__() for classes
from dataclasses import dataclass

#path oo file system path module used to locate the .env file
from pathlib import Path

#os module provides a way of using operating system dependent functionality like reading or writing to the file
import os

#read .env and load environment variables
from typing import Optional
from dotenv import load_dotenv

#read the env from project root
ENV_PATH_ROOT = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH_ROOT)


def _as_bool(val: Optional[str], default: bool = False) -> bool:
    """
    Convert common string representations to a boolean.

    Accepts: "1", "true", "yes", "on" (case-insensitive) as True.
    Anything else returns False (or the provided default if val is None).
    """
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """
    Typed container for configuration.

    frozen=True makes instances immutable (safer: config can't be changed accidentally).
    Fields map directly to environment variables and have sensible defaults.
    """
    database_url: str
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800
    pool_pre_ping: bool = True


def get_settings() -> Settings:
    """
    Build a Settings object from environment variables.

    Steps:
    - Read DATABASE_URL (required). If it starts with "postgresql://", normalize it to
      "postgresql+psycopg://" so SQLAlchemy uses psycopg v3 explicitly.
    - Parse optional tuning knobs for the SQLAlchemy connection pool.
    - Return a Settings instance for the rest of the app to use.

    Notes:
    - Psycopg is the PostgreSQL driver. SQLAlchemy builds queries; psycopg sends them
      over the network to the database.
      URL format: postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
      Docs: https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Add it to ticketing/.env or your environment."
        )

    # Normalize a plain "postgresql://" URL to explicitly use the psycopg v3 driver.
    # This avoids ambiguity and ensures the modern driver is used.
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    return Settings(
        database_url=url,
        echo=_as_bool(os.getenv("SQL_ECHO"), False),
        pool_size=int(os.getenv("SQL_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("SQL_MAX_OVERFLOW", "10")),
        pool_timeout=int(os.getenv("SQL_POOL_TIMEOUT", "30")),
        pool_recycle=int(os.getenv("SQL_POOL_RECYCLE", "1800")),
        pool_pre_ping=True,
    )