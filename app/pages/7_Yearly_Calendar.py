"""
12-Month Cash-Flow Calendar & Sinking Funds Planner for Parivar Arth.
Aether FinTech Design System - Outflow Matrix, Sinking Funds Smoothing, and Heavy Month Alerts.
"""

import os
import sys
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import get_db_session
from core.models import RecurringExpense, Forecast
from core.security import touch_session, get_current_user_id
from core.profile_service import get_household_profile
from planner.sinking_funds import compute_sinking_funds, generate_12_month_cashflow_matrix
from app.styles import (
    apply_theme, render_header, render_footer, render_metric_card,
    render_sidebar_brand, render_sidebar_user, apply_aether_chart_theme,
    PRIMARY_ACCENT, SECONDARY_ACCENT, SOFT_PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER_COLOR,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
)
from app.components.formatters import format_inr


def show_yearly_calendar_page():
    st.set_page_config(
        page_title="Yearly Calendar - Parivar Arth",
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
        st.warning("Please sign in to view your household calendar and sinking funds.")
        st.stop()

    with st.sidebar:
        user_name = user_data.get("name", "Household Account") if user_data else "User"
        render_sidebar_user(username=user_name, role="Primary Account")
        if st.button("Sign Out", key="yc_logout_btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    render_header(
        title="12-Month Cash-Flow Calendar",
        subtitle="Forecast lump-sum expenses, smoothing sinking funds, and peak expenditure spikes",
        tag="Cash Flow"
    )

    with get_db_session() as db:
        profile_data = get_household_profile(db, user_id)
        forecasts = db.query(Forecast).all()

    incomes = profile_data.get("incomes", [])
    obligations = profile_data.get("obligations", [])
    recurring = profile_data.get("recurring", [])
    total_monthly_income = sum(float(getattr(i, "amount", 0.0)) for i in incomes)

    # Build category inflation map from latest forecasts
    cat_inflation = {f.category: f.predicted_inflation for f in forecasts}

    recurring_dicts = []
    if recurring:
        for r in recurring:
            recurring_dicts.append({
                "name": r.name,
                "amount": float(getattr(r, "amount", 0.0)),
                "frequency": r.frequency,
                "due_month": r.due_month,
                "category": r.category
            })
    else:
        recurring_dicts = [
            {"name": "Annual School Admission / Book Fees", "amount": 48000.0, "frequency": "Annual", "due_month": 4, "category": "Education"},
            {"name": "Term Life & Health Insurance Premium", "amount": 24000.0, "frequency": "Annual", "due_month": 11, "category": "Health"},
            {"name": "Diwali & Festival Hometown Travel", "amount": 35000.0, "frequency": "Annual", "due_month": 10, "category": "Transport and Communication"},
            {"name": "Car Servicing & Insurance Renewal", "amount": 18000.0, "frequency": "Annual", "due_month": 8, "category": "Transport and Communication"}
        ]

    obligation_dicts = [{"category": getattr(o, "category", "Other"), "amount": float(getattr(o, "amount", 0.0))} for o in obligations]
    df_matrix, summary = generate_12_month_cashflow_matrix(
        fixed_obligations=obligation_dicts,
        recurring_items=recurring_dicts,
        monthly_incomes=total_monthly_income,
        category_inflation_map=cat_inflation
    )

    # Heavy Month Alert Banner
    if summary["heavy_months_count"] > 0:
        heavy_names = [hm["month"] for hm in summary["heavy_months"]]
        st.markdown(
            f"""
            <div class="aether-card" style="border-left: 4px solid {COLOR_WARNING}; margin-bottom: 1.25rem; padding: 14px 18px;">
                <div style="font-weight: 700; color: {COLOR_WARNING}; font-size: 0.95rem; margin-bottom: 3px;">
                    Heavy Expenditure Spikes Detected: {', '.join(heavy_names)}
                </div>
                <div style="font-size: 0.88rem; color: {TEXT_PRIMARY}; line-height: 1.5;">
                    During these months, school admissions, annual insurance premiums, or festival travel cluster together.
                    Deploying the smoothed sinking fund allocations below neutralizes cash flow deficits.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    tab_cal, tab_sinking, tab_add_rec = st.tabs([
        "12-Month Outflow Matrix",
        "Sinking Fund Reserves",
        "Add Recurring Obligation"
    ])

    # ---------------- TAB 1: CALENDAR MATRIX ----------------
    with tab_cal:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=df_matrix["Month"],
            y=df_matrix["Base_Fixed_Costs"],
            name="Base Fixed Costs (Rent, Food, Utilities)",
            marker=dict(color=PRIMARY_ACCENT, opacity=0.85)
        ))
        fig_bar.add_trace(go.Bar(
            x=df_matrix["Month"],
            y=df_matrix["Lump_Sums_Due"],
            name="Lump Sums Due (Fees, Insurance, Festivals)",
            marker=dict(color=COLOR_WARNING, opacity=0.9)
        ))
        fig_bar.add_trace(go.Scatter(
            x=df_matrix["Month"],
            y=[total_monthly_income] * len(df_matrix),
            mode="lines",
            name="Monthly Take-Home Inflow",
            line=dict(color=COLOR_SUCCESS, dash="dash", width=3)
        ))

        fig_bar.update_layout(barmode="stack")
        apply_aether_chart_theme(
            fig_bar,
            title="12-Month Projected Outflows vs. Monthly Take-Home Income",
            height=390
        )
        fig_bar.update_xaxes(title_text="Month")
        fig_bar.update_yaxes(title_text="Amount in INR (₹)")
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown(
            f"""
            <div style="margin-top: 1rem; margin-bottom: 0.75rem;">
                <h4 style="color: {TEXT_PRIMARY}; font-weight: 700; margin: 0;">Month-by-Month Outflow Matrix</h4>
            </div>
            """,
            unsafe_allow_html=True
        )
        display_df = df_matrix[["Month", "Base_Fixed_Costs", "Lump_Sums_Due", "Total_Outflow", "Net_Surplus", "Lump_Details"]].copy()
        display_df["Base_Fixed_Costs"] = display_df["Base_Fixed_Costs"].apply(format_inr)
        display_df["Lump_Sums_Due"] = display_df["Lump_Sums_Due"].apply(format_inr)
        display_df["Total_Outflow"] = display_df["Total_Outflow"].apply(format_inr)
        display_df["Net_Surplus"] = display_df["Net_Surplus"].apply(format_inr)
        st.dataframe(display_df, use_container_width=True)

    # ---------------- TAB 2: SINKING FUNDS ----------------
    with tab_sinking:
        sinking_results = compute_sinking_funds(recurring_dicts, category_inflation_map=cat_inflation)
        total_monthly_sinking = sum(s["smoothed_monthly_reserve"] for s in sinking_results)

        col_sk1, col_sk2 = st.columns(2)
        with col_sk1:
            render_metric_card(
                label="Monthly Sinking Fund Target",
                value=format_inr(total_monthly_sinking),
                subtext="Total smoothed monthly reserve across all lump-sums",
                badge_text="Target Reserve",
                badge_type="purple"
            )
        with col_sk2:
            annual_lump_sum = sum(s["inflated_due_amount"] for s in sinking_results)
            render_metric_card(
                label="Total Annual Lump-Sums Due",
                value=format_inr(annual_lump_sum),
                subtext="Adjusted for category-specific inflation",
                badge_text="Annual Spikes",
                badge_type="watch"
            )

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        sink_df = pd.DataFrame([{
            "Obligation": s["name"],
            "Category": s["category"],
            "Inflation Rate": f"{s['inflation_rate']:.1f}%",
            "Adjusted Due Amount": format_inr(s["inflated_due_amount"]),
            "Due Month": date(2026, s["due_month"], 1).strftime("%B"),
            "Months Left": s["months_left"],
            "Smoothed Monthly Reserve": format_inr(s["smoothed_monthly_reserve"])
        } for s in sinking_results])
        st.dataframe(sink_df, use_container_width=True)

    # ---------------- TAB 3: ADD RECURRING ITEM ----------------
    with tab_add_rec:
        st.markdown(
            f"""
            <div style="margin-top: 0.5rem; margin-bottom: 1rem;">
                <h4 style="color: {TEXT_PRIMARY}; font-weight: 700; margin: 0;">Register an Annual / Quarterly Obligation</h4>
                <p style="color: {TEXT_SECONDARY}; font-size: 0.88rem; margin: 2px 0 0 0;">Add predictable irregular expenses to automatically smooth them into your monthly budget</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        with st.form("add_recurring_form"):
            r_name = st.text_input("Name of Obligation", placeholder="e.g. Car Insurance, School Admission, Term Policy")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                r_amt = st.number_input("Amount (₹)", min_value=500.0, value=20000.0, step=1000.0)
                r_freq = st.selectbox("Frequency", ["Annual", "Quarterly", "Half-Yearly"])
            with col_r2:
                r_due = st.selectbox("Due Month", options=list(range(1, 13)), format_func=lambda x: date(2026, x, 1).strftime("%B"))
                r_cat = st.selectbox("Category", ["Education", "Health", "Transport and Communication", "Fuel and Light", "Miscellaneous Services"])

            add_sub = st.form_submit_button("Save Recurring Obligation", type="primary")

            if add_sub:
                with get_db_session() as db:
                    new_item = RecurringExpense(
                        user_id=user_id,
                        name=r_name.strip(),
                        amount=r_amt,
                        frequency=r_freq,
                        due_month=r_due,
                        category=r_cat
                    )
                    db.add(new_item)
                    db.commit()
                st.success(f"Added '{r_name}' to your household cash-flow calendar!")
                st.rerun()

    render_footer()


if __name__ == "__main__":
    show_yearly_calendar_page()
