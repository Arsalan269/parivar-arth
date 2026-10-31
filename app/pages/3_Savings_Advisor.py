"""
Savings Advisor & Goal Planner Page for Parivar Arth.
Aether FinTech Design System - Ranked Levers, MoSPI Peer Benchmarks, and Inflation-Adjusted Goals.
"""

import os
import sys
import streamlit as st
import pandas as pd
import plotly.express as px

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import get_db_session
from core.models import Goal
from core.security import touch_session, get_current_user_id
from core.profile_service import get_household_profile
from core.expense_service import get_user_expenses
from planner.savings import generate_savings_recommendations, compare_with_consumption_benchmarks
from planner.family_goals import compute_goal_feasibility
from app.styles import (
    apply_theme, render_header, render_footer, render_metric_card,
    render_sidebar_brand, render_sidebar_user,
    PRIMARY_ACCENT, SECONDARY_ACCENT, SOFT_PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER_COLOR,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
)
from app.components.formatters import format_inr


def show_savings_advisor_page():
    st.set_page_config(
        page_title="Savings Advisor - Parivar Arth",
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
        st.warning("Please sign in to access your personalized savings advisor.")
        st.stop()

    with st.sidebar:
        user_name = user_data.get("name", "Household Account") if user_data else "User"
        render_sidebar_user(username=user_name, role="Primary Account")
        if st.button("Sign Out", key="sa_logout_btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    render_header(
        title="Savings Advisor & Wealth Goals",
        subtitle="Prioritized savings levers, MoSPI consumption benchmarks, and inflation-adjusted milestone planning",
        tag="Advisory"
    )

    with get_db_session() as db:
        profile_data = get_household_profile(db, user_id)
        user_expenses = get_user_expenses(db, user_id)
        saved_goals = db.query(Goal).filter(Goal.user_id == user_id).all()

    incomes = profile_data.get("incomes", [])
    obligations = profile_data.get("obligations", [])
    loans = profile_data.get("loans", [])
    assets = profile_data.get("assets", [])
    prof = profile_data.get("profile")

    total_income = sum(float(getattr(i, "amount", 0.0)) for i in incomes)
    monthly_fixed = sum(float(getattr(o, "amount", 0.0)) for o in obligations)
    monthly_emis = sum(float(getattr(l, "emi", 0.0)) for l in loans)
    monthly_var_expenses = sum(float(getattr(e, "amount", 0.0)) for e in user_expenses) if user_expenses else (monthly_fixed * 0.25)
    total_monthly_spending = monthly_fixed + monthly_emis + monthly_var_expenses
    liquid_reserves = sum(float(getattr(a, "amount", 0.0)) for a in assets if getattr(a, "is_liquid", False))

    loan_dicts = [{"id": l.id, "balance": l.balance, "interest_rate": l.interest_rate, "emi": l.emi} for l in loans]

    # Generate recommendations
    recs = generate_savings_recommendations(
        monthly_income=total_income,
        monthly_expenses=total_monthly_spending,
        liquid_emergency_fund=liquid_reserves,
        loans=loan_dicts,
        wants_spending=monthly_var_expenses * 0.4
    )

    # Top Overview Metrics
    m1, m2, m3 = st.columns(3)
    with m1:
        render_metric_card(
            label="Total Monthly Inflow",
            value=format_inr(total_income),
            subtext="Baseline household income",
            badge_text="Inflows",
            badge_type="purple"
        )
    with m2:
        render_metric_card(
            label="Monthly Outflow Total",
            value=format_inr(total_monthly_spending),
            subtext="Fixed + EMI + variable spend",
            badge_text="Outflows",
            badge_type="watch"
        )
    with m3:
        potential_reclaim = sum(r.get("rupee_impact", 0) for r in recs)
        render_metric_card(
            label="Reclaim Potential",
            value=f"+{format_inr(potential_reclaim)}/mo",
            subtext="From top prioritized levers",
            badge_text="Opportunity",
            badge_type="safe"
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    tab_recs, tab_benchmarks, tab_goals = st.tabs([
        "High-Impact Savings Levers",
        "Peer Consumption Benchmarks",
        "Goal Feasibility Planner"
    ])

    # ---------------- TAB 1: SAVINGS RECOMMENDATIONS ----------------
    with tab_recs:
        st.markdown(
            f"""
            <div style="margin-top: 0.5rem; margin-bottom: 1.25rem;">
                <h4 style="color: {TEXT_PRIMARY}; font-weight: 700; margin: 0;">Prioritized Savings Levers</h4>
                <p style="color: {TEXT_SECONDARY}; font-size: 0.88rem; margin: 2px 0 0 0;">Ranked by monthly rupee impact to deliver immediate headroom to your family</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        if recs:
            for r in recs:
                st.markdown(
                    f"""
                    <div class="aether-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span class="status-badge status-purple">
                                Priority #{r['priority']} • {r['category']}
                            </span>
                            <span style="font-weight: 800; color: {COLOR_SUCCESS}; font-size: 1.05rem;">
                                +{format_inr(r['rupee_impact'])}/mo potential
                            </span>
                        </div>
                        <h4 style="margin: 6px 0 4px 0; color: {TEXT_PRIMARY}; font-size: 1.05rem;">{r['title']}</h4>
                        <p style="margin: 0; color: {TEXT_SECONDARY}; font-size: 0.9rem; line-height: 1.5;">{r['advice']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No urgent savings flags detected. Your household savings rate is on a healthy track.")

    # ---------------- TAB 2: PEER BENCHMARKS ----------------
    with tab_benchmarks:
        st.markdown(
            f"""
            <div style="margin-top: 0.5rem; margin-bottom: 1.25rem;">
                <h4 style="color: {TEXT_PRIMARY}; font-weight: 700; margin: 0;">MoSPI Household Consumption Benchmarks</h4>
                <p style="color: {TEXT_SECONDARY}; font-size: 0.88rem; margin: 2px 0 0 0;">
                    How your family's essential spending compares to peer households in your city classification.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        city_type = prof.city_type if prof else "Metro (Tier-1)"
        food_spend = next((o.amount for o in obligations if "grocer" in o.category.lower() or "food" in o.category.lower()), total_monthly_spending * 0.3)
        rent_spend = next((o.amount for o in obligations if "rent" in o.category.lower() or "hous" in o.category.lower()), total_monthly_spending * 0.25)

        bench = compare_with_consumption_benchmarks(
            city_type=city_type,
            household_size=prof.household_size if prof else 3,
            monthly_income=total_income,
            current_food_spend=food_spend,
            current_rent_spend=rent_spend
        )

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.metric(
                "Food & Groceries Share",
                f"{bench['actual_food_pct']}% of income",
                f"{bench['food_diff_pct']:+0.1f}% vs {city_type} benchmark ({bench['benchmark_food_pct']}%)",
                delta_color="inverse"
            )
        with col_b2:
            st.metric(
                "Rent & Housing Share",
                f"{bench['actual_rent_pct']}% of income",
                f"{bench['rent_diff_pct']:+0.1f}% vs {city_type} benchmark ({bench['benchmark_rent_pct']}%)",
                delta_color="inverse"
            )

        st.markdown(
            f"""
            <div class="aether-card" style="margin-top: 1rem; padding: 12px 16px;">
                <div style="font-size: 0.85rem; color: {TEXT_SECONDARY}; line-height: 1.5;">
                    <strong>Benchmark Observation:</strong> {bench['note']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ---------------- TAB 3: GOAL PLANNER ----------------
    with tab_goals:
        st.markdown(
            f"""
            <div style="margin-top: 0.5rem; margin-bottom: 1.25rem;">
                <h4 style="color: {TEXT_PRIMARY}; font-weight: 700; margin: 0;">Inflation-Adjusted Goal Calculator</h4>
                <p style="color: {TEXT_SECONDARY}; font-size: 0.88rem; margin: 2px 0 0 0;">
                    Model home downpayments, car purchases, or weddings with realistic compounding inflation.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("goal_calculator_form"):
            g_name = st.text_input("Goal Name", value="Home Downpayment / Renovation")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                g_target = st.number_input("Target Amount in Today's Money (₹)", min_value=10000.0, value=1500000.0, step=50000.0)
                g_years = st.number_input("Years to Horizon", min_value=0.5, max_value=30.0, value=5.0, step=0.5)
            with col_g2:
                g_inf = st.number_input("Assumed Inflation Rate (%/yr)", min_value=2.0, max_value=15.0, value=6.0, step=0.5)
                g_roi = st.number_input("Expected Investment Growth (%/yr CAGR)", min_value=4.0, max_value=18.0, value=10.0, step=0.5)

            calc_btn = st.form_submit_button("Calculate Required Monthly Investment", type="primary")

        if calc_btn or g_name:
            res = compute_goal_feasibility(
                goal_name=g_name,
                target_amount=g_target,
                target_years=g_years,
                general_inflation_rate=g_inf,
                expected_return_rate=g_roi
            )

            st.markdown(
                f"""
                <div class="aether-card" style="border-left: 4px solid {PRIMARY_ACCENT}; margin-top: 1.5rem;">
                    <div style="font-size: 1.15rem; font-weight: 700; color: {TEXT_PRIMARY}; margin-bottom: 12px;">
                        Goal Projection: {res['goal_name']}
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                        <div>
                            <div style="font-size: 0.75rem; color: {TEXT_SECONDARY}; text-transform: uppercase; font-weight: 600;">Today's Target</div>
                            <div style="font-size: 1.3rem; font-weight: 800; color: {TEXT_PRIMARY};">{format_inr(res['original_target'])}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: {COLOR_DANGER}; text-transform: uppercase; font-weight: 600;">Inflated Cost ({res['years']} Yrs @ {g_inf}%)</div>
                            <div style="font-size: 1.3rem; font-weight: 800; color: {COLOR_DANGER};">{format_inr(res['inflated_target'])}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: {PRIMARY_ACCENT}; text-transform: uppercase; font-weight: 600;">Required Monthly SIP (@ {g_roi}% CAGR)</div>
                            <div style="font-size: 1.45rem; font-weight: 800; color: {PRIMARY_ACCENT};">{format_inr(res['monthly_sip_needed'])}/mo</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    render_footer()


if __name__ == "__main__":
    show_savings_advisor_page()
