"""
'Reduce My Necessary Expenses' Engine Page for Parivar Arth.
Provides category-specific practical reduction levers ranked by rupee impact,
with transparent Indian economic context and interactive savings simulation.
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
from app.styles import apply_theme, render_header, render_footer, PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
from app.components.formatters import format_inr


def show_reduce_expenses_page():
    st.set_page_config(page_title="Reduce Necessary Expenses - Parivar Arth", page_icon="✂️", layout="centered")
    apply_theme()
    touch_session()

    user_id = get_current_user_id()
    if not user_id:
        st.warning("Please sign in to view your expense reduction opportunities.")
        st.stop()

    render_header(
        title="Reduce Necessary Expenses",
        subtitle="Practical room to optimize essential costs ranked by monthly rupee impact",
        icon="✂️"
    )

    # Honest framing banner
    st.markdown(
        f"""
        <div style="background-color: #F8FAFC; border-left: 4px solid {PRIMARY_TEAL}; padding: 12px 16px; border-radius: 8px; margin-bottom: 1.5rem;">
            <strong style="color: {PRIMARY_TEAL};">Honest Financial Realism:</strong><br>
            <span style="font-size: 0.9rem; color: #475569;">
            We do not claim algorithms can magically cut your landlord's rent or your child's school fees. 
            Instead, we analyze your financial commitments to surface realistic room to optimize 
            ranked strictly by <strong>monthly rupee impact</strong>. All savings figures are estimated guides.
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    with get_db_session() as db:
        profile_data = get_household_profile(db, user_id)

    incomes = profile_data["incomes"]
    obligations = profile_data["obligations"]
    loans = profile_data["loans"]

    total_income = sum(i.amount for i in incomes)
    obligation_dicts = [{"category": o.category, "amount": o.amount} for o in obligations]
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

    st.markdown("### 🎯 Prioritized Reduction Levers")
    st.caption("Select the practical levers your family can adopt to calculate your total monthly savings:")

    selected_savings = 0.0

    for idx, lev in enumerate(levers, start=1):
        col_chk, col_card = st.columns([0.1, 0.9])
        with col_chk:
            st.write("")
            st.write("")
            adopt = st.checkbox("", key=f"adopt_lever_{idx}", value=True)
        with col_card:
            diff_badge = "#DCFCE7" if lev["difficulty"] == "Easy" else ("#FEF3C7" if lev["difficulty"] == "Medium" else "#FEE2E2")
            diff_color = "#15803D" if lev["difficulty"] == "Easy" else ("#B45309" if lev["difficulty"] == "Medium" else "#B91C1C")

            st.markdown(
                f"""
                <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px; margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: {PRIMARY_TEAL}; font-size: 0.95rem;">
                            #{idx} • {lev['category']} (Current: {format_inr(lev['current_spend'])})
                        </span>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <span style="background-color: {diff_badge}; color: {diff_color}; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600;">
                                {lev['difficulty']} Effort
                            </span>
                            <span style="font-weight: 800; color: #16A34A; font-size: 1.1rem;">
                                ~+{format_inr(lev['est_monthly_saving'])}/mo
                            </span>
                        </div>
                    </div>
                    <h4 style="margin: 6px 0; color: {TEXT_NAVY};">{lev['title']}</h4>
                    <p style="margin: 0; color: #475569; font-size: 0.88rem; line-height: 1.4;">{lev['action']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

        if adopt:
            selected_savings += lev["est_monthly_saving"]

    # Interactive Recalculation Summary Card
    st.markdown("---")
    st.markdown(
        f"""
        <div style="background-color: #E6F4F2; border: 2px solid {PRIMARY_TEAL}; border-radius: 12px; padding: 18px; text-align: center; margin-top: 1rem;">
            <h4 style="margin: 0; color: {TEXT_NAVY};">💡 Total Reclaimed Monthly Cash Flow</h4>
            <div style="font-size: 2.2rem; font-weight: 900; color: {PRIMARY_TEAL}; margin: 8px 0;">
                +{format_inr(selected_savings)}/month
            </div>
            <p style="margin: 0; color: #475569; font-size: 0.95rem;">
                Adopting your selected levers frees up approximately <strong>{format_inr(selected_savings * 12)} per year</strong>, 
                which can be redirected to your liquid emergency fund or child education milestone SIPs.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    render_footer()


if __name__ == "__main__":
    show_reduce_expenses_page()
