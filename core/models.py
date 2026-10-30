"""
SQLAlchemy ORM models for Parivar Arth.
All user-owned models include user_id with ON DELETE CASCADE foreign key constraints.
"""

from datetime import datetime, date, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship
from core.db import Base


def get_utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)



class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), default="user", nullable=False)  # "user" or "admin"
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships with CASCADE deletion
    resets = relationship("PasswordReset", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    family_members = relationship("FamilyMember", back_populates="user", cascade="all, delete-orphan")
    income_sources = relationship("IncomeSource", back_populates="user", cascade="all, delete-orphan")
    fixed_obligations = relationship("FixedObligation", back_populates="user", cascade="all, delete-orphan")
    recurring_expenses = relationship("RecurringExpense", back_populates="user", cascade="all, delete-orphan")
    household_help = relationship("HouseholdHelp", back_populates="user", cascade="all, delete-orphan")
    loans = relationship("Loan", back_populates="user", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="user", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("SuggestionFeedback", back_populates="user", cascade="all, delete-orphan")


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="resets")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    state = Column(String(100), nullable=False)
    city_type = Column(String(50), nullable=False)  # "Metro", "Tier-1", "Tier-2/3", "Rural"
    household_size = Column(Integer, default=1, nullable=False)
    is_onboarding_completed = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    user = relationship("User", back_populates="profile")


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    relation = Column(String(50), nullable=False)  # "Self", "Spouse", "Child", "Parent", "Other"
    age = Column(Integer, nullable=False)
    has_chronic_condition = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="family_members")


class IncomeSource(Base):
    __tablename__ = "income_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    earner_id = Column(Integer, ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True)
    source_type = Column(String(100), nullable=False)  # "Salary", "Business", "Freelance/Gig", "Pension", "Rental"
    amount = Column(Float, nullable=False)
    is_variable = Column(Boolean, default=False, nullable=False)
    effective_from = Column(Date, default=date.today, nullable=False)
    effective_to = Column(Date, nullable=True)  # NULL denotes current active version

    user = relationship("User", back_populates="income_sources")
    earner = relationship("FamilyMember")


class FixedObligation(Base):
    __tablename__ = "fixed_obligations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True)
    category = Column(String(100), nullable=False)  # "Rent", "Groceries", "Utilities", "Child Education", "Parent Medical", "Commute", "Insurance"
    amount = Column(Float, nullable=False)
    frequency = Column(String(50), default="Monthly", nullable=False)  # "Monthly", "Quarterly", "Annual", "One-time"
    effective_from = Column(Date, default=date.today, nullable=False)
    effective_to = Column(Date, nullable=True)  # NULL denotes current active version

    user = relationship("User", back_populates="fixed_obligations")
    member = relationship("FamilyMember")


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    amount = Column(Float, nullable=False)
    frequency = Column(String(50), default="Annual", nullable=False)  # "Annual", "Quarterly", "Half-Yearly"
    due_month = Column(Integer, nullable=True)  # 1 to 12
    category = Column(String(100), nullable=False)

    user = relationship("User", back_populates="recurring_expenses")


class HouseholdHelp(Base):
    __tablename__ = "household_help"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(100), nullable=False)  # "Maid", "Cook", "Driver", "Childcare", "Tuition"
    monthly_cost = Column(Float, nullable=False)
    growth_override = Column(Float, nullable=True)  # Custom expected annual jump %

    user = relationship("User", back_populates="household_help")


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    loan_type = Column(String(100), nullable=False)  # "Home Loan", "Car Loan", "Personal Loan", "Credit Card Debt", "Education Loan"
    balance = Column(Float, nullable=False)
    interest_rate = Column(Float, nullable=False)  # Annual % (e.g. 8.5)
    emi = Column(Float, nullable=False)
    remaining_months = Column(Integer, nullable=False)
    rate_type = Column(String(50), default="Fixed", nullable=False)  # "Fixed" or "Floating"

    user = relationship("User", back_populates="loans")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(100), nullable=False)  # "Savings Account", "Fixed Deposit", "Mutual Funds/SIP", "Gold", "Real Estate", "PPF/EPF", "Cash"
    amount = Column(Float, nullable=False)
    is_liquid = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="assets")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    category = Column(String(100), nullable=False)  # "Food", "Groceries", "Transport", "Shopping", "Entertainment", "Health", "Bills", "Other"
    amount = Column(Float, nullable=False)
    note = Column(String(255), default="", nullable=False)

    user = relationship("User", back_populates="expenses")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    target_amount = Column(Float, nullable=False)
    target_date = Column(Date, nullable=False)
    priority = Column(String(50), default="Medium", nullable=False)  # "High", "Medium", "Low"

    user = relationship("User", back_populates="goals")


class SuggestionFeedback(Base):
    __tablename__ = "suggestion_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    suggestion_id = Column(String(100), nullable=False)
    useful = Column(Boolean, nullable=False)

    user = relationship("User", back_populates="feedback")


# Global tables (System / Non-tenant)
class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(100), nullable=False, index=True)
    target_month = Column(Date, nullable=False, index=True)
    predicted_inflation = Column(Float, nullable=False)
    lower_ci = Column(Float, nullable=False)
    upper_ci = Column(Float, nullable=False)
    model_version = Column(String(50), default="v1.0", nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)


class ModelRun(Base):
    __tablename__ = "model_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(50), nullable=False)
    trained_at = Column(DateTime, default=get_utc_now, nullable=False)
    target_category = Column(String(100), nullable=False)
    rmse = Column(Float, nullable=False)
    mae = Column(Float, nullable=False)
    mape = Column(Float, nullable=False)
    baseline_mape = Column(Float, nullable=False)
    model_type = Column(String(100), nullable=False)  # "XGBoost", "SARIMA", "RandomForest", "Naive"
    notes = Column(String(255), default="", nullable=False)


class SavingsLever(Base):
    __tablename__ = "savings_levers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(100), nullable=False)
    condition_key = Column(String(100), nullable=False)
    suggestion_text = Column(String(500), nullable=False)
    estimated_saving_pct = Column(Float, nullable=False)
    priority_rank = Column(Integer, default=1, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=get_utc_now, nullable=False)
    details = Column(String(1000), default="", nullable=False)
