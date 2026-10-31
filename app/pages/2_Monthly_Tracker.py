"""
Monthly Expense Tracker & Anomaly Monitor for Parivar Arth.
Includes:
1. Daily transaction logger with quick category tags
2. Needs (50%) / Wants (30%) / Savings (20%) Indian breakdown
3. Personal z-score overspending anomaly detector
4. CSV statement import with auto-categorization
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
from app.styles import apply_theme, render_header, render_footer, PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
from app.components.formatters import format_inr, format_pct

TRACKER_CATEGORIES = [
    "Groceries", "Dining Out", "Commute", "Utilities", "Shopping",
    "Health", "Child Education", "Entertainment", "Other"
]


def show_monthly_tracker_page():
    st.set_page_config(page_title="Monthly Expense Tracker - Parivar Arth", page_icon=None, layout="centered")
    apply_theme()
    touch_session()

    user_id = get_current_user_id()
    if not user_id:
        st.warning("Please log in to record and track your family expenses.")
        st.stop()

    render_header(
        title="Monthly Expense Tracker",
        subtitle="Log day-to-day spending and detect family overspending anomalies"
    )

    with get_db_session() as db:
        profile_data = get_household_profile(db, user_id)
        expenses = get_user_expenses(db, user_id)
        anomalies = detect_overspending_anomalies(db, user_id)

    total_monthly_income = sum(i.amount for i in profile_data["incomes"])
    total_fixed_obligations = sum(o.amount for o in profile_data["obligations"])

    # 1. Overspending Anomaly Alert Banner
    if anomalies:
        for anom in anomalies:
            st.markdown(
                f"""
                <div style="background-color: #FEF2F2; border-left: 4px solid #DC2626; padding: 12px; border-radius: 8px; margin-bottom: 0.75rem;">
                    <strong style="color: #991B1B;">Overspending Alert ({anom['category']}):</strong><br>
                    <span style="font-size: 0.9rem; color: #7F1D1D;">{anom['message']} (z-score: {anom['z_score']})</span>
                </div>
                """,
                unsafe_allow_html=True
            )

    tab_overview, tab_add, tab_import = st.tabs(["Spending Overview", "Log New Expense", "Import CSV Statement"])

    # ---------------- TAB 1: OVERVIEW ----------------
    with tab_overview:
        # Needs / Wants / Savings Split
        split_data = compute_needs_wants_savings_split(total_monthly_income, total_fixed_obligations, expenses)

        st.markdown("#### Needs / Wants / Savings Distribution")
        st.caption("Standard 50/30/20 benchmark vs your family's actual allocation.")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Needs (Essential)", format_inr(split_data["needs_amount"]), f"{split_data['needs_pct']}% of income")
        with col2:
            st.metric("Wants (Discretionary)", format_inr(split_data["wants_amount"]), f"{split_data['wants_pct']}% of income")
        with col3:
            st.metric("Estimated Savings", format_inr(split_data["savings_amount"]), f"{split_data['savings_pct']}% of income")

        if split_data["is_high_needs"]:
            st.info("**Indian Household Context:** Your essential Needs exceed 60% of income. This is very common in Indian urban families managing rent, school fees, and medical care.")

        st.markdown("---")

        if expenses:
            exp_df = pd.DataFrame([{
                "id": e.id,
                "Date": e.date,
                "Category": e.category,
                "Amount": e.amount,
                "Note": e.note
            } for e in expenses])

            # Visual Category Breakdown
            cat_totals = exp_df.groupby("Category")["Amount"].sum().reset_index()

            fig_donut = px.pie(
                cat_totals,
                values="Amount",
                names="Category",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Prism,
                title="Variable Expense Breakdown by Category"
            )
            fig_donut.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=320)
            st.plotly_chart(fig_donut, use_container_width=True)

            # Recent Transactions
            st.markdown("#### Recorded Expenses")
            st.dataframe(
                exp_df[["Date", "Category", "Amount", "Note"]].sort_values("Date", ascending=False),
                use_container_width=True
            )

            # Quick delete option
            with st.expander("Delete a transaction entry"):
                del_id = st.selectbox("Select Transaction ID to Delete", options=exp_df["id"].tolist())
                if st.button("Delete Selected Transaction", type="secondary"):
                    with get_db_session() as db:
                        ok, msg = delete_expense(db, user_id, del_id)
                        if ok:
                            st.success(msg)
                            st.rerun()
        else:
            st.info("No variable expenses logged yet. Use the 'Log New Expense' tab to record your daily spending.")

    # ---------------- TAB 2: LOG EXPENSE ----------------
    with tab_add:
        st.markdown("#### Record a Day-to-Day Expense")
        with st.form("add_expense_form", clear_on_submit=True):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                e_date = st.date_input("Date of Expense", value=date.today())
                e_cat = st.selectbox("Category", options=TRACKER_CATEGORIES)
            with col_e2:
                e_amt = st.number_input("Amount (₹)", min_value=1.0, value=350.0, step=50.0)
                e_note = st.text_input("Note / Merchant", placeholder="e.g. Swiggy lunch, vegetable market")

            submit_exp = st.form_submit_button("Record Expense", type="primary", use_container_width=True)

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
        st.markdown("#### Import Bank / UPI CSV Statement")
        st.caption("Upload a simple CSV with columns: `date`, `amount`, `description`.")

        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file:
            try:
                raw_csv = pd.read_csv(uploaded_file)
                st.write("Uploaded Preview:", raw_csv.head(3))

                # Identify columns
                cols = [c.lower() for c in raw_csv.columns]
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
