"""
My Household Profile & Onboarding Wizard for Parivar Arth.
Includes:
1. Non-skippable Onboarding Wizard with conditional family-structure validation.
2. Versioned Profile Editing (closes old row via effective_to, inserts new via effective_from).
3. 'What Changed' Audit History timeline.
"""

import os
import sys
import streamlit as st
import pandas as pd
from datetime import date

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import get_db_session
from core.models import Profile
from core.security import touch_session, get_current_user_id
from core.profile_service import (
    get_household_profile, save_initial_onboarding,
    update_obligation_versioned, update_income_versioned, get_version_history
)
from app.styles import apply_theme, render_header, render_footer, PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
from app.components.formatters import format_inr

INDIAN_STATES = [
    "Maharashtra", "Karnataka", "Delhi (NCR)", "Tamil Nadu", "Uttar Pradesh",
    "Gujarat", "West Bengal", "Telangana", "Kerala", "Rajasthan",
    "Madhya Pradesh", "Bihar", "Punjab", "Haryana", "Andhra Pradesh",
    "Assam", "Odisha", "Jharkhand", "Chhattisgarh", "Uttarakhand",
    "Goa", "Himachal Pradesh", "Jammu & Kashmir", "Other State/UT"
]


def show_onboarding_wizard(user_id: int):
    """Render the step-by-step onboarding wizard for new households."""
    st.markdown(
        f"""
        <div style="background-color: #E6F4F2; border-left: 4px solid {PRIMARY_TEAL}; padding: 14px; border-radius: 8px; margin-bottom: 1.5rem;">
            <h4 style="margin: 0; color: {PRIMARY_TEAL};">Step 1: Household Financial Setup</h4>
            <p style="margin: 0; font-size: 0.9rem; color: #334155;">
                Every rupee in Parivar Arth is tailored to your real family structure. 
                Please enter your core monthly details below.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.form("onboarding_wizard_form", clear_on_submit=False):
        # Section 1: Location & Household Size
        st.subheader("1. Household & Geography")
        col1, col2 = st.columns(2)
        with col1:
            state = st.selectbox("State of Residence", options=INDIAN_STATES, index=0)
        with col2:
            city_type = st.selectbox("City Classification", ["Metro (Tier-1)", "Tier-2 / Tier-3 City", "Semi-Urban / Rural"])
        
        hh_size = st.number_input("Household Size (Total members living together)", min_value=1, max_value=20, value=3)

        st.markdown("---")

        # Section 2: Family Structure
        st.subheader("2. Family Members")
        st.caption("Add dependents to enable personalized education and healthcare inflation planning.")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            spouse_present = st.checkbox("Include Spouse in household", value=True)
            children_count = st.number_input("Number of Dependent Children", min_value=0, max_value=8, value=1)
        with col_f2:
            parents_count = st.number_input("Number of Dependent Parents", min_value=0, max_value=4, value=0)
            parent_chronic = st.checkbox("Any parent with chronic health condition (Diabetes, Cardiac, etc.)", value=False)

        st.markdown("---")

        # Section 3: Monthly Incomes
        st.subheader("3. Earners & Monthly Income")
        col_inc1, col_inc2 = st.columns(2)
        with col_inc1:
            primary_income = st.number_input("Primary Earner Monthly Take-Home (₹)", min_value=1000, value=75000, step=5000, help="Net take-home cash income.")
            primary_var = st.checkbox("Income is Variable (Gig worker / Business / Freelance)", value=False)
        with col_inc2:
            secondary_income = st.number_input("Secondary Earner Monthly Income (₹)", min_value=0, value=0, step=5000)

        st.markdown("---")

        # Section 4: Mandatory Core Expenses
        st.subheader("4. Mandatory Core Expenses")
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            rent_emi = st.number_input("Monthly Rent or Housing EMI (₹)", min_value=0, value=22000, step=1000, help="Enter 0 if family-owned ancestral home without loan.")
            groceries = st.number_input("Monthly Groceries Estimate (₹)", min_value=500, value=14000, step=1000, help="Food, grains, milk, vegetables, cooking oil.")
        with col_exp2:
            utilities = st.number_input("Monthly Utilities (₹)", min_value=0, value=4500, step=500, help="Electricity, LPG cylinders, water bills, piped gas.")
            commute = st.number_input("Monthly Commute & Fuel (₹)", min_value=0, value=4000, step=500, help="Petrol, diesel, metro, bus, auto fares.")

        st.markdown("---")

        # Section 5: Conditional Expenses
        st.subheader("5. Dependent Expenses (Conditional)")
        
        child_fees = 0
        if children_count > 0:
            st.markdown("##### 🎓 Children's Education Fees (Mandatory as children were added)")
            child_fees = st.number_input("Total Monthly School / Tuition Fees (₹)", min_value=100, value=6000, step=500)

        parent_medical = 0
        if parents_count > 0:
            st.markdown("##### 🏥 Parents' Medical Provision (Mandatory as parents were added)")
            parent_medical = st.number_input("Monthly Medicines & Doctor Consultations (₹)", min_value=100, value=5000, step=500)

        st.markdown("---")

        # Section 6: Existing Loans & Savings
        st.subheader("6. Loans & Liquid Assets (Optional but Recommended)")
        col_ln1, col_ln2 = st.columns(2)
        with col_ln1:
            loan_balance = st.number_input("Total Outstanding Loan Balance (₹)", min_value=0, value=0, step=25000)
            loan_emi = st.number_input("Total Monthly Loan EMI (₹)", min_value=0, value=0, step=1000)
        with col_ln2:
            liquid_savings = st.number_input("Current Liquid Savings (Savings Account + FDs) (₹)", min_value=0, value=150000, step=10000)
            maid_cost = st.number_input("Household Help (Maid/Cook/Driver) Monthly (₹)", min_value=0, value=3500, step=500)

        submit_onboarding = st.form_submit_button("Complete Onboarding & Save Profile", type="primary", use_container_width=True)

        if submit_onboarding:
            # Construct structures
            members_list = [{"name": "Self", "relation": "Self", "age": 35}]
            if spouse_present:
                members_list.append({"name": "Spouse", "relation": "Spouse", "age": 33})
            for i in range(children_count):
                members_list.append({"name": f"Child {i+1}", "relation": "Child", "age": 7 + (i * 3)})
            for i in range(parents_count):
                members_list.append({"name": f"Parent {i+1}", "relation": "Parent", "age": 65 + (i * 3), "has_chronic_condition": parent_chronic})

            incomes_list = [{"earner_name": "Self", "source_type": "Primary Salary", "amount": primary_income, "is_variable": primary_var}]
            if secondary_income > 0:
                incomes_list.append({"earner_name": "Spouse" if spouse_present else "Self", "source_type": "Secondary Income", "amount": secondary_income, "is_variable": False})

            obligations_list = [
                {"category": "Rent/EMI", "amount": rent_emi, "frequency": "Monthly"},
                {"category": "Groceries", "amount": groceries, "frequency": "Monthly"},
                {"category": "Utilities", "amount": utilities, "frequency": "Monthly"},
                {"category": "Commute", "amount": commute, "frequency": "Monthly"},
            ]
            if children_count > 0:
                obligations_list.append({"category": "Child Education", "amount": child_fees, "frequency": "Monthly"})
            if parents_count > 0:
                obligations_list.append({"category": "Parent Medical", "amount": parent_medical, "frequency": "Monthly"})

            loans_list = []
            if loan_balance > 0 and loan_emi > 0:
                loans_list.append({"loan_type": "Personal / Home Loan", "balance": loan_balance, "emi": loan_emi, "interest_rate": 8.75, "remaining_months": 36, "rate_type": "Floating"})

            assets_list = [{"type": "Savings Account & FDs", "amount": liquid_savings, "is_liquid": True}]
            help_list = [{"role": "Domestic Help", "monthly_cost": maid_cost}] if maid_cost > 0 else []

            with get_db_session() as db:
                success, msg = save_initial_onboarding(
                    db=db,
                    user_id=user_id,
                    state=state,
                    city_type=city_type,
                    household_size=hh_size,
                    members_data=members_list,
                    incomes_data=incomes_list,
                    obligations_data=obligations_list,
                    loans_data=loans_list,
                    assets_data=assets_list,
                    help_data=help_list
                )
                if success:
                    st.success("🎉 Household Profile successfully saved! Unlocking financial planners...")
                    st.rerun()
                else:
                    st.error(f"Validation Error: {msg}")


def show_active_profile(user_id: int):
    """Render existing active household profile, versioned editor, and audit history."""
    with get_db_session() as db:
        data = get_household_profile(db, user_id)
        history = get_version_history(db, user_id)

    prof = data["profile"]
    members = data["members"]
    incomes = data["incomes"]
    obligations = data["obligations"]
    loans = data["loans"]
    assets = data["assets"]
    help_recs = data["household_help"]

    tab_overview, tab_edit, tab_history = st.tabs(["🏠 Active Household Plan", "✏️ Edit & Version Expenses", "📜 What Changed (Audit Trail)"])

    # ---------------- TAB 1: OVERVIEW ----------------
    with tab_overview:
        col_m1, col_m2 = st.columns(2)
        total_income = sum(i.amount for i in incomes)
        total_fixed = sum(o.amount for o in obligations)

        with col_m1:
            st.metric("Total Monthly Household Inflow", format_inr(total_income))
        with col_m2:
            st.metric("Monthly Essential Obligations", format_inr(total_fixed))

        st.markdown("#### 👨‍👩‍👧 Family Composition")
        member_df = pd.DataFrame([{
            "Name": m.name,
            "Relation": m.relation,
            "Age": m.age,
            "Chronic Health Condition": "⚠️ Yes" if m.has_chronic_condition else "No"
        } for m in members])
        st.dataframe(member_df, use_container_width=True)

        st.markdown("#### 💼 Monthly Income Sources")
        inc_df = pd.DataFrame([{
            "Source": i.source_type,
            "Monthly Amount": format_inr(i.amount),
            "Type": "Variable (Gig/Biz)" if i.is_variable else "Fixed Salary",
            "Effective Since": i.effective_from.strftime("%d %b %Y")
        } for i in incomes])
        st.dataframe(inc_df, use_container_width=True)

        st.markdown("#### 🏷️ Active Essential Obligations")
        ob_df = pd.DataFrame([{
            "Category": o.category,
            "Amount": format_inr(o.amount),
            "Frequency": o.frequency,
            "Effective Since": o.effective_from.strftime("%d %b %Y")
        } for o in obligations])
        st.dataframe(ob_df, use_container_width=True)

    # ---------------- TAB 2: VERSIONED EDITING ----------------
    with tab_edit:
        st.markdown(
            f"""
            <div style="background-color: #FEF3C7; border-left: 4px solid {ACCENT_SAFFRON}; padding: 10px 14px; border-radius: 6px; font-size: 0.85rem; color: #78350F; margin-bottom: 1rem;">
                <strong>Versioning Guarantee:</strong> Profile edits never overwrite historical data. 
                Modifying rent or groceries closes the previous record and inserts a new version effective today.
            </div>
            """,
            unsafe_allow_html=True
        )

        edit_choice = st.selectbox(
            "Select Item to Update:",
            options=[o.category for o in obligations] + [f"Income: {i.source_type}" for i in incomes]
        )

        with st.form("versioned_edit_form"):
            if edit_choice.startswith("Income: "):
                source_type = edit_choice.replace("Income: ", "")
                target_inc = next((i for i in incomes if i.source_type == source_type), None)
                curr_val = target_inc.amount if target_inc else 0.0
                new_amt = st.number_input(f"New Monthly Income for {source_type} (₹)", min_value=0.0, value=float(curr_val), step=1000.0)
                is_var = st.checkbox("Is Income Variable", value=target_inc.is_variable if target_inc else False)
                save_edit = st.form_submit_button("Save New Income Version", type="primary")

                if save_edit:
                    with get_db_session() as db:
                        ok, msg = update_income_versioned(db, user_id, target_inc.id, new_amt, is_var)
                        st.success(msg)
                        st.rerun()
            else:
                target_ob = next((o for o in obligations if o.category == edit_choice), None)
                curr_val = target_ob.amount if target_ob else 0.0
                new_amt = st.number_input(f"New Monthly Amount for {edit_choice} (₹)", min_value=0.0, value=float(curr_val), step=500.0)
                save_edit = st.form_submit_button("Save New Obligation Version", type="primary")

                if save_edit:
                    with get_db_session() as db:
                        ok, msg = update_obligation_versioned(db, user_id, edit_choice, new_amt)
                        st.success(msg)
                        st.rerun()

    # ---------------- TAB 3: AUDIT HISTORY ----------------
    with tab_history:
        st.markdown("#### 📜 Chronological 'What Changed' Audit Trail")
        st.caption("Complete audit of all active and superseded financial versions.")
        if history:
            hist_df = pd.DataFrame(history)
            hist_df["Formatted Amount"] = hist_df["amount"].apply(lambda x: format_inr(x))
            display_cols = ["type", "item", "Formatted Amount", "effective_from", "effective_to", "status"]
            st.dataframe(hist_df[display_cols], use_container_width=True)
        else:
            st.info("No modifications recorded yet.")


def show_my_profile_page():
    st.set_page_config(page_title="My Household Profile - Parivar Arth", page_icon="👨‍👩‍👧", layout="centered")
    apply_theme()
    touch_session()

    user_id = get_current_user_id()
    if not user_id:
        st.warning("Please sign in from the Home page to view your profile.")
        st.stop()

    render_header(
        title="My Household Financial Profile",
        subtitle="Versioned profile engine with family structure-driven obligations",
        icon="👨‍👩‍👧"
    )

    with get_db_session() as db:
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        is_onboarded = profile.is_onboarding_completed if profile else False

    if not is_onboarded:
        show_onboarding_wizard(user_id)
    else:
        show_active_profile(user_id)

    render_footer()


if __name__ == "__main__":
    show_my_profile_page()
