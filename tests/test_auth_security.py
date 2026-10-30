"""
Comprehensive authentication, security, lockout, and tenant isolation tests.
"""

from datetime import datetime, timedelta
import pytest
from core.models import User, PasswordReset, Profile, FamilyMember, IncomeSource, FixedObligation, Loan, Expense
from core.auth import (
    hash_password, check_password, validate_password_strength,
    authenticate_user, register_user, create_password_reset_token,
    verify_and_reset_password, delete_user_account, is_session_timed_out,
    MAX_FAILED_ATTEMPTS
)


def test_password_hashing_and_verification():
    """Verify bcrypt hash generation and validation."""
    raw_pw = "PariVar#2026Secure"
    hashed = hash_password(raw_pw)

    assert hashed != raw_pw
    assert hashed.startswith("$2b$")  # bcrypt identifier
    assert check_password(raw_pw, hashed) is True
    assert check_password("WrongPassword123", hashed) is False


def test_password_strength_validation():
    """Verify minimum length, numeric, and character requirements."""
    # Too short
    ok, msg = validate_password_strength("Short1")
    assert not ok
    assert "at least 8" in msg

    # No digits
    ok, msg = validate_password_strength("NoDigitsHere")
    assert not ok
    assert "number" in msg

    # No letters
    ok, msg = validate_password_strength("123456789")
    assert not ok
    assert "letter" in msg

    # Valid
    ok, msg = validate_password_strength("StrongPass88")
    assert ok
    assert msg == ""


def test_account_lockout_after_five_failed_attempts(test_db, user_a):
    """Verify account locks after 5 consecutive failed logins and rejects further attempts."""
    email = user_a.email

    # 4 failed attempts: account should still remain unlocked
    for attempt in range(1, MAX_FAILED_ATTEMPTS):
        u, msg = authenticate_user(test_db, email, "WrongPassword")
        assert u is None
        assert f"{MAX_FAILED_ATTEMPTS - attempt} attempt(s) remaining" in msg

    # 5th failed attempt: triggers lockout
    u, msg = authenticate_user(test_db, email, "WrongPassword")
    assert u is None
    assert "Account locked for 15 minutes" in msg

    # Subsequent attempt even with the RIGHT password should be rejected while locked
    u, msg = authenticate_user(test_db, email, "SecurePassword123")
    assert u is None
    assert "Account locked" in msg


def test_successful_login_resets_failed_attempts(test_db, user_a):
    """Verify that a successful login resets the failed_attempts counter."""
    email = user_a.email

    # Fail twice
    authenticate_user(test_db, email, "WrongPassword")
    authenticate_user(test_db, email, "WrongPassword")

    # Verify counter in DB
    refreshed = test_db.query(User).filter(User.email == email).first()
    assert refreshed.failed_attempts == 2

    # Succeed on 3rd attempt
    u, msg = authenticate_user(test_db, email, "SecurePassword123")
    assert u is not None
    assert u.failed_attempts == 0
    assert u.locked_until is None


def test_session_timeout():
    """Verify session timeout triggers after 20 minutes of inactivity."""
    now_epoch = datetime.utcnow().timestamp()

    # Active 5 minutes ago -> not timed out
    recent_activity = now_epoch - (5 * 60)
    assert is_session_timed_out(recent_activity, timeout_minutes=20) is False

    # Inactive 21 minutes ago -> timed out
    stale_activity = now_epoch - (21 * 60)
    assert is_session_timed_out(stale_activity, timeout_minutes=20) is True


def test_password_reset_flow(test_db, user_a):
    """Verify end-to-end password reset with token hashing and 30-minute validity."""
    email = user_a.email

    ok, msg, token = create_password_reset_token(test_db, email)
    assert ok is True
    assert token is not None

    # Ensure token itself is NOT stored in plain text in DB
    stored_reset = test_db.query(PasswordReset).filter(PasswordReset.user_id == user_a.user_id).first()
    assert stored_reset is not None
    assert stored_reset.token_hash != token
    assert len(stored_reset.token_hash) == 64  # SHA-256 hex string

    # Attempt reset with invalid token
    success, err_msg = verify_and_reset_password(test_db, "InvalidToken12345", "NewPassword789")
    assert not success

    # Reset with valid token
    success, ok_msg = verify_and_reset_password(test_db, token, "NewPassword789")
    assert success
    assert "successful" in ok_msg

    # Verify old password no longer works, new password works
    old_login, _ = authenticate_user(test_db, email, "SecurePassword123")
    assert old_login is None

    new_login, _ = authenticate_user(test_db, email, "NewPassword789")
    assert new_login is not None


def test_multi_tenant_isolation(test_db, user_a, user_b):
    """Verify that User A queries cannot read or touch User B's financial records."""
    # Seed data for User A
    exp_a = Expense(user_id=user_a.user_id, date=datetime.utcnow().date(), category="Groceries", amount=4500.0)
    # Seed data for User B
    exp_b = Expense(user_id=user_b.user_id, date=datetime.utcnow().date(), category="Rent", amount=25000.0)
    test_db.add_all([exp_a, exp_b])
    test_db.commit()

    # Query scoped to User A
    user_a_expenses = test_db.query(Expense).filter(Expense.user_id == user_a.user_id).all()
    assert len(user_a_expenses) == 1
    assert user_a_expenses[0].amount == 4500.0

    # Query scoped to User B
    user_b_expenses = test_db.query(Expense).filter(Expense.user_id == user_b.user_id).all()
    assert len(user_b_expenses) == 1
    assert user_b_expenses[0].amount == 25000.0

    # Ensure no leakage across tenants
    user_a_ids = [e.id for e in user_a_expenses]
    assert exp_b.id not in user_a_ids


def test_account_deletion_with_cascade(test_db, user_a):
    """Verify delete-my-account cascades and completely cleans up all linked tables."""
    user_id = user_a.user_id

    # Populate associated records for User A
    prof = Profile(user_id=user_id, state="Maharashtra", city_type="Metro", household_size=4)
    fam = FamilyMember(user_id=user_id, name="Sunita", relation="Spouse", age=32)
    loan = Loan(user_id=user_id, loan_type="Home Loan", balance=3500000, interest_rate=8.5, emi=30000, remaining_months=180)
    test_db.add_all([prof, fam, loan])
    test_db.commit()

    # Confirm records exist
    assert test_db.query(Profile).filter(Profile.user_id == user_id).count() == 1
    assert test_db.query(FamilyMember).filter(FamilyMember.user_id == user_id).count() == 1
    assert test_db.query(Loan).filter(Loan.user_id == user_id).count() == 1

    # Attempt deletion with incorrect password
    ok, err = delete_user_account(test_db, user_id, "WrongPassword")
    assert not ok
    assert "Incorrect password" in err

    # Perform deletion with correct password
    ok, msg = delete_user_account(test_db, user_id, "SecurePassword123")
    assert ok

    # Verify User and all cascading rows are wiped
    assert test_db.query(User).filter(User.user_id == user_id).first() is None
    assert test_db.query(Profile).filter(Profile.user_id == user_id).first() is None
    assert test_db.query(FamilyMember).filter(FamilyMember.user_id == user_id).first() is None
    assert test_db.query(Loan).filter(Loan.user_id == user_id).first() is None
