"""
Loans, Debt Optimization & Emergency Fund Tracker for Parivar Arth.
Aether FinTech Design System - Dynamic Runway, DTI Health, Prepayment Strategies, and Repo Shock Simulator.
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
from app.styles import (
    apply_theme, render_header, render_footer, render_metric_card,
    render_sidebar_brand, render_sidebar_user,
    PRIMARY_ACCENT, SECONDARY_ACCENT, SOFT_PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER_COLOR,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
)
from app.components.formatters import format_inr, format_pct


def show_loans_emergency_page():
    st.set_page_config(
        page_title="Loans & Emergency - Parivar Arth",
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
        st.warning("Please sign in to access your debt and emergency fund dashboard.")
        st.stop()

    with st.sidebar:
        user_name = user_data.get("name", "Household Account") if user_data else "User"
        render_sidebar_user(username=user_name, role="Primary Account")
        if st.button("Sign Out", key="le_logout_btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    render_header(
        title="Loans, Debt & Emergency Runway",
        subtitle="Household solvency, DTI risk analysis, prepayment strategy, and RBI repo rate shock modeling",
        tag="Balance Sheet"
    )

    with get_db_session() as db:
        profile_data = get_household_profile(db, user_id)

    members = profile_data.get("members", [])
    incomes = profile_data.get("incomes", [])
    obligations = profile_data.get("obligations", [])
    loans = profile_data.get("loans", [])
    assets = profile_data.get("assets", [])

    total_income = sum(float(getattr(i, "amount", 0.0)) for i in incomes)
    monthly_fixed_costs = sum(float(getattr(o, "amount", 0.0)) for o in obligations)
    total_emis = sum(float(getattr(l, "emi", 0.0)) for l in loans)
    monthly_essentials = monthly_fixed_costs + total_emis

    is_single = len(incomes) <= 1
    has_var = any(bool(getattr(i, "is_variable", False)) for i in incomes)
    has_chronic = any(bool(getattr(m, "has_chronic_condition", False)) for m in members)

    target_months, target_explanation = determine_emergency_fund_target_months(
        is_single_earner=is_single,
        has_variable_income=has_var,
        has_chronic_dependents=has_chronic
    )

    asset_dicts = [{"type": getattr(a, "type", "Asset"), "amount": float(getattr(a, "amount", 0.0)), "is_liquid": getattr(a, "is_liquid", False)} for a in assets]
    ef_data = calculate_liquid_emergency_fund(asset_dicts, monthly_essentials, target_months=target_months)

    tab_emergency, tab_loans, tab_repo = st.tabs([
        "Emergency Fund Runway",
        "Debt Health & Prepayment",
        "RBI Repo Rate Shock Simulator"
    ])

    # ---------------- TAB 1: EMERGENCY FUND ----------------
    with tab_emergency:
        st.markdown(
            f"""
            <div class="aether-card" style="margin-top: 0.5rem; margin-bottom: 1.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div style="font-size: 1.1rem; font-weight: 700; color: {TEXT_PRIMARY};">
                        Emergency Runway Status: {ef_data['badge']}
                    </div>
                    <span class="status-badge status-purple">{ef_data['badge']}</span>
                </div>
                <div style="font-size: 0.9rem; color: {TEXT_SECONDARY}; line-height: 1.5;">{ef_data['advice']}</div>
                <div style="font-size: 0.82rem; color: {PRIMARY_ACCENT}; margin-top: 4px; font-weight: 500;">{target_explanation}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            render_metric_card(
                label="Total Liquid Reserves",
                value=format_inr(ef_data["total_liquid"]),
                subtext="Savings account + FDs only",
                badge_text="Liquid Buffer",
                badge_type="purple"
            )
        with col2:
            render_metric_card(
                label="Monthly Essential Burn",
                value=format_inr(monthly_essentials),
                subtext="Fixed obligations + loan EMIs",
                badge_text="Essential Burn",
                badge_type="watch"
            )
        with col3:
            runway_type = "safe" if ef_data['runway_months'] >= target_months else "risk"
            render_metric_card(
                label="Runway Available",
                value=f"{ef_data['runway_months']:.1f} Months",
                subtext=f"Target: {target_months} months based on profile",
                badge_text=runway_type.upper(),
                badge_type=runway_type
            )

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; font-size: 0.88rem; font-weight: 600; color: {TEXT_PRIMARY}; margin-bottom: 4px;">
                <span>Target Funding Progress</span>
                <span>{format_inr(ef_data['total_liquid'])} of {format_inr(ef_data['target_amount'])} ({ef_data['progress_pct']}%)</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.progress(min(1.0, ef_data["progress_pct"] / 100.0))

        st.markdown(
            f"""
            <div style="margin-top: 1.5rem; margin-bottom: 0.75rem;">
                <h4 style="color: {TEXT_PRIMARY}; font-weight: 700; margin: 0;">Liquid Assets vs. Excluded Illiquid Assets</h4>
                <p style="color: {TEXT_SECONDARY}; font-size: 0.85rem; margin: 2px 0 0 0;">Parivar Arth strictly excludes property and lock-in PF from emergency runway</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if ef_data["breakdown"]:
            df_assets = pd.DataFrame(ef_data["breakdown"])
            st.dataframe(df_assets, use_container_width=True)
        else:
            st.info("No assets recorded yet. Add savings accounts or fixed deposits under 'My Profile'.")

    # ---------------- TAB 2: DEBT & PREPAYMENT ----------------
    with tab_loans:
        dti_pct, dti_status, dti_advice = calculate_dti(total_emis, total_income)

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            total_debt_val = sum(float(getattr(l, "balance", 0.0)) for l in loans)
            render_metric_card(
                label="Total Outstanding Debt",
                value=format_inr(total_debt_val),
                subtext="Across all registered loans",
                badge_text="Principal",
                badge_type="purple"
            )
        with col_d2:
            dti_type = "safe" if "healthy" in dti_status.lower() or "safe" in dti_status.lower() else ("watch" if "moderate" in dti_status.lower() else "risk")
            render_metric_card(
                label="Debt-to-Income (DTI)",
                value=f"{dti_pct}%",
                subtext=f"Status: {dti_status}",
                badge_text=dti_status.upper(),
                badge_type=dti_type
            )

        st.markdown(
            f"""
            <div class="aether-card" style="margin-top: 1rem; margin-bottom: 1.25rem; padding: 12px 16px;">
                <div style="font-size: 0.88rem; color: {TEXT_SECONDARY}; line-height: 1.5;">
                    <strong>Banking Underwriting Guidance:</strong> {dti_advice}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="margin-top: 1.25rem; margin-bottom: 0.5rem;">
                <h4 style="color: {TEXT_PRIMARY}; font-weight: 700; margin: 0;">Prepayment Acceleration Strategy</h4>
                <p style="color: {TEXT_SECONDARY}; font-size: 0.85rem; margin: 2px 0 0 0;">Compare Avalanche (interest minimization) vs Snowball (psychological momentum)</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        extra_prepay = st.number_input("Extra Monthly Debt Prepayment (₹)", min_value=1000.0, value=5000.0, step=1000.0)
        loan_dicts = [{"id": l.id, "loan_type": l.loan_type, "balance": l.balance, "interest_rate": l.interest_rate, "emi": l.emi, "remaining_months": l.remaining_months, "rate_type": l.rate_type} for l in loans]

        ranks = rank_debt_prepayments(loan_dicts, extra_monthly_prepayment=extra_prepay)

        col_av, col_sn = st.columns(2)
        with col_av:
            st.markdown(
                f"""
                <div class="aether-card">
                    <div style="font-weight: 700; color: {PRIMARY_ACCENT}; font-size: 1.05rem; margin-bottom: 4px;">
                        Avalanche Method (Highest APR First)
                    </div>
                    <div style="font-size: 0.82rem; color: {TEXT_SECONDARY}; margin-bottom: 12px;">
                        Mathematically saves the highest interest in rupees.
                    </div>
                """,
                unsafe_allow_html=True
            )
            for r in ranks["avalanche"]:
                st.info(r["recommendation"])
            st.markdown("</div>", unsafe_allow_html=True)

        with col_sn:
            st.markdown(
                f"""
                <div class="aether-card">
                    <div style="font-weight: 700; color: {COLOR_SUCCESS}; font-size: 1.05rem; margin-bottom: 4px;">
                        Snowball Method (Smallest Balance First)
                    </div>
                    <div style="font-size: 0.82rem; color: {TEXT_SECONDARY}; margin-bottom: 12px;">
                        Closes individual loans quickly to build psychological momentum.
                    </div>
                """,
                unsafe_allow_html=True
            )
            for r in ranks["snowball"]:
                st.success(r["recommendation"])
            st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- TAB 3: REPO SENSITIVITY ----------------
    with tab_repo:
        st.markdown(
            f"""
            <div style="margin-top: 0.5rem; margin-bottom: 1.25rem;">
                <h4 style="color: {TEXT_PRIMARY}; font-weight: 700; margin: 0;">RBI Repo Rate Floating Loan Sensitivity Shock</h4>
                <p style="color: {TEXT_SECONDARY}; font-size: 0.88rem; margin: 2px 0 0 0;">
                    Simulate how RBI policy rate adjustments pass through to your external benchmark home loan EMIs.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        floating_loans = [l for l in loans if str(l.rate_type).lower() == "floating" or "home" in str(l.loan_type).lower()]
        if not floating_loans:
            st.info("No floating rate loans registered in your profile. Below is a simulation on a standard ₹40 Lakh Home Loan:")
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
            "Simulated RBI Repo Rate Hike (basis points):",
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
            render_metric_card(
                label="Current EMI",
                value=format_inr(shock_res["current_emi"]),
                subtext=f"Base Rate: {sim_rate:.2f}%",
                badge_text="Current",
                badge_type="purple"
            )
        with col_s2:
            render_metric_card(
                label="Shocked EMI",
                value=format_inr(shock_res["new_emi"]),
                subtext=f"New Rate: {shock_res['new_rate']}%",
                badge_text="Adjusted",
                badge_type="watch"
            )
        with col_s3:
            render_metric_card(
                label="Monthly Outflow Surge",
                value=f"+{format_inr(shock_res['emi_increase'])}",
                subtext="Direct additional monthly drain",
                badge_text="Surge",
                badge_type="risk"
            )

        st.markdown(
            f"""
            <div class="aether-card" style="margin-top: 1.25rem; border-left: 4px solid {COLOR_WARNING};">
                <div style="font-weight: 700; color: {COLOR_WARNING}; font-size: 0.95rem; margin-bottom: 4px;">
                    Tenure Extension Warning
                </div>
                <div style="font-size: 0.88rem; color: {TEXT_PRIMARY}; line-height: 1.5;">
                    If your lender keeps your EMI payment fixed instead of raising it, your loan tenure will automatically extend by
                    <strong>+{shock_res['tenure_extension_months']} months</strong> (~{shock_res['tenure_extension_months'] // 12} years),
                    adding significant compounding interest over the life of your mortgage.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    render_footer()


if __name__ == "__main__":
    show_loans_emergency_page()
