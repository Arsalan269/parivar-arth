"""
Future Planner & Financial Intelligence Engine for Parivar Arth.
Aether FinTech Design System - Predictive Shortfall, 1,000-Run Monte Carlo, and Goal Milestones.
"""

import os
import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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
from app.styles import (
    apply_theme, render_header, render_footer, render_metric_card,
    render_sidebar_brand, render_sidebar_user, apply_aether_chart_theme,
    PRIMARY_ACCENT, SECONDARY_ACCENT, SOFT_PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER_COLOR,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
)
from app.components.formatters import format_inr, format_pct


def show_future_planner_page():
    st.set_page_config(
        page_title="Future Planner - Parivar Arth",
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
        st.warning("Please sign in to access the Future Planner engine.")
        st.stop()

    with st.sidebar:
        user_name = user_data.get("name", "Household Account") if user_data else "User"
        render_sidebar_user(username=user_name, role="Primary Account")
        if st.button("Sign Out", key="fp_logout_btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    render_header(
        title="Future Planner & Intelligence Engine",
        subtitle="Multi-category compounded inflation, 1,000-run Monte Carlo projections, and family milestones",
        tag="Predictive AI"
    )

    with get_db_session() as db:
        profile_data = get_household_profile(db, user_id)
        forecast_rows = db.query(Forecast).all()

    incomes = profile_data.get("incomes", [])
    obligations = profile_data.get("obligations", [])
    loans = profile_data.get("loans", [])
    members = profile_data.get("members", [])
    assets = profile_data.get("assets", [])

    total_income = sum(float(getattr(i, "amount", 0.0)) for i in incomes)
    monthly_emis = sum(float(getattr(l, "emi", 0.0)) for l in loans)
    liquid_reserves = sum(float(getattr(a, "amount", 0.0)) for a in assets if getattr(a, "is_liquid", False))
    obligation_dicts = [{"category": getattr(o, "category", "Other"), "amount": float(getattr(o, "amount", 0.0))} for o in obligations]

    # Map forecast intervals per category
    category_intervals = {}
    for f in forecast_rows:
        if f.category not in category_intervals:
            category_intervals[f.category] = (f.lower_ci, f.predicted_inflation, f.upper_ci)

    # Initial snapshot computation with baseline assumptions
    base_shortfall = compute_shortfall_timeline(
        current_monthly_income=total_income,
        obligations=obligation_dicts,
        monthly_emis=monthly_emis,
        annual_income_increment_pct=6.0,
        min_savings_target_pct=10.0,
        horizon_months=24
    )

    # Top Overview Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        current_surplus = base_shortfall["current_surplus"]
        render_metric_card(
            label="Current Monthly Surplus",
            value=format_inr(current_surplus),
            subtext="Inflows minus total monthly burn",
            badge_text="Surplus" if current_surplus >= 0 else "Deficit",
            badge_type="safe" if current_surplus >= 0 else "risk"
        )
    with m2:
        m24_burn = base_shortfall["timeline_df"]["Total_Outflows"].iloc[-1] if not base_shortfall["timeline_df"].empty else 0
        render_metric_card(
            label="Projected Burn (Month 24)",
            value=format_inr(m24_burn),
            subtext="Compounded at category inflation",
            badge_text="Inflated",
            badge_type="watch"
        )
    with m3:
        sf_month = base_shortfall.get("shortfall_month")
        sf_badge = f"Month {sf_month}" if sf_month else "Zero Deficit"
        render_metric_card(
            label="Cash Flow Horizon",
            value=sf_badge,
            subtext="First month of projected shortfall",
            badge_text="Safe" if not sf_month else "Action Req.",
            badge_type="safe" if not sf_month else "risk"
        )
    with m4:
        surplus_24m = base_shortfall["surplus_24m"]
        render_metric_card(
            label="Net Surplus at M24",
            value=format_inr(surplus_24m),
            subtext="With 6% salary hike assumption",
            badge_text="Healthy" if surplus_24m > 0 else "Shortfall",
            badge_type="safe" if surplus_24m > 0 else "risk"
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Main Tabs
    tab_shortfall, tab_montecarlo, tab_whatif, tab_milestones = st.tabs([
        "24-Month Shortfall Timeline",
        "Monte Carlo Volatility (1,000 Runs)",
        "Stress Testing & What-If Shocks",
        "Family Milestones & Life Goals"
    ])

    # ---------------- TAB 1: SHORTFALL TIMELINE ----------------
    with tab_shortfall:
        st.markdown(
            f"""
            <div style="margin-top: 0.5rem; margin-bottom: 1.25rem;">
                <h3 style="font-size: 1.25rem; font-weight: 700; color: {TEXT_PRIMARY}; margin: 0;">24-Month Cash Flow Trajectory</h3>
                <p style="font-size: 0.88rem; color: {TEXT_SECONDARY}; margin: 2px 0 0 0;">Interactive forward cash flow model adjusted for realistic Indian inflation</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        ctrl_col1, ctrl_col2 = st.columns(2)
        with ctrl_col1:
            annual_hike = st.slider(
                "Expected Annual Income Hike (% / year)",
                min_value=0.0, max_value=15.0, value=6.0, step=0.5,
                help="Projected annual increment in primary & secondary household income."
            )
        with ctrl_col2:
            min_savings = st.slider(
                "Target Monthly Savings Reserve (% of monthly income)",
                min_value=0.0, max_value=30.0, value=10.0, step=2.0,
                help="Buffer percentage reserved before calculating net discretionary cash."
            )

        shortfall_res = compute_shortfall_timeline(
            current_monthly_income=total_income,
            obligations=obligation_dicts,
            monthly_emis=monthly_emis,
            annual_income_increment_pct=annual_hike,
            min_savings_target_pct=min_savings,
            horizon_months=24
        )

        # Overview banner card
        is_safe = shortfall_res["shortfall_month"] is None
        banner_border = "#A7F3D0" if is_safe else "#FECACA"
        banner_bg = "#E6F8F3" if is_safe else "#FEF2F2"
        banner_color = COLOR_SUCCESS if is_safe else COLOR_DANGER

        st.markdown(
            f"""
            <div class="aether-card" style="border-left: 4px solid {banner_color}; margin-top: 1rem; margin-bottom: 1.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div style="font-size: 1.05rem; font-weight: 700; color: {TEXT_PRIMARY};">
                        Shortfall Engine Diagnostic: {shortfall_res['badge']}
                    </div>
                    <span class="status-badge {'status-safe' if is_safe else 'status-at-risk'}">{shortfall_res['badge']}</span>
                </div>
                <div style="font-size: 0.9rem; color: {TEXT_SECONDARY}; line-height: 1.5;">
                    {shortfall_res['explanation']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Milestone surplus progression metrics
        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        with col_m1:
            st.metric("Surplus Today", format_inr(shortfall_res["current_surplus"]))
        with col_m2:
            st.metric("At Month 6", format_inr(shortfall_res["surplus_6m"]))
        with col_m3:
            st.metric("At Month 12", format_inr(shortfall_res["surplus_12m"]))
        with col_m4:
            st.metric("At Month 18", format_inr(shortfall_res["surplus_18m"]))
        with col_m5:
            st.metric("At Month 24", format_inr(shortfall_res["surplus_24m"]))

        # Chart: Income vs Compounded Outflows
        df_time = shortfall_res["timeline_df"]
        fig_short = go.Figure()

        fig_short.add_trace(go.Scatter(
            x=df_time["Month"], y=df_time["Projected_Income"],
            mode="lines+markers", name="Projected Income (with hikes)",
            line=dict(color=COLOR_SUCCESS, width=3),
            marker=dict(size=4)
        ))
        fig_short.add_trace(go.Scatter(
            x=df_time["Month"], y=df_time["Total_Outflows"],
            mode="lines", name="Essential Outflows (Compounded Inflation)",
            line=dict(color=COLOR_DANGER, width=2.5, dash="dash")
        ))
        fig_short.add_trace(go.Bar(
            x=df_time["Month"], y=df_time["Net_Surplus"],
            name="Net Monthly Cash Flow",
            marker=dict(
                color=df_time["Net_Surplus"].apply(lambda x: COLOR_SUCCESS if x >= 0 else COLOR_DANGER),
                opacity=0.35
            )
        ))

        apply_aether_chart_theme(
            fig_short,
            title="24-Month Income vs. Compounded Outflows vs. Net Surplus",
            height=390
        )
        fig_short.update_xaxes(title_text="Projection Horizon (Months)")
        fig_short.update_yaxes(title_text="Amount in INR (₹)")
        st.plotly_chart(fig_short, use_container_width=True)

        with st.expander("View Detailed Month-by-Month Cash Flow Table", expanded=False):
            df_display = df_time.copy()
            df_display["Projected_Income"] = df_display["Projected_Income"].apply(format_inr)
            if "Essential_Expenses" in df_display.columns:
                df_display["Essential_Expenses"] = df_display["Essential_Expenses"].apply(format_inr)
            if "EMIs" in df_display.columns:
                df_display["EMIs"] = df_display["EMIs"].apply(format_inr)
            df_display["Total_Outflows"] = df_display["Total_Outflows"].apply(format_inr)
            df_display["Net_Surplus"] = df_display["Net_Surplus"].apply(format_inr)
            if "Status" in df_display.columns:
                df_display["Status"] = df_display["Status"].apply(lambda s: str(s).upper())
            elif "Is_Shortfall" in df_display.columns:
                df_display["Status"] = df_display["Is_Shortfall"].apply(lambda x: "SHORTFALL" if x else "SURPLUS")
            show_cols = [c for c in ["Month", "Projected_Income", "Essential_Expenses", "EMIs", "Total_Outflows", "Net_Surplus", "Status"] if c in df_display.columns]
            st.dataframe(df_display[show_cols], use_container_width=True)

    # ---------------- TAB 2: MONTE CARLO (1,000 RUNS) ----------------
    with tab_montecarlo:
        st.markdown(
            f"""
            <div style="margin-top: 0.5rem; margin-bottom: 1.25rem;">
                <h3 style="font-size: 1.25rem; font-weight: 700; color: {TEXT_PRIMARY}; margin: 0;">1,000-Run Monte Carlo Simulation</h3>
                <p style="font-size: 0.88rem; color: {TEXT_SECONDARY}; margin: 2px 0 0 0;">
                    Instead of assuming fixed inflation, the engine executes 1,000 stochastic economic simulations using ML prediction intervals.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        mc_res = run_monte_carlo_shortfall_simulation(
            current_income=total_income,
            obligations=obligation_dicts,
            monthly_emis=monthly_emis,
            annual_income_increment_pct=annual_hike,
            category_interval_map=category_intervals
        )

        prob_pct = mc_res['shortfall_probability_pct']
        prob_type = "safe" if prob_pct <= 15 else ("watch" if prob_pct <= 40 else "risk")

        col_mc1, col_mc2, col_mc3 = st.columns(3)
        with col_mc1:
            render_metric_card(
                label="Shortfall Probability",
                value=f"{prob_pct}%",
                subtext="Scenarios with cash deficit",
                badge_text=prob_type.upper(),
                badge_type=prob_type
            )
        with col_mc2:
            render_metric_card(
                label="Deficit Trajectories",
                value=f"{mc_res['shortfall_runs_count']} / 1,000",
                subtext="Simulated paths showing deficit",
                badge_text="Runs",
                badge_type="purple"
            )
        with col_mc3:
            df_pct = mc_res["percentiles_df"]
            p10_min = df_pct["P10_Stress"].min() if not df_pct.empty else 0
            render_metric_card(
                label="P10 Stress Level",
                value=format_inr(p10_min),
                subtext="Worst-case 10th percentile surplus",
                badge_text="Stress",
                badge_type="risk" if p10_min < 0 else "safe"
            )

        st.markdown(
            f"""
            <div class="aether-card" style="margin-top: 1rem; margin-bottom: 1.25rem; padding: 1rem 1.25rem;">
                <div style="font-weight: 600; color: {TEXT_PRIMARY}; font-size: 0.92rem;">Probabilistic Assessment</div>
                <div style="color: {TEXT_SECONDARY}; font-size: 0.88rem; line-height: 1.5; margin-top: 2px;">
                    {mc_res['probability_text']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Plotly Percentiles Trajectory Chart (P10, P50, P90)
        fig_mc = go.Figure()

        # Shaded confidence fan between P10 (Stress) and P90 (Optimistic)
        fig_mc.add_trace(go.Scatter(
            x=df_pct["Month"], y=df_pct["P90_Optimistic"],
            mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"
        ))
        fig_mc.add_trace(go.Scatter(
            x=df_pct["Month"], y=df_pct["P10_Stress"],
            mode="lines", line=dict(width=0), fill="tonexty",
            fillcolor="rgba(108, 99, 255, 0.14)", name="80% Monte Carlo Confidence Range"
        ))
        # P50 Median Line
        fig_mc.add_trace(go.Scatter(
            x=df_pct["Month"], y=df_pct["P50_Median"],
            mode="lines+markers", line=dict(color=PRIMARY_ACCENT, width=3),
            marker=dict(size=4),
            name="P50 Expected Median"
        ))
        # Zero Shortfall Reference line
        fig_mc.add_trace(go.Scatter(
            x=df_pct["Month"], y=[0] * len(df_pct),
            mode="lines", line=dict(color=COLOR_DANGER, dash="dot", width=1.5),
            name="Deficit Boundary (₹0)"
        ))

        apply_aether_chart_theme(
            fig_mc,
            title="Monte Carlo Confidence Fans: Stress (P10) vs. Median (P50) vs. Optimistic (P90)",
            height=390
        )
        fig_mc.update_xaxes(title_text="Month")
        fig_mc.update_yaxes(title_text="Net Monthly Surplus (₹)")
        st.plotly_chart(fig_mc, use_container_width=True)

    # ---------------- TAB 3: WHAT-IF SCENARIOS ----------------
    with tab_whatif:
        st.markdown(
            f"""
            <div style="margin-top: 0.5rem; margin-bottom: 1.25rem;">
                <h3 style="font-size: 1.25rem; font-weight: 700; color: {TEXT_PRIMARY}; margin: 0;">Household Stress Testing & Macro Shocks</h3>
                <p style="font-size: 0.88rem; color: {TEXT_SECONDARY}; margin: 2px 0 0 0;">
                    Stress-test your family's cash flow against real-world economic shocks and life transitions.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        scenario_choice = st.selectbox(
            "Select Stress Scenario to Model:",
            [
                "Scenario A: Primary Earner Job Transition (3 Months Zero Inflow)",
                "Scenario B: Unexpected Medical Emergency (₹1,50,000 Out-of-Pocket)",
                "Scenario C: Global Crude Oil Spike (+15% Commute & Energy Surge)",
                "Scenario D: Deficit Monsoon Shock (Food & Grocery Spike +20%)"
            ]
        )

        if "Job Transition" in scenario_choice:
            monthly_essential_cost = sum(o["amount"] for o in obligation_dicts) + monthly_emis
            runway_left = round(liquid_reserves / monthly_essential_cost, 1) if monthly_essential_cost > 0 else 0

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                render_metric_card(
                    label="Liquid Emergency Reserves",
                    value=format_inr(liquid_reserves),
                    subtext="Accessible bank savings + FDs",
                    badge_text="Reserves",
                    badge_type="purple"
                )
            with col_s2:
                render_metric_card(
                    label="Runway Without Inflows",
                    value=f"{runway_left} Months",
                    subtext="At current baseline essential burn",
                    badge_text="Safe" if runway_left >= 3.0 else "Vulnerable",
                    badge_type="safe" if runway_left >= 3.0 else "risk"
                )

            if runway_left >= 3.0:
                st.markdown(
                    f"""
                    <div class="aether-card" style="border-left: 4px solid {COLOR_SUCCESS}; margin-top: 1rem;">
                        <strong style="color: {COLOR_SUCCESS};">Stress Test Passed:</strong>
                        Your emergency fund provides {runway_left} months of buffer, successfully absorbing a 3-month job gap without requiring liquidation of investments.
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div class="aether-card" style="border-left: 4px solid {COLOR_DANGER}; margin-top: 1rem;">
                        <strong style="color: {COLOR_DANGER};">Vulnerable:</strong>
                        Your reserves cover only {runway_left} months. A 3-month transition would exhaust liquid funds in Month {int(runway_left)}. Consider prioritizing an emergency buffer.
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        elif "Medical" in scenario_choice:
            remaining_liquid = liquid_reserves - 150000.0
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                render_metric_card(
                    label="Reserves After ₹1.5L Shock",
                    value=format_inr(max(0, remaining_liquid)),
                    subtext="Post-deduction liquid buffer",
                    badge_text="Liquid Buffer",
                    badge_type="safe" if remaining_liquid > 0 else "risk"
                )
            with col_s2:
                render_metric_card(
                    label="Liquidity Status",
                    value="Solvent" if remaining_liquid > 0 else "Deficit",
                    subtext="Ability to self-insure without debt",
                    badge_text="Solvent" if remaining_liquid > 0 else "Borrowing Req.",
                    badge_type="safe" if remaining_liquid > 0 else "risk"
                )

            if remaining_liquid > 0:
                st.markdown(
                    f"""
                    <div class="aether-card" style="border-left: 4px solid {COLOR_SUCCESS}; margin-top: 1rem;">
                        <strong style="color: {COLOR_SUCCESS};">Self-Insured Cushion:</strong>
                        Your liquid assets absorb the ₹1,50,000 hospitalization expense, leaving {format_inr(remaining_liquid)} in emergency reserves.
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div class="aether-card" style="border-left: 4px solid {COLOR_DANGER}; margin-top: 1rem;">
                        <strong style="color: {COLOR_DANGER};">Liquidity Exhaustion:</strong>
                        A ₹1.5L out-of-pocket shock would completely drain liquid savings. Immediate action: secure comprehensive family health insurance.
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        elif "Crude" in scenario_choice:
            shocked_obs = []
            for ob in obligation_dicts:
                if ob["category"] in ["Commute", "Utilities"]:
                    shocked_obs.append({"category": ob["category"], "amount": ob["amount"] * 1.15})
                else:
                    shocked_obs.append(ob)
            res_shock = compute_shortfall_timeline(total_income, shocked_obs, monthly_emis=monthly_emis, annual_income_increment_pct=annual_hike)

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                render_metric_card(
                    label="Surplus Under Fuel Spike",
                    value=format_inr(res_shock["current_surplus"]),
                    subtext="With +15% fuel & utility rates",
                    badge_text=res_shock["badge"],
                    badge_type="safe" if res_shock["current_surplus"] >= 0 else "risk"
                )
            with col_s2:
                render_metric_card(
                    label="Shortfall Month Under Spike",
                    value=f"Month {res_shock['shortfall_month']}" if res_shock['shortfall_month'] else "None",
                    subtext="Horizon of positive cash flow",
                    badge_text="Stable" if not res_shock['shortfall_month'] else "Watch",
                    badge_type="safe" if not res_shock['shortfall_month'] else "risk"
                )

        elif "Monsoon" in scenario_choice:
            shocked_obs = []
            for ob in obligation_dicts:
                if ob["category"] == "Groceries":
                    shocked_obs.append({"category": ob["category"], "amount": ob["amount"] * 1.20})
                else:
                    shocked_obs.append(ob)
            res_shock = compute_shortfall_timeline(total_income, shocked_obs, monthly_emis=monthly_emis, annual_income_increment_pct=annual_hike)

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                render_metric_card(
                    label="Surplus Under Food Surge",
                    value=format_inr(res_shock["current_surplus"]),
                    subtext="With +20% grocery & staple prices",
                    badge_text=res_shock["badge"],
                    badge_type="safe" if res_shock["current_surplus"] >= 0 else "risk"
                )
            with col_s2:
                render_metric_card(
                    label="Shortfall Month Under Food Shock",
                    value=f"Month {res_shock['shortfall_month']}" if res_shock['shortfall_month'] else "None",
                    subtext="Horizon of positive cash flow",
                    badge_text="Stable" if not res_shock['shortfall_month'] else "Watch",
                    badge_type="safe" if not res_shock['shortfall_month'] else "risk"
                )

    # ---------------- TAB 4: FAMILY PLANNING MILESTONES ----------------
    with tab_milestones:
        st.markdown(
            f"""
            <div style="margin-top: 0.5rem; margin-bottom: 1.25rem;">
                <h3 style="font-size: 1.25rem; font-weight: 700; color: {TEXT_PRIMARY}; margin: 0;">Family Life Goals & Inflation Milestones</h3>
                <p style="font-size: 0.88rem; color: {TEXT_SECONDARY}; margin: 2px 0 0 0;">
                    Project future costs for major life events compounding at sector-specific inflation rates.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Children's Education Section
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <div style="font-size: 1.1rem; font-weight: 700; color: {TEXT_PRIMARY};">
                    Children's Higher Education Milestones
                </div>
                <span class="status-badge status-purple">7.5% Education Inflation</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        children = [m for m in members if getattr(m, "relation", "") == "Child"]
        if children:
            for ch in children:
                st.markdown(
                    f"""
                    <div style="font-size: 0.95rem; font-weight: 600; color: {PRIMARY_ACCENT}; margin-top: 12px; margin-bottom: 6px;">
                        Plan for {ch.name} (Current Age: {ch.age})
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                m_list = compute_education_milestones(
                    child_name=ch.name,
                    current_age=ch.age,
                    current_annual_cost=60000.0,
                    education_inflation_rate=7.5
                )

                # Goal Cards Grid
                goal_cols = st.columns(min(len(m_list), 4))
                for idx, m in enumerate(m_list[:4]):
                    with goal_cols[idx]:
                        st.markdown(
                            f"""
                            <div class="aether-card" style="padding: 1.1rem;">
                                <div style="font-size: 0.76rem; text-transform: uppercase; font-weight: 700; color: {TEXT_SECONDARY}; margin-bottom: 4px;">
                                    {m['milestone']}
                                </div>
                                <div style="font-size: 1.35rem; font-weight: 800; color: {TEXT_PRIMARY}; margin-bottom: 2px;">
                                    {format_inr(m['inflated_cost'])}
                                </div>
                                <div style="font-size: 0.8rem; color: {TEXT_SECONDARY}; margin-bottom: 8px;">
                                    Target Age: {m['target_age']} ({m['years_away']} yrs away)
                                </div>
                                <div style="border-top: 1px solid {BORDER_COLOR}; padding-top: 6px; font-size: 0.8rem; color: {PRIMARY_ACCENT}; font-weight: 600;">
                                    SIP: {format_inr(m['monthly_investment_needed'])}/mo
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                df_milestones = pd.DataFrame([{
                    "Academic Milestone": m["milestone"],
                    "Target Age": m["target_age"],
                    "Years Away": f"{m['years_away']} yrs",
                    "Inflated Cost (7.5% Inflation)": format_inr(m["inflated_cost"]),
                    "Monthly SIP Needed (9% CAGR)": format_inr(m["monthly_investment_needed"])
                } for m in m_list])
                st.dataframe(df_milestones, use_container_width=True)
        else:
            st.info("No children registered in your household profile. Add family members under 'My Profile' to unlock education milestone projections.")

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        # Elderly Parents Section
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <div style="font-size: 1.1rem; font-weight: 700; color: {TEXT_PRIMARY};">
                    Elderly Parents' Healthcare Provision
                </div>
                <span class="status-badge status-watch">8-10% Medical Inflation</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        parents = [m for m in members if getattr(m, "relation", "") == "Parent"]
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
                    <div class="aether-card" style="margin-bottom: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div style="font-size: 1.05rem; font-weight: 700; color: {TEXT_PRIMARY};">
                                {med_res['parent_name']} (Age {med_res['age']})
                            </div>
                            <span class="status-badge status-watch">Medical Buffer</span>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 12px;">
                            <div>
                                <div style="font-size: 0.75rem; color: {TEXT_SECONDARY}; text-transform: uppercase;">Current Monthly Meds</div>
                                <div style="font-size: 1.1rem; font-weight: 700; color: {TEXT_PRIMARY};">{format_inr(med_res['current_monthly'])}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.75rem; color: {TEXT_SECONDARY}; text-transform: uppercase;">5-Yr Projected Outgo</div>
                                <div style="font-size: 1.1rem; font-weight: 700; color: {TEXT_PRIMARY};">{format_inr(med_res['five_year_projected_monthly'])}/mo</div>
                            </div>
                            <div>
                                <div style="font-size: 0.75rem; color: {TEXT_SECONDARY}; text-transform: uppercase;">Recommended Buffer</div>
                                <div style="font-size: 1.1rem; font-weight: 700; color: {PRIMARY_ACCENT};">{format_inr(med_res['recommended_buffer'])}</div>
                            </div>
                        </div>
                        <div style="font-size: 0.85rem; color: {COLOR_DANGER}; line-height: 1.4; border-top: 1px solid {BORDER_COLOR}; padding-top: 8px;">
                            {med_res['advice']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No dependent parents registered in your household profile. Add parents under 'My Profile' to evaluate healthcare provisions.")

    render_footer()


if __name__ == "__main__":
    show_future_planner_page()
