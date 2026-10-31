"""
12-Month Cash-Flow Calendar & Sinking Funds Planner for Parivar Arth.
Includes:
1. Sinking Funds calculation converting heavy annual costs into smoothed monthly reserves
2. 12-month forward cash-flow calendar highlighting heavy expenditure months
3. Category-specific inflation adjustments applied across all items
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
from app.styles import apply_theme, render_header, render_footer, PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
from app.components.formatters import format_inr


def show_yearly_calendar_page():
    st.set_page_config(page_title="Yearly Calendar & Sinking Funds - Parivar Arth", page_icon=None, layout="centered")
    apply_theme()
    touch_session()

    user_id = get_current_user_id()
    if not user_id:
        st.warning("Please sign in to view your household calendar and sinking funds.")
        st.stop()

    render_header(
        title="12-Month Cash-Flow Calendar",
        subtitle="Forecast lump-sum expenses, sinking funds & heavy months"
    )

    with get_db_session() as db:
        profile_data = get_household_profile(db, user_id)
        forecasts = db.query(Forecast).all()

    incomes = profile_data["incomes"]
    obligations = profile_data["obligations"]
    recurring = profile_data["recurring"]
    total_monthly_income = sum(i.amount for i in incomes)

    # Build category inflation map from latest forecasts
    cat_inflation = {f.category: f.predicted_inflation for f in forecasts}

    # If no recurring items exist, provide friendly defaults for typical Indian families
    recurring_dicts = []
    if recurring:
        for r in recurring:
            recurring_dicts.append({
                "name": r.name,
                "amount": r.amount,
                "frequency": r.frequency,
                "due_month": r.due_month,
                "category": r.category
            })
    else:
        # Default sample provisions for demonstration
        recurring_dicts = [
            {"name": "Annual School Admission / Book Fees", "amount": 48000.0, "frequency": "Annual", "due_month": 4, "category": "Education"},
            {"name": "Term Life & Health Insurance Premium", "amount": 24000.0, "frequency": "Annual", "due_month": 11, "category": "Health"},
            {"name": "Diwali & Festival Hometown Travel", "amount": 35000.0, "frequency": "Annual", "due_month": 10, "category": "Transport and Communication"},
            {"name": "Car Servicing & Insurance Renewal", "amount": 18000.0, "frequency": "Annual", "due_month": 8, "category": "Transport and Communication"}
        ]

    obligation_dicts = [{"category": o.category, "amount": o.amount} for o in obligations]
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
            <div style="background-color: #FEF3C7; border-left: 4px solid {ACCENT_SAFFRON}; padding: 12px; border-radius: 8px; margin-bottom: 1rem;">
                <strong style="color: #78350F;">Heavy Expenditure Months Detected: {', '.join(heavy_names)}</strong><br>
                <span style="font-size: 0.9rem; color: #92400E;">
                During these months, school admissions, festival travel, or insurance premiums cluster together. 
                Using the sinking fund allocations below prevents cash flow shortfalls.
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    tab_cal, tab_sinking, tab_add_rec = st.tabs(["12-Month Outflow Matrix", "Sinking Fund Reserves", "Add Recurring Obligation"])

    # ---------------- TAB 1: CALENDAR MATRIX ----------------
    with tab_cal:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=df_matrix["Month"],
            y=df_matrix["Base_Fixed_Costs"],
            name="Base Fixed Costs (Rent, Food, Utilities)",
            marker_color=PRIMARY_TEAL
        ))
        fig_bar.add_trace(go.Bar(
            x=df_matrix["Month"],
            y=df_matrix["Lump_Sums_Due"],
            name="Lump Sums Due (Fees, Insurance, Festivals)",
            marker_color=ACCENT_SAFFRON
        ))
        # Total Income line
        fig_bar.add_trace(go.Scatter(
            x=df_matrix["Month"],
            y=[total_monthly_income] * len(df_matrix),
            mode="lines",
            name="Monthly Take-Home Income",
            line=dict(color="#16A34A", dash="dash", width=2.5)
        ))

        fig_bar.update_layout(
            barmode="stack",
            title="12-Month Projected Outflows vs. Monthly Income",
            xaxis_title="Month",
            yaxis_title="Amount (₹)",
            template="plotly_white",
            height=380,
            margin=dict(l=20, r=20, t=50, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("#### Month-by-Month Projected Breakdown")
        display_df = df_matrix[["Month", "Base_Fixed_Costs", "Lump_Sums_Due", "Total_Outflow", "Net_Surplus", "Lump_Details"]].copy()
        display_df["Base_Fixed_Costs"] = display_df["Base_Fixed_Costs"].apply(format_inr)
        display_df["Lump_Sums_Due"] = display_df["Lump_Sums_Due"].apply(format_inr)
        display_df["Total_Outflow"] = display_df["Total_Outflow"].apply(format_inr)
        display_df["Net_Surplus"] = display_df["Net_Surplus"].apply(format_inr)
        st.dataframe(display_df, use_container_width=True)

    # ---------------- TAB 2: SINKING FUNDS ----------------
    with tab_sinking:
        st.markdown("#### Monthly Sinking Fund Allocations")
        st.markdown(
            """
            Instead of getting blindsided by a ₹48,000 school fee in April or a ₹24,000 insurance bill in November,
            set aside a fixed monthly sinking allocation. Category-specific inflation is already factored in!
            """
        )

        sinking_results = compute_sinking_funds(recurring_dicts, category_inflation_map=cat_inflation)
        total_monthly_sinking = sum(s["smoothed_monthly_reserve"] for s in sinking_results)

        st.metric("Total Monthly Sinking Fund Allocation Needed", format_inr(total_monthly_sinking))

        sink_df = pd.DataFrame([{
            "Obligation": s["name"],
            "Category": s["category"],
            "Forecast Inflation": f"{s['inflation_rate']:.1f}%",
            "Adjusted Due Amount": format_inr(s["inflated_due_amount"]),
            "Due Month": date(2026, s["due_month"], 1).strftime("%B"),
            "Months Left": s["months_left"],
            "Recommended Monthly Reserve": format_inr(s["smoothed_monthly_reserve"])
        } for s in sinking_results])
        st.dataframe(sink_df, use_container_width=True)

    # ---------------- TAB 3: ADD RECURRING ITEM ----------------
    with tab_add_rec:
        st.markdown("#### Register an Annual / Quarterly Obligation")
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
