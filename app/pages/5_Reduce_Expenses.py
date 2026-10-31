"""
'Reduce My Necessary Expenses' Engine Page for Parivar Arth.
Aether FinTech Design System - Practical Category Optimization Levers and Interactive Reclaim Engine.
"""

import os
import sys
import streamlit as st
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import get_db_session
from core.security import touch_session, get_current_user_id
from core.profile_service import get_household_profile
from planner.reduction import evaluate_necessary_expense_reductions
from app.styles import (
    apply_theme, render_header, render_footer, render_metric_card,
    render_sidebar_brand, render_sidebar_user,
    PRIMARY_ACCENT, SECONDARY_ACCENT, SOFT_PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER_COLOR,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
)
from app.components.formatters import format_inr


def show_reduce_expenses_page():
    st.set_page_config(
        page_title="Reduce Expenses - Parivar Arth",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    apply_theme()
    touch_session()

    render_sidebar_brand()

    user_data = st.session_state.get("user")
    user_id = user_data["user_id"] if user_data else get_current_user_id()
    if not user_id:
        st.warning("Please sign in to view your expense reduction opportunities.")
        st.stop()

    with st.sidebar:
        user_name = user_data.get("name", "Household Account") if user_data else "User"
        render_sidebar_user(username=user_name, role="Primary Account")
        if st.button("Sign Out", key="re_logout_btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    render_header(
        title="Reduce Necessary Expenses",
        subtitle="Practical, dignified levers to trim fixed commitments ranked by monthly rupee impact",
        tag="Optimization"
    )

    # Realistic framing banner
    st.markdown(
        f"""
        <div class="aether-card" style="margin-bottom: 1.5rem; border-left: 4px solid {PRIMARY_ACCENT}; padding: 14px 18px;">
            <div style="font-weight: 700; color: {TEXT_PRIMARY}; font-size: 0.95rem; margin-bottom: 3px;">
                Transparent Optimization Philosophy
            </div>
            <div style="font-size: 0.88rem; color: {TEXT_SECONDARY}; line-height: 1.6;">
                We do not recommend unrealistic compromises. Instead, we analyze your financial obligations
                to identify actionable optimizations (electricity tariff slabs, bulk staples, fuel routes, and subscription consolidation)
                ranked strictly by <strong>monthly rupee impact</strong>.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with get_db_session() as db:
        profile_data = get_household_profile(db, user_id)

    incomes = profile_data.get("incomes", [])
    obligations = profile_data.get("obligations", [])
    loans = profile_data.get("loans", [])

    total_income = sum(float(getattr(i, "amount", 0.0)) for i in incomes)
    obligation_dicts = [{"category": getattr(o, "category", "Other"), "amount": float(getattr(o, "amount", 0.0))} for o in obligations]
    loan_dicts = [{"id": l.id, "loan_type": l.loan_type, "balance": l.balance, "interest_rate": l.interest_rate, "emi": l.emi} for l in loans]

    levers = evaluate_necessary_expense_reductions(
        monthly_income=total_income,
        obligations=obligation_dicts,
        loans=loan_dicts,
        food_inflation_forecast=6.2
    )

    if not levers:
        st.info("No immediate high-cost optimization flags detected in your profile.")
        render_footer()
        return

    st.markdown(
        f"""
        <div style="margin-top: 1rem; margin-bottom: 0.75rem;">
            <h3 style="font-size: 1.25rem; font-weight: 700; color: {TEXT_PRIMARY}; margin: 0;">Interactive Reclaim Simulator</h3>
            <p style="font-size: 0.88rem; color: {TEXT_SECONDARY}; margin: 2px 0 0 0;">Check or uncheck levers to compute immediate monthly and annual savings</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    selected_savings = 0.0

    for idx, lev in enumerate(levers, start=1):
        col_chk, col_card = st.columns([0.08, 0.92])
        with col_chk:
            st.write("")
            st.write("")
            adopt = st.checkbox("", key=f"adopt_lever_{idx}", value=True)
        with col_card:
            diff_badge = "#E6F8F3" if lev["difficulty"] == "Easy" else ("#FFFBEB" if lev["difficulty"] == "Medium" else "#FEF2F2")
            diff_color = COLOR_SUCCESS if lev["difficulty"] == "Easy" else ("#D97706" if lev["difficulty"] == "Medium" else COLOR_DANGER)

            st.markdown(
                f"""
                <div class="aether-card" style="margin-bottom: 0.75rem; padding: 1.15rem 1.4rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span class="status-badge status-purple">
                            #{idx} • {lev['category']} (Current: {format_inr(lev['current_spend'])})
                        </span>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <span style="background-color: {diff_badge}; color: {diff_color}; padding: 3px 9px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700;">
                                {lev['difficulty']} Effort
                            </span>
                            <span style="font-weight: 800; color: {COLOR_SUCCESS}; font-size: 1.1rem;">
                                ~+{format_inr(lev['est_monthly_saving'])}/mo
                            </span>
                        </div>
                    </div>
                    <h4 style="margin: 6px 0 4px 0; color: {TEXT_PRIMARY}; font-size: 1.05rem;">{lev['title']}</h4>
                    <p style="margin: 0; color: {TEXT_SECONDARY}; font-size: 0.88rem; line-height: 1.5;">{lev['action']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

        if adopt:
            selected_savings += lev["est_monthly_saving"]

    # Interactive Recalculation Summary Card
    annual_savings = selected_savings * 12
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="aether-glass-card" style="text-align: center; padding: 2rem 1.5rem; border: 1px solid #D6D2FF;">
            <div style="font-size: 0.82rem; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em; color: {TEXT_SECONDARY};">
                Total Reclaimed Monthly Cash Flow
            </div>
            <div style="font-size: 2.5rem; font-weight: 800; color: {PRIMARY_ACCENT}; margin: 8px 0; letter-spacing: -0.03em;">
                +{format_inr(selected_savings)} / month
            </div>
            <div style="font-size: 0.95rem; color: {TEXT_PRIMARY}; max-width: 600px; margin: 0 auto; line-height: 1.6;">
                Adopting your selected levers frees up approximately <strong>{format_inr(annual_savings)} per year</strong>,
                which can be channeled directly into your liquid emergency buffer or children's education milestones.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    render_footer()


if __name__ == "__main__":
    show_reduce_expenses_page()
