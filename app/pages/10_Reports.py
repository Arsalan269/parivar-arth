"""
Reports & Data Export Page for Parivar Arth.
Generates downloadable, executive PDF (fpdf2) and multi-sheet Excel (openpyxl) reports
computed exclusively from the authenticated household's data.
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
from app.styles import apply_theme, render_header, render_footer, PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
from app.components.formatters import format_inr


def show_reports_page():
    st.set_page_config(page_title="Reports & Exports - Parivar Arth", page_icon="📑", layout="centered")
    apply_theme()
    touch_session()

    user_id = get_current_user_id()
    if not user_id:
        st.warning("Please sign in to generate and export your household reports.")
        st.stop()

    render_header(
        title="Household Reports & Exports",
        subtitle="Download official, inflation-adjusted PDF & Excel statements",
        icon="📑"
    )

    user_data = st.session_state.get("user", {})
    user_name = user_data.get("name", "Household")
    user_email = user_data.get("email", "")

    with get_db_session() as db:
        profile_data = get_household_profile(db, user_id)

    incomes = profile_data["incomes"]
    obligations = profile_data["obligations"]
    loans = profile_data["loans"]
    assets = profile_data["assets"]
    members = profile_data["members"]

    total_income = sum(i.amount for i in incomes)
    monthly_fixed = sum(o.amount for o in obligations)
    total_emis = sum(l.emi for l in loans)
    monthly_essentials = monthly_fixed + total_emis
    current_surplus = total_income - monthly_essentials
    dti, _, _ = calculate_dti(total_emis, total_income)

    obligation_dicts = [{"category": o.category, "amount": o.amount, "frequency": o.frequency} for o in obligations]
    loan_dicts = [{"id": l.id, "loan_type": l.loan_type, "balance": l.balance, "interest_rate": l.interest_rate, "emi": l.emi, "remaining_months": l.remaining_months, "rate_type": l.rate_type} for l in loans]
    asset_dicts = [{"type": a.type, "amount": a.amount, "is_liquid": a.is_liquid} for a in assets]

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
        has_variable_income=any(i.is_variable for i in incomes),
        has_chronic_dependents=any(m.has_chronic_condition for m in members)
    )
    emergency_data = calculate_liquid_emergency_fund(asset_dicts, monthly_essentials, target_months=target_m)

    status_summary = {
        "total_income": total_income,
        "fixed_obligations": monthly_fixed,
        "total_emis": total_emis,
        "current_surplus": current_surplus,
        "dti": dti
    }

    st.markdown(
        f"""
        <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; margin-bottom: 1.5rem;">
            <h4 style="margin: 0; color: {PRIMARY_TEAL};">Report Snapshot Ready for Export</h4>
            <p style="margin: 4px 0 0 0; color: #475569; font-size: 0.9rem;">
                Account: <strong>{user_name}</strong> ({user_email}) • 
                Household Risk Status: <strong>{shortfall_data['status']}</strong> • 
                Emergency Runway: <strong>{emergency_data['runway_months']} Months</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📄 Executive PDF Statement")
        st.write("Clean, branded executive summary with status badges, milestone tables, and statutory disclaimer.")
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
            label="⬇️ Download PDF Statement",
            data=pdf_bytes,
            file_name=f"Parivar_Arth_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )

    with col2:
        st.markdown("#### 📊 Comprehensive Excel Workbook")
        st.write("Multi-tab financial model (.xlsx) with 24-month cashflow projections, loan amortization, and obligations.")
        excel_bytes = generate_household_excel_workbook(
            user_name=user_name,
            status_summary=status_summary,
            obligations=obligation_dicts,
            loans=loan_dicts,
            shortfall_data=shortfall_data,
            emergency_data=emergency_data
        )
        st.download_button(
            label="⬇️ Download Excel Workbook (.xlsx)",
            data=excel_bytes,
            file_name=f"Parivar_Arth_Workbook_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    render_footer()


if __name__ == "__main__":
    show_reports_page()
