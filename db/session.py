#Manages DB connections created by dburl
#session orm handle for transactions (query/insert/update/delete
#get_session() context manager that commits on success, rolls back on error)

from contextlib import contextmanager
from typing import Iterator, Dict, Any


#engine factory and raw sql helper
from sqlalchemy import create_engine, text

#session factory
from sqlalchemy.orm import sessionmaker, Session

#import setting from config
from config import get_settings

#shared base to create_all/drop_all 
from db.base import Base

#load settings
settings = get_settings()

# Creating the Engine (connection factory).
#    - echo=settings.echo → prints SQL if true
#    - pool_* → connection pool tuning (safe defaults for dev).
#    - pool_pre_ping=True → validates connections to avoid stale-connection errors.
#    - connect_args timezone=utc → run sessions in UTC (consistent timestamps).
engine = create_engine(
    settings.database_url,
    echo=settings.echo,
    pool_size=settings.pool_size,
    max_overflow=settings.max_overflow,
    pool_timeout=settings.pool_timeout,
    pool_recycle=settings.pool_recycle,
    pool_pre_ping=True,
    connect_args={"options": "-c timezone=utc"},
    future=True,  # Use SQLAlchemy 2.x behavior explicitly.
)

#  Buildintg  a Session factory.
#    - autoflush=False → you control when pending changes are flushed.
#    - autocommit=False → explicit commit/rollback (safer).
#    - expire_on_commit=False → objects remain usable after commit (nice for CLIs).
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
    future=True,
)

@contextmanager
def get_session() -> Iterator[Session]:
    #makes get_session as Session

    #commits if no exception: rolls back error, & always close session
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def create_all() -> None:
    """Create all tables in the database. Uses metadata from Base."""
    Base.metadata.create_all(bind=engine)

def drop_all() -> None:
    """Drop all tables in the database. Uses metadata from Base."""
    Base.metadata.drop_all(bind=engine)

def db_healthcheck() -> Dict[str, Any]:
    """
    Quick connectivity test: fetch server version and current timestamp.
    Returns a dict you can print for diagnostics.
    """
    with engine.connect() as conn:
        server_version = conn.execute(text("show server_version")).scalar_one()
        now = conn.execute(text("select now()")).scalar_one()
        return {"server_version": str(server_version), "now": str(now)}
