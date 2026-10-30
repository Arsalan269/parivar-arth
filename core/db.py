"""
Database Connection and Session Management for Parivar Arth.
Supports SQLite (development/default) and PostgreSQL (production).
"""

import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Base class for declarative models
Base = declarative_base()


def get_database_url() -> str:
    """
    Retrieve database URL with fallback order:
    1. Streamlit secrets (if running in Streamlit)
    2. DATABASE_URL environment variable
    3. Default local SQLite database file in the project root
    """
    # Try streamlit secrets if available
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass

    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url

    # Default to sqlite file in current working directory or package root
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    db_path = os.path.join(base_dir, "parivar_arth.db")
    return f"sqlite:///{db_path}"


# Enable SQLite Foreign Key constraints
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Ensure SQLite enforces FOREIGN KEY constraints and ON DELETE CASCADE."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass


_engine = None
_SessionFactory = None


def get_engine():
    """Get or initialize the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        db_url = get_database_url()
        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
    return _engine


def get_session_factory():
    """Get or initialize sessionmaker factory."""
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False
        )
    return _SessionFactory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for safe transactional database sessions."""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine=None):
    """Create all defined database tables."""
    eng = engine or get_engine()
    Base.metadata.create_all(bind=eng)
