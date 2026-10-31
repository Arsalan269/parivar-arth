"""
Monthly Expense Tracker & Anomaly Monitor for Parivar Arth.
Aether FinTech Design System - 50/30/20 Breakdown, Z-Score Anomaly Alerts, and CSV Import.
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
from core.models import Expense
from core.security import touch_session, get_current_user_id
from core.profile_service import get_household_profile
from core.expense_service import (
    add_expense, delete_expense, get_user_expenses,
    compute_needs_wants_savings_split, detect_overspending_anomalies,
    auto_categorize_description
)
from app.styles import (
    apply_theme, render_header, render_footer, render_metric_card,
    render_sidebar_brand, render_sidebar_user, apply_aether_chart_theme,
    PRIMARY_ACCENT, SECONDARY_ACCENT, SOFT_PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER_COLOR,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
)
from app.components.formatters import format_inr, format_pct

TRACKER_CATEGORIES = [
    "Groceries", "Dining Out", "Commute", "Utilities", "Shopping",
    "Health", "Child Education", "Entertainment", "Other"
]


def show_monthly_tracker_page():
    st.set_page_config(
        page_title="Expense Tracker - Parivar Arth",
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
        st.warning("Please sign in to record and track your family expenses.")
        st.stop()

    with st.sidebar:
        user_name = user_data.get("name", "Household Account") if user_data else "User"
        render_sidebar_user(username=user_name, role="Primary Account")
        if st.button("Sign Out", key="mt_logout_btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    render_header(
        title="Monthly Expense Tracker & Anomaly Monitor",
        subtitle="Real-time transaction tracking, 50/30/20 budget adherence, and statistical anomaly detection",
        tag="Cash Flow"
    )

    with get_db_session() as db:
        profile_data = get_household_profile(db, user_id)
        expenses = get_user_expenses(db, user_id)
        anomalies = detect_overspending_anomalies(db, user_id)

    total_monthly_income = sum(float(getattr(i, "amount", 0.0)) for i in profile_data.get("incomes", []))
    total_fixed_obligations = sum(float(getattr(o, "amount", 0.0)) for o in profile_data.get("obligations", []))

    # Overspending Anomaly Alert Banners
    if anomalies:
        for anom in anomalies:
            st.markdown(
                f"""
                <div class="aether-card" style="border-left: 4px solid {COLOR_DANGER}; margin-bottom: 0.75rem; padding: 12px 16px;">
                    <div style="font-weight: 700; color: {COLOR_DANGER}; font-size: 0.92rem; margin-bottom: 2px;">
                        Overspending Anomaly Detected: {anom['category']}
                    </div>
                    <div style="font-size: 0.88rem; color: {TEXT_PRIMARY};">
                        {anom['message']} <span style="color: {TEXT_SECONDARY};">(z-score: {anom['z_score']})</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    tab_overview, tab_add, tab_import = st.tabs([
        "Spending Overview & Breakdown",
        "Log Daily Expense",
        "Import Bank / UPI Statement"
    ])

    # ---------------- TAB 1: OVERVIEW ----------------
    with tab_overview:
        split_data = compute_needs_wants_savings_split(total_monthly_income, total_fixed_obligations, expenses)

        # 3 Aether Metric Cards
        col1, col2, col3 = st.columns(3)
        with col1:
            render_metric_card(
                label="Needs (Essential)",
                value=format_inr(split_data["needs_amount"]),
                subtext=f"{split_data['needs_pct']}% of total income (Target ~50%)",
                badge_text="Essential",
                badge_type="watch" if split_data["is_high_needs"] else "safe"
            )
        with col2:
            render_metric_card(
                label="Wants (Discretionary)",
                value=format_inr(split_data["wants_amount"]),
                subtext=f"{split_data['wants_pct']}% of total income (Target ~30%)",
                badge_text="Lifestyle",
                badge_type="purple"
            )
        with col3:
            render_metric_card(
                label="Estimated Savings",
                value=format_inr(split_data["savings_amount"]),
                subtext=f"{split_data['savings_pct']}% of total income (Target ~20%)",
                badge_text="Reserves",
                badge_type="safe" if split_data["savings_amount"] >= 0 else "risk"
            )

        if split_data["is_high_needs"]:
            st.markdown(
                f"""
                <div class="aether-card" style="margin-top: 1rem; border-left: 4px solid {COLOR_WARNING}; padding: 10px 14px;">
                    <strong style="color: {COLOR_WARNING};">Indian Household Reality:</strong>
                    Essential Needs exceed 60% of income. This is very common in urban families balancing metro rent, tuition fees, and medical care. Check "Reduce Expenses" for structural savings.
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        if expenses:
            exp_df = pd.DataFrame([{
                "id": e.id,
                "Date": e.date,
                "Category": e.category,
                "Amount": e.amount,
                "Note": e.note
            } for e in expenses])

            chart_col, data_col = st.columns([1.2, 1.8])
            with chart_col:
                cat_totals = exp_df.groupby("Category")["Amount"].sum().reset_index()
                fig_donut = px.pie(
                    cat_totals,
                    values="Amount",
                    names="Category",
                    hole=0.55,
                    color_discrete_sequence=[PRIMARY_ACCENT, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, SECONDARY_ACCENT, "#38BDF8", "#A78BFA"],
                    title="Spending by Category"
                )
                apply_aether_chart_theme(fig_donut, title="Variable Spending Distribution", height=340)
                st.plotly_chart(fig_donut, use_container_width=True)

            with data_col:
                st.markdown(
                    f"""
                    <div style="font-size: 1.05rem; font-weight: 700; color: {TEXT_PRIMARY}; margin-bottom: 8px;">
                        Recent Transactions
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                display_table = exp_df[["Date", "Category", "Amount", "Note"]].sort_values("Date", ascending=False).copy()
                display_table["Amount"] = display_table["Amount"].apply(format_inr)
                st.dataframe(display_table, use_container_width=True, height=280)

            # Quick delete option
            with st.expander("Delete a transaction entry", expanded=False):
                del_id = st.selectbox("Select Transaction ID to Delete", options=exp_df["id"].tolist())
                if st.button("Delete Selected Transaction", type="secondary"):
                    with get_db_session() as db:
                        ok, msg = delete_expense(db, user_id, del_id)
                        if ok:
                            st.success(msg)
                            st.rerun()
        else:
            st.info("No variable expenses logged yet. Use the 'Log Daily Expense' tab to record your daily spending.")

    # ---------------- TAB 2: LOG EXPENSE ----------------
    with tab_add:
        st.markdown(
            f"""
            <div style="margin-top: 0.5rem; margin-bottom: 1rem;">
                <h4 style="color: {TEXT_PRIMARY}; font-weight: 700; margin: 0;">Record Daily Expense</h4>
                <p style="color: {TEXT_SECONDARY}; font-size: 0.88rem; margin: 2px 0 0 0;">Log a single out-of-pocket transaction with automatic category tagging</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        with st.form("add_expense_form", clear_on_submit=True):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                e_date = st.date_input("Date of Expense", value=date.today())
                e_cat = st.selectbox("Category", options=TRACKER_CATEGORIES)
            with col_e2:
                e_amt = st.number_input("Amount (₹)", min_value=1.0, value=350.0, step=50.0)
                e_note = st.text_input("Note / Merchant", placeholder="e.g. Swiggy order, vegetable market")

            submit_exp = st.form_submit_button("Record Transaction", type="primary", use_container_width=True)

            if submit_exp:
                with get_db_session() as db:
                    ok, msg = add_expense(db, user_id, e_date, e_cat, e_amt, e_note)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    # ---------------- TAB 3: CSV IMPORT ----------------
    with tab_import:
        st.markdown(
            f"""
            <div style="margin-top: 0.5rem; margin-bottom: 1rem;">
                <h4 style="color: {TEXT_PRIMARY}; font-weight: 700; margin: 0;">Import Bank / UPI CSV Statement</h4>
                <p style="color: {TEXT_SECONDARY}; font-size: 0.88rem; margin: 2px 0 0 0;">Batch import transactions with auto-categorization for Indian merchants</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        uploaded_file = st.file_uploader("Upload CSV Statement", type=["csv"])
        if uploaded_file:
            try:
                raw_csv = pd.read_csv(uploaded_file)
                st.write("File Preview:", raw_csv.head(3))

                date_col = next((c for c in raw_csv.columns if "date" in c.lower()), None)
                amt_col = next((c for c in raw_csv.columns if "amount" in c.lower() or "debit" in c.lower()), None)
                desc_col = next((c for c in raw_csv.columns if "desc" in c.lower() or "narration" in c.lower() or "note" in c.lower() or "particular" in c.lower()), None)

                if date_col and amt_col:
                    preview_records = []
                    for _, row in raw_csv.iterrows():
                        desc = str(row.get(desc_col, "Expense")) if desc_col else "Expense"
                        cat = auto_categorize_description(desc)
                        try:
                            a_val = abs(float(row[amt_col]))
                            if a_val > 0:
                                preview_records.append({
                                    "Date": pd.to_datetime(row[date_col]).date(),
                                    "Category": cat,
                                    "Amount": a_val,
                                    "Description": desc
                                })
                        except Exception:
                            continue

                    st.markdown(f"**Identified {len(preview_records)} valid expense records for import:**")
                    st.dataframe(pd.DataFrame(preview_records).head(10), use_container_width=True)

                    if st.button("Confirm Import All Transactions", type="primary"):
                        with get_db_session() as db:
                            imported_count = 0
                            for rec in preview_records:
                                add_expense(db, user_id, rec["Date"], rec["Category"], rec["Amount"], rec["Description"])
                                imported_count += 1
                        st.success(f"Successfully imported {imported_count} transactions!")
                        st.rerun()
                else:
                    st.error("Could not automatically locate 'date' and 'amount' columns in the uploaded file.")
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

    render_footer()


if __name__ == "__main__":
    show_monthly_tracker_page()
