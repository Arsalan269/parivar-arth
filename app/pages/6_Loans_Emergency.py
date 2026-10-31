"""
Loans, Debt Optimization & Emergency Fund Tracker for Parivar Arth.
Includes:
1. Dynamic 3 vs 6-Month Emergency Runway using strictly liquid reserves
2. Debt-to-Income (DTI) ratio analyzer
3. Prepayment Prioritization: Avalanche (highest rate) vs Snowball (smallest balance)
4. RBI Repo Rate Floating Loan Sensitivity Shock Simulator
"""

import os
import sys
import streamlit as st
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import get_db_session
from core.models import Loan, Asset
from core.security import touch_session, get_current_user_id
from core.profile_service import get_household_profile
from planner.emergency import determine_emergency_fund_target_months, calculate_liquid_emergency_fund
from planner.loans import calculate_dti, simulate_floating_repo_shock, rank_debt_prepayments
from app.styles import apply_theme, render_header, render_footer, PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
from app.components.formatters import format_inr, format_pct


def show_loans_emergency_page():
    st.set_page_config(page_title="Loans & Emergency Fund - Parivar Arth", page_icon=None, layout="centered")
    apply_theme()
    touch_session()

    user_id = get_current_user_id()
    if not user_id:
        st.warning("Please sign in to access your debt and emergency fund dashboard.")
        st.stop()

    render_header(
        title="Loans & Emergency Fund Health",
        subtitle="Manage debt stress, repo-rate sensitivity, and household emergency runway"
    )

    with get_db_session() as db:
        profile_data = get_household_profile(db, user_id)

    members = profile_data["members"]
    incomes = profile_data["incomes"]
    obligations = profile_data["obligations"]
    loans = profile_data["loans"]
    assets = profile_data["assets"]

    total_income = sum(i.amount for i in incomes)
    monthly_fixed_costs = sum(o.amount for o in obligations)
    total_emis = sum(l.emi for l in loans)
    monthly_essentials = monthly_fixed_costs + total_emis

    # Check risk profile
    is_single = len(incomes) <= 1
    has_var = any(i.is_variable for i in incomes)
    has_chronic = any(m.has_chronic_condition for m in members)

    target_months, target_explanation = determine_emergency_fund_target_months(
        is_single_earner=is_single,
        has_variable_income=has_var,
        has_chronic_dependents=has_chronic
    )

    # Compute emergency fund
    asset_dicts = [{"type": a.type, "amount": a.amount, "is_liquid": a.is_liquid} for a in assets]
    ef_data = calculate_liquid_emergency_fund(asset_dicts, monthly_essentials, target_months=target_months)

    tab_emergency, tab_loans, tab_repo = st.tabs(["Emergency Fund Runway", "Debt & Prepayment", "Repo Rate Sensitivity"])

    # ---------------- TAB 1: EMERGENCY FUND ----------------
    with tab_emergency:
        st.markdown(
            f"""
            <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0; color: {PRIMARY_TEAL};">Emergency Runway Status</h4>
                    <span style="font-size: 1.1rem; font-weight: bold;">{ef_data['badge']}</span>
                </div>
                <p style="margin: 6px 0 0 0; color: #475569; font-size: 0.95rem;">{ef_data['advice']}</p>
                <p style="margin: 4px 0 0 0; color: #64748B; font-size: 0.85rem;"><em>{target_explanation}</em></p>
            </div>
            """,
            unsafe_allow_html=True
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Liquid Reserves", format_inr(ef_data["total_liquid"]))
        with col2:
            st.metric("Monthly Essential Needs", format_inr(monthly_essentials))
        with col3:
            st.metric("Runway Available", f"{ef_data['runway_months']} Months")

        st.markdown(f"**Emergency Target Progress ({format_inr(ef_data['total_liquid'])} of {format_inr(ef_data['target_amount'])})**")
        st.progress(ef_data["progress_pct"] / 100.0)

        st.markdown("#### Counted Liquid Assets vs. Excluded Illiquid Assets")
        if ef_data["breakdown"]:
            st.dataframe(pd.DataFrame(ef_data["breakdown"]), use_container_width=True)
        else:
            st.info("No assets recorded. Add savings accounts or fixed deposits under My Household Profile.")

    # ---------------- TAB 2: DEBT & PREPAYMENT ----------------
    with tab_loans:
        dti_pct, dti_status, dti_advice = calculate_dti(total_emis, total_income)

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.metric("Total Outstanding Debt", format_inr(sum(l.balance for l in loans)))
        with col_d2:
            st.metric("Debt-to-Income (DTI)", f"{dti_pct}%", f"[{dti_status}]")

        st.caption(f"**Banking Guidance:** {dti_advice}")

        st.markdown("---")
        st.markdown("#### Prepayment Strategy: Avalanche vs. Snowball")
        st.write("Accelerate debt freedom by deploying an extra prepayment each month:")

        extra_prepay = st.number_input("Extra Monthly Debt Prepayment (₹)", min_value=1000.0, value=5000.0, step=1000.0)
        loan_dicts = [{"id": l.id, "loan_type": l.loan_type, "balance": l.balance, "interest_rate": l.interest_rate, "emi": l.emi, "remaining_months": l.remaining_months, "rate_type": l.rate_type} for l in loans]
        
        ranks = rank_debt_prepayments(loan_dicts, extra_monthly_prepayment=extra_prepay)

        col_av, col_sn = st.columns(2)
        with col_av:
            st.markdown("##### Avalanche (Highest APR First)")
            st.caption("Mathematically saves the highest interest in rupees.")
            for r in ranks["avalanche"]:
                st.info(r["recommendation"])

        with col_sn:
            st.markdown("##### Snowball (Smallest Balance First)")
            st.caption("Eliminates loan counts fast for psychological momentum.")
            for r in ranks["snowball"]:
                st.success(r["recommendation"])

    # ---------------- TAB 3: REPO SENSITIVITY ----------------
    with tab_repo:
        st.markdown("#### RBI Repo Rate Floating Loan Sensitivity Shock")
        st.markdown(
            """
            When the Reserve Bank of India increases the policy repo rate, banks immediately pass on 
            the increase to external benchmark linked floating rate loans (Home Loans, LAP).
            """
        )

        floating_loans = [l for l in loans if str(l.rate_type).lower() == "floating" or "home" in str(l.loan_type).lower()]
        if not floating_loans:
            st.info("You have no floating rate loans registered in your profile. You can simulate on a sample ₹40 Lakh Home Loan below:")
            sim_balance = 4000000.0
            sim_rate = 8.5
            sim_months = 240
        else:
            fl = floating_loans[0]
            sim_balance = fl.balance
            sim_rate = fl.interest_rate
            sim_months = fl.remaining_months
            st.markdown(f"**Evaluating active floating loan:** `{fl.loan_type}` (Balance: {format_inr(sim_balance)}, Rate: {sim_rate}%)")

        shock_bps = st.select_slider(
            "Hypothetical RBI Repo Rate Hike (basis points):",
            options=[25, 50, 75, 100, 150],
            value=50,
            format_func=lambda x: f"+{x} bps (+{x/100:.2f}%)"
        )

        shock_res = simulate_floating_repo_shock(
            principal_balance=sim_balance,
            current_annual_rate=sim_rate,
            remaining_months=sim_months,
            repo_change_bps=shock_bps
        )

        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("Current EMI", format_inr(shock_res["current_emi"]))
        with col_s2:
            st.metric(f"New EMI (at {shock_res['new_rate']}%)", format_inr(shock_res["new_emi"]))
        with col_s3:
            st.metric("Monthly Outflow Increase", f"+{format_inr(shock_res['emi_increase'])}")

        st.warning(
            f"**Tenure Impact Option:** If your bank keeps your monthly EMI fixed instead of increasing it, "
            f"your loan tenure will automatically extend by **+{shock_res['tenure_extension_months']} months** "
            f"(~{shock_res['tenure_extension_months'] // 12} years), resulting in substantial additional interest paid to the lender."
        )

    render_footer()


if __name__ == "__main__":
    show_loans_emergency_page()
