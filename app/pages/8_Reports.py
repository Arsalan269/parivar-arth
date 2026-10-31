"""
Reports & Data Export Page for Parivar Arth.
Aether FinTech Design System - Executive PDF Statements and Multi-Sheet Excel Workbooks.
"""

import os
import sys
import streamlit as st
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import get_db_session
from core.security import touch_session, get_current_user_id
from core.profile_service import get_household_profile
from planner.shortfall import compute_shortfall_timeline
from planner.emergency import determine_emergency_fund_target_months, calculate_liquid_emergency_fund
from planner.loans import calculate_dti
from reports.pdf_generator import generate_household_pdf_report
from reports.excel_generator import generate_household_excel_workbook
from app.styles import (
    apply_theme, render_header, render_footer, render_metric_card,
    render_sidebar_brand, render_sidebar_user,
    PRIMARY_ACCENT, SECONDARY_ACCENT, SOFT_PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER_COLOR,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
)
from app.components.formatters import format_inr


def show_reports_page():
    st.set_page_config(
        page_title="Reports & Exports - Parivar Arth",
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
        st.warning("Please sign in to generate and export your household reports.")
        st.stop()

    user_name = user_data.get("name", "Household") if user_data else "Household"
    user_email = user_data.get("email", "") if user_data else ""

    with st.sidebar:
        render_sidebar_user(username=user_name, role="Primary Account")
        if st.button("Sign Out", key="rep_logout_btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    render_header(
        title="Household Statements & Export",
        subtitle="Generate executive, inflation-adjusted PDF statements and multi-tab Excel models",
        tag="Export"
    )

    with get_db_session() as db:
        profile_data = get_household_profile(db, user_id)

    incomes = profile_data.get("incomes", [])
    obligations = profile_data.get("obligations", [])
    loans = profile_data.get("loans", [])
    assets = profile_data.get("assets", [])
    members = profile_data.get("members", [])

    total_income = sum(float(getattr(i, "amount", 0.0)) for i in incomes)
    monthly_fixed = sum(float(getattr(o, "amount", 0.0)) for o in obligations)
    total_emis = sum(float(getattr(l, "emi", 0.0)) for l in loans)
    monthly_essentials = monthly_fixed + total_emis
    current_surplus = total_income - monthly_essentials
    dti, _, _ = calculate_dti(total_emis, total_income)

    obligation_dicts = [{"category": getattr(o, "category", "Other"), "amount": float(getattr(o, "amount", 0.0)), "frequency": getattr(o, "frequency", "Monthly")} for o in obligations]
    loan_dicts = [{"id": l.id, "loan_type": l.loan_type, "balance": l.balance, "interest_rate": l.interest_rate, "emi": l.emi, "remaining_months": l.remaining_months, "rate_type": l.rate_type} for l in loans]
    asset_dicts = [{"type": getattr(a, "type", "Asset"), "amount": float(getattr(a, "amount", 0.0)), "is_liquid": getattr(a, "is_liquid", False)} for a in assets]

    # Compute shortfall data
    shortfall_data = compute_shortfall_timeline(
        current_monthly_income=total_income,
        obligations=obligation_dicts,
        monthly_emis=total_emis,
        annual_income_increment_pct=5.0
    )

    # Compute emergency data
    target_m, _ = determine_emergency_fund_target_months(
        is_single_earner=len(incomes) <= 1,
        has_variable_income=any(bool(getattr(i, "is_variable", False)) for i in incomes),
        has_chronic_dependents=any(bool(getattr(m, "has_chronic_condition", False)) for m in members)
    )
    emergency_data = calculate_liquid_emergency_fund(asset_dicts, monthly_essentials, target_months=target_m)

    status_summary = {
        "total_income": total_income,
        "fixed_obligations": monthly_fixed,
        "total_emis": total_emis,
        "current_surplus": current_surplus,
        "dti": dti
    }

    # Snapshot Preview Card
    st.markdown(
        f"""
        <div class="aether-card" style="margin-bottom: 1.5rem; border-left: 4px solid {PRIMARY_ACCENT};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <div style="font-size: 1.05rem; font-weight: 700; color: {TEXT_PRIMARY};">
                    Statement Ready for Generation
                </div>
                <span class="status-badge status-purple">Verified Snapshot</span>
            </div>
            <div style="font-size: 0.88rem; color: {TEXT_SECONDARY}; line-height: 1.5;">
                Household Account: <strong>{user_name}</strong> ({user_email}) &bull;
                Shortfall Status: <strong>{shortfall_data['status']}</strong> &bull;
                Emergency Runway: <strong>{emergency_data['runway_months']:.1f} Months</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"""
            <div class="aether-card" style="min-height: 240px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div style="font-size: 1.15rem; font-weight: 700; color: {TEXT_PRIMARY};">Executive PDF Statement</div>
                        <span class="status-badge status-safe">Official</span>
                    </div>
                    <div style="font-size: 0.88rem; color: {TEXT_SECONDARY}; line-height: 1.5; margin-bottom: 16px;">
                        Formatted multi-page summary featuring household solvency badges, 24-month shortfall projections,
                        expense breakdown charts, and statutory disclaimers. Suitable for loan underwriters or family advisors.
                    </div>
                </div>
            """,
            unsafe_allow_html=True
        )
        pdf_bytes = generate_household_pdf_report(
            user_name=user_name,
            email=user_email,
            status_summary=status_summary,
            obligations=obligation_dicts,
            loans=loan_dicts,
            shortfall_data=shortfall_data,
            emergency_data=emergency_data
        )
        st.download_button(
            label="Download PDF Statement",
            data=pdf_bytes,
            file_name=f"Parivar_Arth_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown(
            f"""
            <div class="aether-card" style="min-height: 240px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div style="font-size: 1.15rem; font-weight: 700; color: {TEXT_PRIMARY};">Excel Financial Model</div>
                        <span class="status-badge status-purple">XLSX</span>
                    </div>
                    <div style="font-size: 0.88rem; color: {TEXT_SECONDARY}; line-height: 1.5; margin-bottom: 16px;">
                        Comprehensive multi-tab spreadsheet (.xlsx) complete with monthly cash flow projection columns,
                        full debt amortization schedules, obligation lists, and live formulas.
                    </div>
                </div>
            """,
            unsafe_allow_html=True
        )
        excel_bytes = generate_household_excel_workbook(
            user_name=user_name,
            status_summary=status_summary,
            obligations=obligation_dicts,
            loans=loan_dicts,
            shortfall_data=shortfall_data,
            emergency_data=emergency_data
        )
        st.download_button(
            label="Download Excel Workbook (.xlsx)",
            data=excel_bytes,
            file_name=f"Parivar_Arth_Workbook_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

    render_footer()


if __name__ == "__main__":
    show_reports_page()
