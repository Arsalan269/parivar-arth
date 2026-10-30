"""
Multi-tenant security helpers for Parivar Arth.
Guarantees that user_id is strictly resolved from the authenticated session
and never from URL query parameters or client request payloads.
"""

from datetime import datetime
from typing import Optional, Any
import streamlit as st
from sqlalchemy.orm import Query
from core.models import User


def get_current_user_id() -> Optional[int]:
    """
    Retrieve the authenticated user_id from Streamlit session state.
    Returns None if the user is unauthenticated.
    """
    if "user" in st.session_state and st.session_state["user"]:
        return st.session_state["user"].get("user_id")
    return None


def get_current_user_role() -> str:
    """Retrieve the current user's role ("user" or "admin")."""
    if "user" in st.session_state and st.session_state["user"]:
        return st.session_state["user"].get("role", "user")
    return "user"


def is_authenticated() -> bool:
    """Check if a valid, authenticated session exists."""
    return get_current_user_id() is not None


def is_admin_user() -> bool:
    """Check if the authenticated user has administrative privileges."""
    return get_current_user_role() == "admin"


def touch_session():
    """Update the last activity timestamp for session timeout monitoring."""
    st.session_state["last_activity"] = datetime.utcnow().timestamp()


def scope_query_to_user(query: Query, model_class: Any) -> Query:
    """
    Strictly enforce tenant isolation on SQLAlchemy queries by filtering
    on the authenticated user's ID. Raises PermissionError if unauthenticated.
    """
    user_id = get_current_user_id()
    if user_id is None:
        raise PermissionError("Unauthenticated request. Access denied.")
    
    if hasattr(model_class, "user_id"):
        return query.filter(model_class.user_id == user_id)
    return query
