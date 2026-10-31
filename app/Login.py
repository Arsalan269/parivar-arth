"""
Parivar Arth - Family Financial Intelligence Platform
Aether FinTech Design System - Login & Household Overview.
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
from core.security import touch_session, get_current_user_id
from app.styles import (
    apply_theme, render_header, render_footer, render_metric_card,
    render_sidebar_brand, render_sidebar_user,
    PRIMARY_ACCENT, SECONDARY_ACCENT, SOFT_PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER_COLOR,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER
)
from app.components.auth_forms import render_auth_tabs


def main():
    st.set_page_config(
        page_title="Parivar Arth - Family Financial Intelligence",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize tables if not already present
    init_db()

    # Auto-seed initial demo households & forecasts on fresh deployments
    with get_db_session() as db:
        if db.query(User).count() == 0:
            try:
                from scripts.seed_demo_data import seed_database
                seed_database()
            except Exception:
                pass

    # Apply Aether theme styling
    apply_theme()

    # 1. Session timeout check (20-minute threshold)
    if "user" in st.session_state and st.session_state["user"]:
        last_act = st.session_state.get("last_activity")
        if is_session_timed_out(last_act, timeout_minutes=20):
            st.session_state.clear()
            st.warning("Your session has expired after 20 minutes of inactivity. Please log in again to continue.")
            st.stop()
        else:
            touch_session()

    # Always render clean sidebar brand
    render_sidebar_brand()

    # 2. Authentication Gate
    user_data = st.session_state.get("user")
    if not user_data:
        render_header(
            title="Parivar Arth",
            subtitle="Family Financial Planning & Intelligence Platform",
            tag="Aether FinTech"
        )

        st.markdown(
            f"""
            <div class="aether-glass-card" style="margin-bottom: 2rem;">
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <div style="font-size: 1.15rem; font-weight: 700; color: {TEXT_PRIMARY};">
                        Anticipate Inflation. Secure Household Cash Flow.
                    </div>
                    <div style="font-size: 0.92rem; color: {TEXT_SECONDARY}; line-height: 1.6;">
                        Parivar Arth is a multi-user financial intelligence platform engineered for Indian households.
                        It projects category-wise inflation (groceries, school fees, healthcare, rent, energy), runs 1,000 Monte Carlo simulations,
                        and highlights cash-flow shortfall months up to 24 months in advance.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Center auth form container
        auth_col1, auth_col2, auth_col3 = st.columns([1, 2.5, 1])
        with auth_col2:
            render_auth_tabs()

        render_footer()
        st.stop()

    # 3. Authenticated Header & Navigation State
    user_id = user_data["user_id"]
    user_name = user_data["name"]

    # Sidebar User Profile & Actions
    with st.sidebar:
        render_sidebar_user(username=user_name, role="Primary Account")
        if st.button("Sign Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # 4. Mandatory Onboarding Check Guard
    with get_db_session() as db:
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        is_onboarded = profile.is_onboarding_completed if profile else False

    if not is_onboarded:
        render_header(
            title=f"Welcome, {user_name}",
            subtitle="Complete your household profile to initialize inflation forecasts and shortfall projections",
            tag="Onboarding Required"
        )

        st.markdown(
            f"""
            <div class="aether-card" style="text-align: center; padding: 2.5rem 1.5rem;">
                <div style="font-size: 1.25rem; font-weight: 700; color: {TEXT_PRIMARY}; margin-bottom: 0.5rem;">
                    Household Setup Needed
                </div>
                <div style="color: {TEXT_SECONDARY}; font-size: 0.95rem; max-width: 540px; margin: 0 auto 1.5rem auto; line-height: 1.6;">
                    To calculate your family's customized inflation rate, emergency fund target, and 24-month cash flow trajectory, please set up your household profile.
                </div>
                <div style="display: inline-block; background-color: {SOFT_PURPLE}; color: {PRIMARY_ACCENT}; padding: 8px 18px; border-radius: 9999px; font-weight: 600; font-size: 0.88rem;">
                    Open "My Profile" from the sidebar navigation to get started
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        render_footer()
        st.stop()

    # 5. Welcome Dashboard (Authenticated Overview)
    render_header(
        title=f"Welcome back, {user_name}",
        subtitle="Household Financial Intelligence & Cash Flow Overview",
        tag="Active Plan"
    )

    # Compute high-level snapshot for user
    with get_db_session() as db:
        from core.profile_service import get_household_profile
        from app.components.formatters import format_inr
        from planner.emergency import calculate_emergency_fund_target

        h_data = get_household_profile(db, user_id)
        total_income = sum(float(getattr(inc, "amount", 0.0)) for inc in h_data.get("incomes", []))
        total_obligations = sum(float(getattr(ob, "amount", 0.0)) for ob in h_data.get("obligations", []))
        total_emis = sum(float(getattr(ln, "emi", 0.0)) for ln in h_data.get("loans", []))
        total_liquid_savings = sum(
            float(getattr(a, "amount", 0.0))
            for a in h_data.get("assets", [])
            if getattr(a, "is_liquid", False)
        )

        # Calculate runway
        monthly_burn = total_obligations + total_emis
        has_var_inc = any(bool(getattr(inc, "is_variable", False)) for inc in h_data.get("incomes", []))
        has_dep_parents = any(str(getattr(m, "relation", "")).lower() == "parent" for m in h_data.get("members", []))
        ef_info = calculate_emergency_fund_target(
            monthly_essential_expenses=monthly_burn if monthly_burn > 0 else 1.0,
            earners_count=len(h_data.get("incomes", [])),
            has_variable_income=has_var_inc,
            has_dependent_parents=has_dep_parents,
            current_liquid_assets=total_liquid_savings
        )
        runway_months = ef_info.get("runway_months", 0.0)

    # 4 Aether Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card(
            label="Monthly Income",
            value=format_inr(total_income),
            subtext="Combined household inflows",
            badge_text="Inflows",
            badge_type="purple"
        )
    with m2:
        render_metric_card(
            label="Essential Outflows",
            value=format_inr(monthly_burn),
            subtext="Fixed obligations + loan EMIs",
            badge_text="Outflows",
            badge_type="watch" if monthly_burn > total_income * 0.7 else "safe"
        )
    with m3:
        render_metric_card(
            label="Liquid Reserves",
            value=format_inr(total_liquid_savings),
            subtext="Readily accessible savings & FDs",
            badge_text="Emergency Fund",
            badge_type="safe" if runway_months >= 6 else "watch"
        )
    with m4:
        runway_badge = "safe" if runway_months >= 6 else ("watch" if runway_months >= 3 else "risk")
        render_metric_card(
            label="Emergency Runway",
            value=f"{runway_months:.1f} Mo",
            subtext="Coverage at current burn rate",
            badge_text=runway_badge.upper(),
            badge_type=runway_badge
        )

    # Risk Status Banner
    if runway_months >= 6:
        banner_border = "#A7F3D0"
        banner_bg = "#E6F8F3"
        banner_title = "Financial Health: Robust Emergency Runway"
        banner_color = COLOR_SUCCESS
        banner_text = f"Your household holds {runway_months:.1f} months of essential runway in liquid reserves. Your family is well-cushioned against unexpected shocks."
    elif runway_months >= 3:
        banner_border = "#FDE68A"
        banner_bg = "#FFFBEB"
        banner_title = "Financial Health: Moderate Watch State"
        banner_color = COLOR_WARNING
        banner_text = f"Your household runway is {runway_months:.1f} months. Build reserves toward the 6-month threshold before taking on discretionary commitments."
    else:
        banner_border = "#FECACA"
        banner_bg = "#FEF2F2"
        banner_title = "Financial Health: Elevated Shortfall Risk"
        banner_color = COLOR_DANGER
        banner_text = f"Current runway is {runway_months:.1f} months, which is below the recommended safety buffer. Explore the 'Reduce Expenses' section to shore up cash flow."

    st.markdown(
        f"""
        <div style="background-color: {banner_bg}; border: 1px solid {banner_border}; border-radius: 14px; padding: 14px 18px; margin: 1.5rem 0;">
            <div style="font-weight: 700; color: {banner_color}; font-size: 0.95rem; margin-bottom: 2px;">{banner_title}</div>
            <div style="font-size: 0.88rem; color: {TEXT_PRIMARY}; line-height: 1.5;">{banner_text}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Feature Grid Cards
    st.markdown(
        f"""
        <div style="margin-top: 1.5rem; margin-bottom: 0.75rem;">
            <h3 style="font-size: 1.25rem; font-weight: 700; color: {TEXT_PRIMARY}; margin: 0;">Planning Modules</h3>
            <p style="font-size: 0.85rem; color: {TEXT_SECONDARY}; margin: 2px 0 0 0;">Navigate using the sidebar to explore each financial module</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        st.markdown(
            f"""
            <div class="aether-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: 700; color: {TEXT_PRIMARY}; font-size: 1.05rem;">Future Shortfall Predictor</div>
                    <span class="status-badge status-purple">Monte Carlo</span>
                </div>
                <div style="font-size: 0.88rem; color: {TEXT_SECONDARY}; line-height: 1.5; margin-bottom: 12px;">
                    Simulate 24 months of multi-category Indian inflation across 1,000 probabilistic scenarios. Pinpoint the exact month a deficit might occur.
                </div>
                <div style="font-size: 0.82rem; font-weight: 600; color: {PRIMARY_ACCENT};">
                    Open "Future Planner" in sidebar &rarr;
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            f"""
            <div class="aether-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: 700; color: {TEXT_PRIMARY}; font-size: 1.05rem;">12-Month Sinking Funds</div>
                    <span class="status-badge status-safe">Cash Flow</span>
                </div>
                <div style="font-size: 0.88rem; color: {TEXT_SECONDARY}; line-height: 1.5; margin-bottom: 12px;">
                    Smooth out high-expense spikes such as school admissions, festive purchases, and insurance renewals into steady monthly allocations.
                </div>
                <div style="font-size: 0.82rem; font-weight: 600; color: {PRIMARY_ACCENT};">
                    Open "Yearly Calendar" in sidebar &rarr;
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with f_col2:
        st.markdown(
            f"""
            <div class="aether-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: 700; color: {TEXT_PRIMARY}; font-size: 1.05rem;">Actionable Expense Levers</div>
                    <span class="status-badge status-watch">Optimization</span>
                </div>
                <div style="font-size: 0.88rem; color: {TEXT_SECONDARY}; line-height: 1.5; margin-bottom: 12px;">
                    Implement realistic, dignified strategies across electricity slab tariffs, fuel routes, grocery substitutes, and OTT audits to reclaim cash flow.
                </div>
                <div style="font-size: 0.82rem; font-weight: 600; color: {PRIMARY_ACCENT};">
                    Open "Reduce Expenses" in sidebar &rarr;
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            f"""
            <div class="aether-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: 700; color: {TEXT_PRIMARY}; font-size: 1.05rem;">Executive Reports</div>
                    <span class="status-badge status-purple">Export</span>
                </div>
                <div style="font-size: 0.88rem; color: {TEXT_SECONDARY}; line-height: 1.5; margin-bottom: 12px;">
                    Generate comprehensive PDF summary statements and multi-sheet Excel workbooks with a single click for loan applications or family reviews.
                </div>
                <div style="font-size: 0.82rem; font-weight: 600; color: {PRIMARY_ACCENT};">
                    Open "Reports" in sidebar &rarr;
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Indian Context Insight Callout
    st.markdown(
        f"""
        <div style="background-color: {BG_CARD}; border: 1px solid {BORDER_COLOR}; border-radius: 14px; padding: 16px 20px; margin-top: 1rem; margin-bottom: 1.5rem;">
            <div style="font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: {PRIMARY_ACCENT}; margin-bottom: 4px;">
                FinTech Insight: Multi-Tier Inflation Dynamics
            </div>
            <div style="font-size: 0.88rem; color: {TEXT_SECONDARY}; line-height: 1.6;">
                General CPI fails to capture the true cost-of-living increase for middle-class Indian families.
                While consumer electronics often experience low inflation, essential services such as private schooling (8-12% annual rise)
                and specialized healthcare (10-14% annual rise) outpace standard wage increases. Parivar Arth projects these separately to safeguard your long-term goals.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    render_footer()


if __name__ == "__main__":
    main()
