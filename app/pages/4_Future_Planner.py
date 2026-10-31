"""
Future Planner, Shortfall Predictor & Monte Carlo Simulation for Parivar Arth.
The flagship engine: combines category-specific ML forecasts, 1,000-run Monte Carlo simulations,
what-if shocks, and family milestone projections.
"""

import os
import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import get_db_session
from core.models import Forecast
from core.security import touch_session, get_current_user_id
from core.profile_service import get_household_profile
from planner.shortfall import compute_shortfall_timeline
from planner.montecarlo import run_monte_carlo_shortfall_simulation
from planner.family_goals import compute_education_milestones, evaluate_parent_medical_provision
from app.styles import apply_theme, render_header, render_footer, PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
from app.components.formatters import format_inr, format_pct


def show_future_planner_page():
    st.set_page_config(page_title="Future Planner & Shortfall Engine - Parivar Arth", page_icon=None, layout="centered")
    apply_theme()
    touch_session()

    user_id = get_current_user_id()
    if not user_id:
        st.warning("Please sign in to view your family's future inflation and shortfall projections.")
        st.stop()

    render_header(
        title="Future Shortfall Predictor",
        subtitle="Forecasted category inflation applied to your real household finances"
    )

    with get_db_session() as db:
        profile_data = get_household_profile(db, user_id)
        forecast_rows = db.query(Forecast).all()

    incomes = profile_data["incomes"]
    obligations = profile_data["obligations"]
    loans = profile_data["loans"]
    members = profile_data["members"]
    assets = profile_data["assets"]

    total_income = sum(i.amount for i in incomes)
    monthly_emis = sum(l.emi for l in loans)
    liquid_reserves = sum(a.amount for a in assets if a.is_liquid)
    obligation_dicts = [{"category": o.category, "amount": o.amount} for o in obligations]

    # Map forecast intervals per category
    category_intervals = {}
    for f in forecast_rows:
        if f.category not in category_intervals:
            category_intervals[f.category] = (f.lower_ci, f.predicted_inflation, f.upper_ci)

    tab_shortfall, tab_montecarlo, tab_whatif, tab_milestones = st.tabs([
        "24-Month Shortfall Timeline",
        "Monte Carlo Risk (1,000 Runs)",
        "What-If Scenarios & Shocks",
        "Family Planning Milestones"
    ])

    # ---------------- TAB 1: SHORTFALL TIMELINE ----------------
    with tab_shortfall:
        col_ctrl1, col_ctrl2 = st.columns(2)
        with col_ctrl1:
            annual_hike = st.slider("Expected Annual Salary / Income Hike (%/year)", 0.0, 15.0, 6.0, 0.5)
        with col_ctrl2:
            min_savings = st.slider("Target Monthly Savings Reserve (% of income)", 0.0, 30.0, 10.0, 2.0)

        shortfall_res = compute_shortfall_timeline(
            current_monthly_income=total_income,
            obligations=obligation_dicts,
            monthly_emis=monthly_emis,
            annual_income_increment_pct=annual_hike,
            min_savings_target_pct=min_savings,
            horizon_months=24
        )

        st.markdown(
            f"""
            <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; margin: 1rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0; color: {PRIMARY_TEAL};">Household Shortfall Outlook</h4>
                    <span style="font-size: 1.15rem; font-weight: bold;">{shortfall_res['badge']}</span>
                </div>
                <p style="margin: 8px 0 0 0; color: #475569; font-size: 0.95rem; line-height: 1.4;">
                    {shortfall_res['explanation']}
                </p>
                {f'<div style="margin-top: 8px; color: #DC2626; font-weight: bold;">Month of Shortfall: Month {shortfall_res["shortfall_month"]} (Projected Monthly Deficit: ₹{shortfall_res["max_shortfall_amount"]:,.0f})</div>' if shortfall_res['shortfall_month'] else '<div style="margin-top: 8px; color: #16A34A; font-weight: bold;">No cash-flow shortfall detected within 24 months.</div>'}
            </div>
            """,
            unsafe_allow_html=True
        )

        # Surplus cards across key milestones
        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        with col_m1:
            st.metric("Surplus Today", format_inr(shortfall_res["current_surplus"]))
        with col_m2:
            st.metric("In 6 Months", format_inr(shortfall_res["surplus_6m"]))
        with col_m3:
            st.metric("In 12 Months", format_inr(shortfall_res["surplus_12m"]))
        with col_m4:
            st.metric("In 18 Months", format_inr(shortfall_res["surplus_18m"]))
        with col_m5:
            st.metric("In 24 Months", format_inr(shortfall_res["surplus_24m"]))

        # Chart: Income vs Compounded Outflows
        df_time = shortfall_res["timeline_df"]
        fig_short = go.Figure()

        fig_short.add_trace(go.Scatter(
            x=df_time["Month"], y=df_time["Projected_Income"],
            mode="lines", name="Projected Income (with hikes)",
            line=dict(color="#16A34A", width=3)
        ))
        fig_short.add_trace(go.Scatter(
            x=df_time["Month"], y=df_time["Total_Outflows"],
            mode="lines", name="Essential Outflows (Compounded Inflation)",
            line=dict(color="#DC2626", width=2.5, dash="dash")
        ))
        fig_short.add_trace(go.Bar(
            x=df_time["Month"], y=df_time["Net_Surplus"],
            name="Net Monthly Cash Flow",
            marker_color=df_time["Net_Surplus"].apply(lambda x: "#86EFAC" if x >= 0 else "#FCA5A5"),
            opacity=0.6
        ))

        fig_short.update_layout(
            title="24-Month Income vs. Inflation-Compounded Essential Outflows",
            xaxis_title="Months Ahead",
            yaxis_title="Monthly Amount (₹)",
            template="plotly_white",
            height=380,
            margin=dict(l=20, r=20, t=50, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_short, use_container_width=True)

    # ---------------- TAB 2: MONTE CARLO (1,000 RUNS) ----------------
    with tab_montecarlo:
        st.markdown("#### 1,000-Run Monte Carlo Inflation Volatility Simulation")
        st.markdown(
            """
            Instead of assuming one fixed inflation number, this simulation samples 1,000 potential 
            future economic trajectories from the **model's 80% prediction intervals** (accounting for food spikes, fuel shocks, and policy rate moves).
            """
        )

        mc_res = run_monte_carlo_shortfall_simulation(
            current_income=total_income,
            obligations=obligation_dicts,
            monthly_emis=monthly_emis,
            annual_income_increment_pct=annual_hike,
            category_interval_map=category_intervals
        )

        col_mc1, col_mc2 = st.columns(2)
        with col_mc1:
            st.metric("Shortfall Probability (Within 24 Months)", f"{mc_res['shortfall_probability_pct']}%")
        with col_mc2:
            st.metric("Shortfall Scenarios Detected", f"{mc_res['shortfall_runs_count']} of 1,000 Runs")

        st.info(mc_res["probability_text"])

        # Plotly Percentiles Trajectory Chart (P10, P50, P90)
        df_pct = mc_res["percentiles_df"]
        fig_mc = go.Figure()

        # Shaded ribbon between P10 (Stress) and P90 (Optimistic)
        fig_mc.add_trace(go.Scatter(
            x=df_pct["Month"], y=df_pct["P90_Optimistic"],
            mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"
        ))
        fig_mc.add_trace(go.Scatter(
            x=df_pct["Month"], y=df_pct["P10_Stress"],
            mode="lines", line=dict(width=0), fill="tonexty",
            fillcolor="rgba(245, 158, 11, 0.2)", name="80% Monte Carlo Confidence Fan"
        ))
        # P50 Median Line
        fig_mc.add_trace(go.Scatter(
            x=df_pct["Month"], y=df_pct["P50_Median"],
            mode="lines+markers", line=dict(color=PRIMARY_TEAL, width=2.5),
            name="P50 Median Trajectory"
        ))
        # Zero line
        fig_mc.add_trace(go.Scatter(
            x=df_pct["Month"], y=[0] * len(df_pct),
            mode="lines", line=dict(color="#DC2626", dash="dot", width=1.5),
            name="Shortfall Threshold (₹0)"
        ))

        fig_mc.update_layout(
            title="Monte Carlo Cash Flow Fans: Stress (P10) vs. Median (P50) vs. Optimistic (P90)",
            xaxis_title="Month",
            yaxis_title="Net Monthly Surplus (₹)",
            template="plotly_white",
            height=380,
            margin=dict(l=20, r=20, t=50, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_mc, use_container_width=True)

    # ---------------- TAB 3: WHAT-IF SCENARIOS ----------------
    with tab_whatif:
        st.markdown("#### Test Stress Shocks on Your Household")
        st.caption("Evaluate how life events or external macro shocks impact your financial runway.")

        scenario_choice = st.selectbox(
            "Select Scenario to Test:",
            [
                "Scenario A: Primary Earner Job Loss for 3 Months",
                "Scenario B: Unexpected Medical Emergency (₹1,50,000 Shock)",
                "Scenario C: Global Crude Oil Spike (+15% Fuel & Commute Surge)",
                "Scenario D: Monsoon Failure (Food & Groceries Inflation +5%)"
            ]
        )

        if "Job Loss" in scenario_choice:
            st.warning("**Simulating 3-Month Income Loss:** Evaluating how long your liquid emergency fund lasts.")
            monthly_essential_cost = sum(o["amount"] for o in obligation_dicts) + monthly_emis
            runway_left = round(liquid_reserves / monthly_essential_cost, 1) if monthly_essential_cost > 0 else 0
            st.metric("Liquid Emergency Reserves Available", format_inr(liquid_reserves))
            st.metric("Emergency Runway Without Income", f"{runway_left} Months")

            if runway_left >= 3.0:
                st.success(f"Your emergency fund provides {runway_left} months of buffer, successfully absorbing a 3-month job transition.")
            else:
                st.error(f"Vulnerable: Your runway is only {runway_left} months. A 3-month gap would deplete reserves in Month {int(runway_left)}.")

        elif "Medical" in scenario_choice:
            st.warning("**Simulating ₹1,50,000 Out-of-Pocket Hospitalization Shock:**")
            remaining_liquid = liquid_reserves - 150000.0
            st.metric("Liquid Reserves After Medical Shock", format_inr(remaining_liquid))
            if remaining_liquid > 0:
                st.info(f"Your liquid assets absorb the ₹1.5L shock, leaving ₹{remaining_liquid:,.0f} in reserves.")
            else:
                st.error("Liquid reserves completely exhausted! You would require short-term borrowing or personal loans.")

        elif "Crude" in scenario_choice:
            st.warning("**Simulating Global Crude Oil Surge:** Petrol/diesel and LPG fuel increase by +15%.")
            shocked_obs = []
            for ob in obligation_dicts:
                if ob["category"] in ["Commute", "Utilities"]:
                    shocked_obs.append({"category": ob["category"], "amount": ob["amount"] * 1.15})
                else:
                    shocked_obs.append(ob)
            res_shock = compute_shortfall_timeline(total_income, shocked_obs, monthly_emis=monthly_emis, annual_income_increment_pct=annual_hike)
            st.metric("New Surplus Today (Under Fuel Spike)", format_inr(res_shock["current_surplus"]))
            st.info(f"Status under shock: **{res_shock['badge']}** • Month of shortfall: {res_shock['shortfall_month'] or 'None'}")

        elif "Monsoon" in scenario_choice:
            st.warning("**Simulating Deficit Monsoon:** Vegetable and staple grocery costs surge by +20%.")
            shocked_obs = []
            for ob in obligation_dicts:
                if ob["category"] == "Groceries":
                    shocked_obs.append({"category": ob["category"], "amount": ob["amount"] * 1.20})
                else:
                    shocked_obs.append(ob)
            res_shock = compute_shortfall_timeline(total_income, shocked_obs, monthly_emis=monthly_emis, annual_income_increment_pct=annual_hike)
            st.metric("New Surplus Today (Under Food Surge)", format_inr(res_shock["current_surplus"]))
            st.info(f"Status under food spike: **{res_shock['badge']}** • Month of shortfall: {res_shock['shortfall_month'] or 'None'}")

    # ---------------- TAB 4: FAMILY PLANNING MILESTONES ----------------
    with tab_milestones:
        st.markdown("#### Children's Education Milestones")
        children = [m for m in members if m.relation == "Child"]
        if children:
            for ch in children:
                st.markdown(f"##### Milestone Projections for {ch.name} (Age {ch.age})")
                m_list = compute_education_milestones(
                    child_name=ch.name,
                    current_age=ch.age,
                    current_annual_cost=60000.0,
                    education_inflation_rate=7.5
                )
                df_milestones = pd.DataFrame([{
                    "Academic Milestone": m["milestone"],
                    "Target Age": m["target_age"],
                    "Years Away": f"{m['years_away']} yrs",
                    "Inflated Cost (at 7.5% Inflation)": format_inr(m["inflated_cost"]),
                    "Monthly Investment Needed (at 9% CAGR)": format_inr(m["monthly_investment_needed"])
                } for m in m_list])
                st.dataframe(df_milestones, use_container_width=True)
        else:
            st.info("No children registered in your household profile. You can add family members under 'My Household Profile'.")

        st.markdown("---")
        st.markdown("#### Elderly Parents' Healthcare Provision")
        parents = [m for m in members if m.relation == "Parent"]
        if parents:
            for p in parents:
                med_res = evaluate_parent_medical_provision(
                    parent_name=p.name,
                    age=p.age,
                    current_monthly_meds=5000.0,
                    has_chronic_condition=p.has_chronic_condition,
                    has_health_insurance=False
                )
                st.markdown(
                    f"""
                    <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                        <strong>{med_res['parent_name']} (Age {med_res['age']})</strong><br>
                        • Current Monthly Meds: {format_inr(med_res['current_monthly'])} | Risk-Adjusted: {format_inr(med_res['risk_adjusted_monthly'])}<br>
                        • 5-Year Projected Outgo (at 7% Medical Inflation): {format_inr(med_res['five_year_projected_monthly'])}/mo<br>
                        • Recommended Dedicated Emergency Hospitalization Buffer: <strong>{format_inr(med_res['recommended_buffer'])}</strong><br>
                        <span style="color: #DC2626;">{med_res['advice']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No dependent parents registered in your household profile.")

    render_footer()


if __name__ == "__main__":
    show_future_planner_page()
