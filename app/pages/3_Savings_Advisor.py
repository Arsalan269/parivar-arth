"""
Savings Advisor & Goal Planner Page for Parivar Arth.
Includes:
1. Actionable savings levers ranked by monthly rupee impact
2. Indian Household Consumption Expenditure Survey (HCES) peer benchmarks
3. Inflation-adjusted savings goal feasibility calculator
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
from app.styles import apply_theme, render_header, render_footer, PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
from app.components.formatters import format_inr


def show_savings_advisor_page():
    st.set_page_config(page_title="Savings Advisor - Parivar Arth", page_icon=None, layout="centered")
    apply_theme()
    touch_session()

    user_id = get_current_user_id()
    if not user_id:
        st.warning("Please sign in to access your personalized savings advisor.")
        st.stop()

    render_header(
        title="Savings Advisor & Goals",
        subtitle="Ranked savings recommendations and inflation-adjusted milestone planning"
    )

    with get_db_session() as db:
        profile_data = get_household_profile(db, user_id)
        user_expenses = get_user_expenses(db, user_id)
        saved_goals = db.query(Goal).filter(Goal.user_id == user_id).all()

    incomes = profile_data["incomes"]
    obligations = profile_data["obligations"]
    loans = profile_data["loans"]
    assets = profile_data["assets"]
    prof = profile_data["profile"]

    total_income = sum(i.amount for i in incomes)
    monthly_fixed = sum(o.amount for o in obligations)
    monthly_emis = sum(l.emi for l in loans)
    monthly_var_expenses = sum(e.amount for e in user_expenses) if user_expenses else (monthly_fixed * 0.25)
    total_monthly_spending = monthly_fixed + monthly_emis + monthly_var_expenses
    liquid_reserves = sum(a.amount for a in assets if a.is_liquid)

    loan_dicts = [{"id": l.id, "balance": l.balance, "interest_rate": l.interest_rate, "emi": l.emi} for l in loans]
    
    # Generate recommendations
    recs = generate_savings_recommendations(
        monthly_income=total_income,
        monthly_expenses=total_monthly_spending,
        liquid_emergency_fund=liquid_reserves,
        loans=loan_dicts,
        wants_spending=monthly_var_expenses * 0.4
    )

    tab_recs, tab_benchmarks, tab_goals = st.tabs(["High-Impact Levers", "Peer Benchmarks", "Goal Planner"])

    # ---------------- TAB 1: SAVINGS RECOMMENDATIONS ----------------
    with tab_recs:
        st.markdown("#### Prioritized Savings Levers (Ranked by Rupee Impact)")
        st.caption("Focus on the highest rupee return first to maximize family financial headroom.")

        if recs:
            for r in recs:
                st.markdown(
                    f"""
                    <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; margin-bottom: 1rem; box-shadow: 0 1px 4px rgba(0,0,0,0.04);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="background-color: #E6F4F2; color: {PRIMARY_TEAL}; padding: 3px 10px; border-radius: 999px; font-size: 0.8rem; font-weight: bold;">
                                #{r['priority']} • {r['category']}
                            </span>
                            <span style="font-weight: 800; color: #16A34A; font-size: 1.05rem;">
                                +{format_inr(r['rupee_impact'])}/mo potential
                            </span>
                        </div>
                        <h4 style="margin: 4px 0 6px 0; color: {TEXT_NAVY};">{r['title']}</h4>
                        <p style="margin: 0; color: #475569; font-size: 0.9rem; line-height: 1.4;">{r['advice']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No immediate savings red-flags detected. Your household savings rate is strong!")

    # ---------------- TAB 2: PEER BENCHMARKS ----------------
    with tab_benchmarks:
        st.markdown("#### Household Consumption Survey Peer Comparison")
        st.markdown(
            """
            How does your family's allocation compare to similar households in your city tier?
            *(Data source: MoSPI Household Consumption Expenditure Survey benchmarks).*
            """
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

        st.caption(f"Note: {bench['note']}")

    # ---------------- TAB 3: GOAL PLANNER ----------------
    with tab_goals:
        st.markdown("#### Inflation-Adjusted Goal Calculator")
        st.caption("Plan for marriage, vehicle purchase, or home downpayment with compounding inflation.")

        with st.form("goal_calculator_form"):
            g_name = st.text_input("Goal Name", value="Home Downpayment / Renovation")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                g_target = st.number_input("Target Amount in Today's Money (₹)", min_value=10000.0, value=1500000.0, step=50000.0)
                g_years = st.number_input("Years to Goal", min_value=0.5, max_value=30.0, value=5.0, step=0.5)
            with col_g2:
                g_inf = st.number_input("Assumed Inflation Rate (%/yr)", min_value=2.0, max_value=15.0, value=6.0, step=0.5)
                g_roi = st.number_input("Expected Investment Growth (%/yr)", min_value=4.0, max_value=18.0, value=10.0, step=0.5)

            calc_btn = st.form_submit_button("Calculate Inflation-Adjusted Monthly SIP", type="primary")

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
                <div style="background-color: #E6F4F2; border: 1px solid #86EFAC; border-radius: 12px; padding: 18px; margin-top: 1rem;">
                    <h3 style="color: {PRIMARY_TEAL}; margin-top: 0;">Goal Projection: {res['goal_name']}</h3>
                    <div style="display: flex; gap: 24px; flex-wrap: wrap;">
                        <div>
                            <span style="font-size: 0.85rem; color: #475569;">Target in Today's Rupees</span><br>
                            <strong style="font-size: 1.25rem; color: {TEXT_NAVY};">{format_inr(res['original_target'])}</strong>
                        </div>
                        <div>
                            <span style="font-size: 0.85rem; color: #475569;">Future Cost in {res['years']} Years ({g_inf}% Inflation)</span><br>
                            <strong style="font-size: 1.25rem; color: #DC2626;">{format_inr(res['inflated_target'])}</strong>
                        </div>
                        <div>
                            <span style="font-size: 0.85rem; color: #475569;">Required Monthly Investment (at {g_roi}% CAGR)</span><br>
                            <strong style="font-size: 1.4rem; color: {PRIMARY_TEAL};">{format_inr(res['monthly_sip_needed'])}/mo</strong>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    render_footer()


if __name__ == "__main__":
    show_savings_advisor_page()
