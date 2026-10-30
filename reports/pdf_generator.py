"""
PDF Report Generator for Parivar Arth using fpdf2.
Produces a clean, branded household financial forecast report
with executive summary, inflation projections, debt status, and statutory disclaimer.
"""

import io
from datetime import datetime, date
from typing import Dict, Any, List
from fpdf import FPDF
from app.components.formatters import format_inr


def clean_pdf_text(text: Any) -> str:
    """Replace non-Latin-1 glyphs like rupee symbol with Rs. for standard Helvetica PDF."""
    if text is None:
        return ""
    return str(text).replace("₹", "Rs. ").replace("•", "-")



class ParivarReportPDF(FPDF):
    def header(self):
        # Teal banner
        self.set_fill_color(15, 118, 110)  # #0F766E
        self.rect(0, 0, 210, 18, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 13)
        self.set_xy(10, 4)
        self.cell(0, 10, "PARIVAR ARTH (Family Money Planner) - Financial Health Report", ln=0, align="L")
        self.ln(18)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 116, 139)
        disclaimer = "Planning tool only, not financial or medical advice. Predictions are estimates. Generated exclusively for your household."
        self.cell(0, 5, disclaimer, align="C", ln=1)
        self.cell(0, 5, f"Page {self.page_no()}/{{nb}}", align="C", ln=0)


def generate_household_pdf_report(
    user_name: str,
    email: str,
    status_summary: Dict[str, Any],
    obligations: List[Dict[str, Any]],
    loans: List[Dict[str, Any]],
    shortfall_data: Dict[str, Any],
    emergency_data: Dict[str, Any]
) -> bytes:
    """Generate printable PDF byte buffer."""
    pdf = ParivarReportPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)

    # 1. Household Info & Date
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(11, 31, 58)  # Navy
    pdf.cell(0, 8, f"Household Plan: {user_name}", ln=1)
    
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    now_str = datetime.now().strftime("%d %B %Y, %I:%M %p")
    pdf.cell(0, 5, f"Report Generated: {now_str} | Account: {email}", ln=1)
    pdf.ln(3)

    # 2. Executive Status Card
    status = shortfall_data.get("status", "Safe")
    if "Safe" in status:
        pdf.set_fill_color(220, 252, 231)  # Light Green
        pdf.set_text_color(21, 128, 61)
        badge = "STATUS: SAFE (Healthy Cash Flow & Emergency Runway)"
    elif "Watch" in status:
        pdf.set_fill_color(254, 243, 199)  # Light Amber
        pdf.set_text_color(180, 83, 9)
        badge = "STATUS: WATCH (Inflation Erosion or Buffer Shortfall)"
    else:
        pdf.set_fill_color(254, 226, 226)  # Light Red
        pdf.set_text_color(185, 28, 28)
        badge = "STATUS: AT RISK (Deficit Month Detected)"

    pdf.rect(10, pdf.get_y(), 190, 14, "F")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_xy(14, pdf.get_y() + 2)
    pdf.cell(180, 5, clean_pdf_text(badge), ln=1)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_x(14)
    explanation = shortfall_data.get("explanation", "")[:120]
    pdf.cell(180, 5, clean_pdf_text(explanation), ln=1)
    pdf.ln(6)

    # 3. Monthly Financial Summary Table
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(11, 31, 58)
    pdf.cell(0, 6, "1. Monthly Cash Inflow & Fixed Outflows", ln=1)

    income = status_summary.get("total_income", 0.0)
    fixed = status_summary.get("fixed_obligations", 0.0)
    emis = status_summary.get("total_emis", 0.0)
    surplus = status_summary.get("current_surplus", 0.0)

    pdf.set_font("Helvetica", "", 9)
    metrics = [
        ("Monthly Net Inflow (Take-Home)", format_inr(income)),
        ("Essential Living Obligations", format_inr(fixed)),
        ("Total Monthly Loan EMIs", format_inr(emis)),
        ("Net Current Monthly Surplus", format_inr(surplus)),
        ("Emergency Fund Runway Available", f"{emergency_data.get('runway_months', 0)} Months ({emergency_data.get('status', 'Watch')})"),
        ("Debt-to-Income (DTI) Ratio", f"{status_summary.get('dti', 0)}%"),
    ]

    for label, val in metrics:
        pdf.set_text_color(71, 85, 105)
        pdf.cell(120, 6, clean_pdf_text(label), border="B")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(11, 31, 58)
        pdf.cell(70, 6, clean_pdf_text(val), border="B", ln=1, align="R")
        pdf.set_font("Helvetica", "", 9)
    pdf.ln(5)

    # 4. 24-Month Future Projection Outlook
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(11, 31, 58)
    pdf.cell(0, 6, "2. Inflation-Compounded Projections (24-Month Outlook)", ln=1)

    shortfall_m = shortfall_data.get("shortfall_month")
    shortfall_str = f"Month {shortfall_m} (Deficit: {format_inr(shortfall_data.get('max_shortfall_amount', 0))})" if shortfall_m else "No shortfall within 24 months"

    proj_rows = [
        ("Surplus in 6 Months", format_inr(shortfall_data.get("surplus_6m", 0))),
        ("Surplus in 12 Months", format_inr(shortfall_data.get("surplus_12m", 0))),
        ("Surplus in 18 Months", format_inr(shortfall_data.get("surplus_18m", 0))),
        ("Surplus in 24 Months", format_inr(shortfall_data.get("surplus_24m", 0))),
        ("Projected Month of Shortfall", shortfall_str),
    ]

    for label, val in proj_rows:
        pdf.set_text_color(71, 85, 105)
        pdf.cell(120, 6, clean_pdf_text(label), border="B")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(11, 31, 58)
        pdf.cell(70, 6, clean_pdf_text(val), border="B", ln=1, align="R")
        pdf.set_font("Helvetica", "", 9)
    pdf.ln(5)

    # 5. Core Obligations Breakdown Table
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(11, 31, 58)
    pdf.cell(0, 6, "3. Registered Household Obligations", ln=1)

    # Table Header
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(90, 6, "Expense Category", border=1, fill=True)
    pdf.cell(40, 6, "Frequency", border=1, fill=True)
    pdf.cell(60, 6, "Current Monthly Cost", border=1, fill=True, ln=1, align="R")

    pdf.set_font("Helvetica", "", 8)
    for ob in obligations:
        cat = str(ob.get("category", "Other"))
        freq = str(ob.get("frequency", "Monthly"))
        amt = float(ob.get("amount", 0))
        pdf.cell(90, 5, clean_pdf_text(cat), border=1)
        pdf.cell(40, 5, clean_pdf_text(freq), border=1)
        pdf.cell(60, 5, clean_pdf_text(format_inr(amt)), border=1, ln=1, align="R")

    # Output to byte buffer
    return bytes(pdf.output())
