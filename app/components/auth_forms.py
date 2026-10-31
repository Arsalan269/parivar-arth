"""
Authentication UI Components for Parivar Arth (Aether FinTech Theme):
Login, Register (with consent & privacy disclaimer), Password Reset, and Account Deletion.
"""

import time
import streamlit as st
from core.db import get_db_session
from core.auth import (
    authenticate_user, register_user, create_password_reset_token,
    verify_and_reset_password, delete_user_account
)
from core.security import touch_session
from app.styles import (
    PRIMARY_ACCENT, SECONDARY_ACCENT, TEXT_PRIMARY, TEXT_SECONDARY,
    BORDER_COLOR, COLOR_DANGER, COLOR_SUCCESS, SOFT_PURPLE,
    PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
)


def render_auth_tabs():
    """Render Tabbed Authentication Interface: Login, Register, Forgot Password."""
    login_tab, register_tab, reset_tab = st.tabs(["Sign In", "Register New Family", "Forgot Password"])

    # ---------------- LOGIN TAB ----------------
    with login_tab:
        st.markdown(
            f"""
            <div style="margin-bottom: 1.25rem;">
                <h3 style="color: {TEXT_PRIMARY}; font-size: 1.35rem; font-weight: 700; margin-bottom: 0.25rem;">Sign In to Parivar Arth</h3>
                <p style="color: {TEXT_SECONDARY}; font-size: 0.9rem; margin-top: 0;">Access your household's inflation projections, cash flow engine, and savings plan.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email Address", placeholder="name@example.com", help="Your registered email address.")
            password = st.text_input("Password", type="password", placeholder="Enter your password", help="Enter your account password.")
            submitted = st.form_submit_button("Sign In to Dashboard", use_container_width=True, type="primary")

            if submitted:
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    with get_db_session() as db:
                        user, message = authenticate_user(db, email, password)
                        if user:
                            # Set session
                            st.session_state["user"] = {
                                "user_id": user.user_id,
                                "name": user.name,
                                "email": user.email,
                                "role": user.role
                            }
                            touch_session()
                            st.success(f"Welcome back, {user.name}! Redirecting to dashboard...")
                            time.sleep(0.4)
                            st.rerun()
                        else:
                            st.error(message)

    # ---------------- REGISTER TAB ----------------
    with register_tab:
        st.markdown(
            f"""
            <div style="margin-bottom: 1.25rem;">
                <h3 style="color: {TEXT_PRIMARY}; font-size: 1.35rem; font-weight: 700; margin-bottom: 0.25rem;">Create Household Account</h3>
                <p style="color: {TEXT_SECONDARY}; font-size: 0.9rem; margin-top: 0;">One account per household. All financial forecasts and data are strictly isolated.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("register_form", clear_on_submit=False):
            name = st.text_input("Primary Earner / Head of Household Name", placeholder="e.g. Rajesh Kumar")
            reg_email = st.text_input("Email Address", placeholder="rajesh@example.com")
            reg_pw = st.text_input("Create Password", type="password", placeholder="At least 8 characters, letters & numbers")
            reg_pw_confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")

            st.markdown(
                f"""
                <div style="background-color: #FAFAFD; border: 1px solid {BORDER_COLOR}; border-radius: 12px; padding: 12px 16px; font-size: 0.82rem; color: {TEXT_SECONDARY}; margin: 12px 0;">
                    <div style="font-weight: 700; color: {TEXT_PRIMARY}; margin-bottom: 4px;">Data Privacy & Planning Disclaimer</div>
                    • Parivar Arth is an educational planning tool, not SEBI-registered financial or medical advice.<br>
                    • We never sell, share, or monetize family transaction records.<br>
                    • Encrypted with bcrypt; queries use multi-tenant session isolation.
                </div>
                """,
                unsafe_allow_html=True
            )

            consent = st.checkbox("I understand and accept the privacy notice and disclaimer terms.", value=False)
            reg_submitted = st.form_submit_button("Create Account & Start Planning", use_container_width=True, type="primary")

            if reg_submitted:
                if not consent:
                    st.error("Please accept the privacy note and disclaimer to create an account.")
                elif reg_pw != reg_pw_confirm:
                    st.error("Passwords do not match.")
                else:
                    with get_db_session() as db:
                        user, message = register_user(db, name, reg_email, reg_pw)
                        if user:
                            st.session_state["user"] = {
                                "user_id": user.user_id,
                                "name": user.name,
                                "email": user.email,
                                "role": user.role
                            }
                            touch_session()
                            st.success("Account created successfully! Welcome to Parivar Arth.")
                            time.sleep(0.4)
                            st.rerun()
                        else:
                            st.error(message)

    # ---------------- FORGOT PASSWORD TAB ----------------
    with reset_tab:
        st.markdown(
            f"""
            <div style="margin-bottom: 1.25rem;">
                <h3 style="color: {TEXT_PRIMARY}; font-size: 1.35rem; font-weight: 700; margin-bottom: 0.25rem;">Reset Your Password</h3>
                <p style="color: {TEXT_SECONDARY}; font-size: 0.9rem; margin-top: 0;">Generate a secure, one-time 30-minute token to update your password.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        sub_tab1, sub_tab2 = st.tabs(["1. Request Token", "2. Submit Token & New Password"])

        with sub_tab1:
            with st.form("request_token_form"):
                req_email = st.text_input("Enter your registered email")
                req_btn = st.form_submit_button("Send Reset Token", use_container_width=True)
                if req_btn:
                    if not req_email:
                        st.error("Please provide your email.")
                    else:
                        with get_db_session() as db:
                            ok, msg, token = create_password_reset_token(db, req_email)
                            if token:
                                st.info(f"Demo Mode: Your one-time token is: **`{token}`** (expires in 30 mins). In production, this is sent via email.")
                            st.success(msg)

        with sub_tab2:
            with st.form("reset_password_form"):
                reset_token = st.text_input("Paste Reset Token", placeholder="Enter the 32-character token")
                new_pw = st.text_input("New Password", type="password", placeholder="Minimum 8 characters with letters & digits")
                new_pw_conf = st.text_input("Confirm New Password", type="password")
                submit_reset = st.form_submit_button("Set New Password", use_container_width=True, type="primary")

                if submit_reset:
                    if new_pw != new_pw_conf:
                        st.error("New passwords do not match.")
                    else:
                        with get_db_session() as db:
                            success, msg = verify_and_reset_password(db, reset_token, new_pw)
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)


def render_delete_account_dialog(user_id: int):
    """Render Delete Account confirmation modal/expander."""
    with st.expander("Danger Zone: Delete My Account", expanded=False):
        st.markdown(
            f"""
            <div style="color: {COLOR_DANGER}; font-size: 0.88rem; margin-bottom: 12px; line-height: 1.4;">
                <strong>Warning:</strong> Deleting your account will permanently wipe all your family profiles,
                income sources, fixed obligations, recorded expenses, and loan records.
                This action cannot be undone.
            </div>
            """,
            unsafe_allow_html=True
        )
        with st.form("delete_account_form"):
            del_pw = st.text_input("Confirm your password to authorize permanent deletion", type="password")
            confirm_check = st.checkbox("I understand that all my family financial records will be permanently erased.")
            del_btn = st.form_submit_button("Permanently Delete My Account", type="secondary", use_container_width=True)

            if del_btn:
                if not confirm_check:
                    st.error("Please check the confirmation box.")
                elif not del_pw:
                    st.error("Please enter your current password.")
                else:
                    with get_db_session() as db:
                        ok, msg = delete_user_account(db, user_id, del_pw)
                        if ok:
                            st.session_state.clear()
                            st.success("Account successfully deleted.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(msg)
