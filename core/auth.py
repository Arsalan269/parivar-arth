"""
Authentication, Password Security, Lockout, and Token Management for Parivar Arth.
Uses bcrypt hashing, brute-force lockout, session timeouts, and token hashing.
"""

import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import bcrypt
from sqlalchemy.orm import Session
from core.models import User, PasswordReset, AuditLog

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
RESET_TOKEN_EXPIRY_MINUTES = 30
SESSION_TIMEOUT_MINUTES = 20


def get_utc_now() -> datetime:
    """Return timezone-naive UTC datetime for consistent database persistence."""
    return datetime.now(timezone.utc).replace(tzinfo=None)



def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt and automatic salt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def check_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength rules:
    - Minimum 8 characters
    - At least one letter
    - At least one number
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isalpha() for c in password):
        return False, "Password must contain at least one letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    return True, ""


def hash_token(token: str) -> str:
    """Hash a raw reset token with SHA-256 for secure storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def register_user(
    db: Session,
    name: str,
    email: str,
    password: str,
    role: str = "user"
) -> Tuple[Optional[User], str]:
    """Register a new user with bcrypt password and unique email check."""
    clean_name = name.strip()
    clean_email = email.strip().lower()

    if not clean_name:
        return None, "Please enter your name."
    if not clean_email or "@" not in clean_email or "." not in clean_email:
        return None, "Please enter a valid email address."

    is_strong, msg = validate_password_strength(password)
    if not is_strong:
        return None, msg

    # Check email duplicate
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        return None, "An account with this email already exists."

    pw_hash = hash_password(password)
    now = get_utc_now()
    user = User(
        name=clean_name,
        email=clean_email,
        password_hash=pw_hash,
        role=role,
        failed_attempts=0,
        locked_until=None,
        created_at=now,
    )
    db.add(user)
    db.flush()

    audit = AuditLog(
        actor=clean_email,
        action="USER_REGISTERED",
        timestamp=now,
        details=f"User registered with role: {role}",
    )
    db.add(audit)
    db.commit()
    db.refresh(user)
    return user, "Registration successful."


def authenticate_user(
    db: Session,
    email: str,
    password: str
) -> Tuple[Optional[User], str]:
    """
    Authenticate user credentials with brute-force lockout defense.
    Locks account for 15 minutes after 5 consecutive failed attempts.
    """
    clean_email = email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()

    if not user:
        return None, "Invalid email or password."

    # Check lockout
    now = get_utc_now()
    if user.locked_until and user.locked_until > now:
        remaining_secs = int((user.locked_until - now).total_seconds())
        remaining_mins = max(1, remaining_secs // 60)
        return None, f"Account locked due to multiple failed attempts. Please retry in {remaining_mins} minutes or reset your password."

    if not check_password(password, user.password_hash):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            db.add(AuditLog(
                actor=clean_email,
                action="ACCOUNT_LOCKED",
                timestamp=now,
                details=f"Locked out after {user.failed_attempts} failed attempts.",
            ))
            db.commit()
            return None, f"Account locked for {LOCKOUT_DURATION_MINUTES} minutes due to {MAX_FAILED_ATTEMPTS} failed attempts."
        
        db.commit()
        remaining = MAX_FAILED_ATTEMPTS - user.failed_attempts
        return None, f"Invalid email or password. ({remaining} attempt(s) remaining before lockout)."

    # Password matches - reset lockout & record login
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login = now
    db.add(AuditLog(
        actor=clean_email,
        action="USER_LOGIN",
        timestamp=now,
        details="Successful login.",
    ))
    db.commit()
    return user, "Login successful."


def create_password_reset_token(db: Session, email: str) -> Tuple[bool, str, Optional[str]]:
    """
    Generate a 32-byte cryptographically secure reset token, store its SHA-256 hash,
    and output via pluggable email / console fallback.
    """
    clean_email = email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()

    if not user:
        # Return generic message to prevent account enumeration
        return True, "If an account exists with that email, a password reset link has been dispatched.", None

    token = secrets.token_urlsafe(32)
    thash = hash_token(token)
    now = get_utc_now()
    expires_at = now + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)

    reset_record = PasswordReset(
        user_id=user.user_id,
        token_hash=thash,
        expires_at=expires_at
    )
    db.add(reset_record)
    db.add(AuditLog(
        actor=clean_email,
        action="PASSWORD_RESET_REQUESTED",
        timestamp=now,
        details=f"Token expires at {expires_at.isoformat()}",
    ))
    db.commit()

    # Pluggable dispatcher (console fallback for demos)
    print(f"\n[PARIVAR ARTH SECURITY] Password Reset Token for {clean_email}:\nTOKEN: {token}\n(Expires in 30 minutes)\n")
    return True, "Password reset token generated. Check your email (or terminal console in demo mode).", token


def verify_and_reset_password(
    db: Session,
    token: str,
    new_password: str
) -> Tuple[bool, str]:
    """Verify reset token hash, check expiry, and update password."""
    clean_token = token.strip()
    if not clean_token:
        return False, "Please provide the reset token."

    is_strong, msg = validate_password_strength(new_password)
    if not is_strong:
        return False, msg

    thash = hash_token(clean_token)
    now = get_utc_now()

    reset_record = (
        db.query(PasswordReset)
        .filter(PasswordReset.token_hash == thash, PasswordReset.expires_at > now)
        .first()
    )

    if not reset_record:
        return False, "Invalid or expired reset token. Please request a new one."

    user = db.query(User).filter(User.user_id == reset_record.user_id).first()
    if not user:
        return False, "User not found."

    user.password_hash = hash_password(new_password)
    user.failed_attempts = 0
    user.locked_until = None

    # Delete all pending reset tokens for this user
    db.query(PasswordReset).filter(PasswordReset.user_id == user.user_id).delete()

    db.add(AuditLog(
        actor=user.email,
        action="PASSWORD_RESET_COMPLETED",
        timestamp=now,
        details="Password successfully updated using reset token.",
    ))
    db.commit()
    return True, "Password reset successful! You can now log in with your new password."


def delete_user_account(db: Session, user_id: int, password: str) -> Tuple[bool, str]:
    """
    Verify current password and cascade delete the entire account and all associated records.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return False, "User not found."

    if not check_password(password, user.password_hash):
        return False, "Incorrect password. Account deletion aborted."

    email = user.email
    db.delete(user)
    db.add(AuditLog(
        actor=email,
        action="ACCOUNT_DELETED",
        timestamp=get_utc_now(),
        details="Account and all cascading data permanently purged.",
    ))
    db.commit()
    return True, "Account and all associated family data have been permanently deleted."


def is_session_timed_out(last_activity_epoch: Optional[float], timeout_minutes: int = SESSION_TIMEOUT_MINUTES) -> bool:
    """Check if session has exceeded the inactivity timeout threshold."""
    if last_activity_epoch is None:
        return False
    now_epoch = get_utc_now().timestamp()
    return (now_epoch - last_activity_epoch) > (timeout_minutes * 60)
