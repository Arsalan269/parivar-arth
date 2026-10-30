"""
Parivar Arth (Family Money Planner) - Main Application Entrypoint.
Multi-user, ML-powered personal finance planner for Indian households.
"""

import os
import sys
import streamlit as st

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import init_db, get_db_session
from core.models import User, Profile
from core.auth import is_session_timed_out
from core.security import touch_session, get_current_user_id, is_admin_user
from app.styles import apply_theme, render_header, render_footer, PRIMARY_TEAL, ACCENT_SAFFRON
from app.components.auth_forms import render_auth_tabs


def main():
    st.set_page_config(
        page_title="Parivar Arth - Family Money Planner",
        page_icon="₹",
        layout="centered",
        initial_sidebar_state="expanded"
    )

    # Initialize tables if not already present
    init_db()

    # Auto-seed initial demo households & forecasts on fresh deployments (e.g. Streamlit Cloud)
    with get_db_session() as db:
        if db.query(User).count() == 0:
            try:
                from scripts.seed_demo_data import seed_database
                seed_database()
            except Exception:
                pass

    # Apply Indian Warmth theme styling
    apply_theme()

    # 1. Session timeout check (20-minute threshold)
    if "user" in st.session_state and st.session_state["user"]:
        last_act = st.session_state.get("last_activity")
        if is_session_timed_out(last_act, timeout_minutes=20):
            st.session_state.clear()
            st.warning("⏱️ Your session has expired after 20 minutes of inactivity. Please log in again to continue.")
            st.stop()
        else:
            touch_session()

    # 2. Authentication Gate
    user_data = st.session_state.get("user")
    if not user_data:
        render_header(
            title="Parivar Arth (परिवार अर्थ)",
            subtitle="ML-powered personal finance & inflation-adjusted planner for Indian families",
            icon="₹ 📈"
        )
        st.markdown(
            f"""
            <div style="background-color: #E6F4F2; border-left: 4px solid {PRIMARY_TEAL}; padding: 12px 16px; border-radius: 8px; margin-bottom: 1.5rem;">
                <strong style="color: {PRIMARY_TEAL};">Prices keep rising, but family budgets do not adjust in time.</strong><br>
                <span style="font-size: 0.9rem; color: #334155;">
                Parivar Arth forecasts category-wise Indian inflation (groceries, school fees, medical care, rent, fuel) 
                and shows your household's future costs, shortfall risks, and savings opportunities in advance.
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
        render_auth_tabs()
        render_footer()
        st.stop()

    # 3. Authenticated Header & Navigation State
    user_id = user_data["user_id"]
    user_name = user_data["name"]
    user_role = user_data.get("role", "user")

    # Sidebar Profile & Logout
    with st.sidebar:
        st.markdown(f"### 👤 {user_name}")
        role_badge = "👑 Admin" if user_role == "admin" else "🏠 Household"
        st.caption(f"{user_data['email']} • {role_badge}")

        if st.button("Log Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        st.markdown("---")
        st.markdown("#### 🧭 Quick Navigation")
        st.markdown(
            """
            - 🏠 **Home & Health Check**
            - 📈 **Inflation Trends & Forecasts**
            - 👨‍👩‍👧 **My Household Profile**
            - 📊 **Monthly Expense Tracker**
            - 💡 **Savings Advisor**
            - 🔮 **Future Planner (Shortfall Engine)**
            - ✂️ **Reduce Necessary Expenses**
            - 💳 **Loans & Emergency Fund**
            - 📅 **12-Month Cashflow Calendar**
            - 📑 **PDF / Excel Reports**
            - 🤖 **Parivar AI Assistant**
            - 📖 **User Guide & Glossary**
            """
        )
        if user_role == "admin":
            st.markdown("- ⚙️ **Admin System Metrics**")

    # 4. Mandatory Onboarding Check Guard
    with get_db_session() as db:
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        is_onboarded = profile.is_onboarding_completed if profile else False

    if not is_onboarded:
        render_header(
            title=f"Namaste, {user_name}!",
            subtitle="Step 1 of 1: Complete your household financial profile to unlock forecasts & planning",
            icon="📝"
        )
        st.info("👋 Welcome to Parivar Arth! Before we can calculate your personalized inflation projection, please complete your mandatory household profile. Navigate to **My Household Profile** or fill in the onboarding form.")
        
        # We will mount the Onboarding Wizard in Phase 3
        st.markdown(
            f"""
            <div style="text-align: center; padding: 2rem 1rem;">
                <p style="color: #64748B;">Please proceed to <strong>'My Household Profile'</strong> from the navigation sidebar to enter family members, monthly earnings, rent/EMI, and grocery estimates.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        render_footer()
        st.stop()

    # 5. Welcome Dashboard
    render_header(
        title=f"Namaste, {user_name}!",
        subtitle="Here is your family's financial health summary",
        icon="₹ 📈"
    )

    # Compute high-level snapshot for user
    with get_db_session() as db:
        from core.profile_service import get_household_profile
        from app.components.formatters import format_inr
        from planner.emergency import calculate_emergency_fund_target

        h_data = get_household_profile(db, user_id)
        total_income = sum(float(inc.monthly_amount) for inc in h_data["incomes"])
        total_obligations = sum(float(ob.monthly_amount) for ob in h_data["obligations"])
        total_emis = sum(float(ln.monthly_emi) for ln in h_data["loans"])
        total_liquid_savings = sum(float(a.current_value) for a in h_data["assets"] if a.is_liquid)
        
        # Calculate runway
        monthly_burn = total_obligations + total_emis
        ef_info = calculate_emergency_fund_target(
            monthly_essential_expenses=monthly_burn if monthly_burn > 0 else 1.0,
            earners_count=len(h_data["incomes"]),
            has_variable_income=any(getattr(inc, "income_type", "") == "variable" for inc in h_data["incomes"]),
            has_dependent_parents=any(getattr(m, "relationship", "") == "parent" for m in h_data["members"]),
            current_liquid_assets=total_liquid_savings
        )
        runway_months = ef_info.get("current_runway_months", 0.0)

    # 4 Quick Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Monthly Income", format_inr(total_income))
    with c2:
        st.metric("Essential Outflows", format_inr(monthly_burn))
    with c3:
        st.metric("Liquid Emergency Fund", format_inr(total_liquid_savings))
    with c4:
        st.metric("Emergency Runway", f"{runway_months:.1f} Months")

    # Risk Status Banner
    if runway_months >= 6:
        status_html = '<div style="background-color: #DCFCE7; border: 1px solid #86EFAC; border-radius: 10px; padding: 12px 16px; margin: 1rem 0;">🟢 <strong style="color: #15803D;">Financial Stance: SAFE</strong> — Your family has healthy emergency reserves (> 6 months runway).</div>'
    elif runway_months >= 3:
        status_html = '<div style="background-color: #FEF3C7; border: 1px solid #FDE68A; border-radius: 10px; padding: 12px 16px; margin: 1rem 0;">🟡 <strong style="color: #B45309;">Financial Stance: WATCH</strong> — Emergency runway is between 3 to 6 months. Maintain budget discipline.</div>'
    else:
        status_html = '<div style="background-color: #FEE2E2; border: 1px solid #FCA5A5; border-radius: 10px; padding: 12px 16px; margin: 1rem 0;">🔴 <strong style="color: #B91C1C;">Financial Stance: AT RISK</strong> — Emergency runway is under 3 months. Review expense reduction levers.</div>'
    
    st.markdown(status_html, unsafe_allow_html=True)

    # Quick Feature Links Cards
    st.markdown("### 🚀 Key Planning Features")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            f"""
            <div class="parivar-card">
                <h4 style="margin-top: 0; color: #0F766E;">🔮 Future Shortfall Predictor</h4>
                <p style="font-size: 0.9rem; color: #475569;">
                    See the exact month your household might face a cash-flow gap with 24-month compounding inflation and 1,000-run Monte Carlo simulation.
                </p>
                <p style="font-size: 0.85rem; color: #0F766E; font-weight: 600;">👉 Navigate to <em>Future Planner</em> in sidebar</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            f"""
            <div class="parivar-card">
                <h4 style="margin-top: 0; color: #0F766E;">📈 Category Inflation Trends</h4>
                <p style="font-size: 0.9rem; color: #475569;">
                    Explore official MoSPI CPI inflation forecasts for Groceries, School Fees, Medical Care, Rent, and Fuel backed by ML models.
                </p>
                <p style="font-size: 0.85rem; color: #0F766E; font-weight: 600;">👉 Navigate to <em>Inflation Trends</em> in sidebar</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_b:
        st.markdown(
            f"""
            <div class="parivar-card">
                <h4 style="margin-top: 0; color: #0F766E;">✂️ Reduce Necessary Expenses</h4>
                <p style="font-size: 0.9rem; color: #475569;">
                    Actionable, dignified levers to trim rent, electricity slab tariffs, fuel, grocery substitutes, and OTT subscriptions.
                </p>
                <p style="font-size: 0.85rem; color: #0F766E; font-weight: 600;">👉 Navigate to <em>Reduce Expenses</em> in sidebar</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            f"""
            <div class="parivar-card">
                <h4 style="margin-top: 0; color: #0F766E;">📑 Download Health Reports</h4>
                <p style="font-size: 0.9rem; color: #475569;">
                    Export your complete 24-month inflation trajectory to an official executive PDF or multi-tab Excel workbook with one click.
                </p>
                <p style="font-size: 0.85rem; color: #0F766E; font-weight: 600;">👉 Navigate to <em>Reports</em> in sidebar</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Indian Household Context Tip
    st.markdown(
        """
        <div style="background-color: #F8FAFC; border-left: 4px solid #F59E0B; padding: 12px 16px; border-radius: 8px; margin-top: 0.5rem; margin-bottom: 1.5rem;">
            <strong style="color: #B45309;">💡 Indian Family Budget Tip:</strong><br>
            <span style="font-size: 0.9rem; color: #334155;">
            In India, food and fuel carry the highest month-to-month volatility, while education fees and healthcare rise at structural rates of 8% to 12% annually. Parivar Arth projects these separately so your children's schooling and parents' medical care are never under-budgeted.
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    render_footer()


if __name__ == "__main__":
    main()
