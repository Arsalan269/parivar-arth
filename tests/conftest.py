"""
Pytest configuration and database fixtures for Parivar Arth.
Uses an in-memory SQLite database with StaticPool to ensure test isolation and speed.
"""

import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import Base
from core.models import User, Profile, FamilyMember, IncomeSource, FixedObligation, Loan, Expense
from core.auth import register_user


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory SQLite database isolated per test function."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    # Enable foreign keys in SQLite
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys = ON;")

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def user_a(test_db):
    """Seed user A (salaried earner)."""
    user, _ = register_user(
        db=test_db,
        name="Aarav Sharma",
        email="aarav@sharma.in",
        password="SecurePassword123",
        role="user"
    )
    return user


@pytest.fixture(scope="function")
def user_b(test_db):
    """Seed user B (separate household)."""
    user, _ = register_user(
        db=test_db,
        name="Vikram Patel",
        email="vikram@patel.in",
        password="AnotherPassword456",
        role="user"
    )
    return user


@pytest.fixture(scope="function")
def admin_user(test_db):
    """Seed an admin user."""
    user, _ = register_user(
        db=test_db,
        name="Admin Parivar",
        email="admin@parivararth.in",
        password="AdminMasterPass999",
        role="admin"
    )
    return user
