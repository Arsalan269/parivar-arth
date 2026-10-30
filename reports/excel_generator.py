"""
Excel Spreadsheet Report Generator for Parivar Arth using openpyxl.
Produces an executive multi-sheet workbook covering overview metrics,
24-month cashflow projections, sinking fund allocations, and debt schedules.
"""

import io
from typing import Dict, Any, List
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def generate_household_excel_workbook(
    user_name: str,
    status_summary: Dict[str, Any],
    obligations: List[Dict[str, Any]],
    loans: List[Dict[str, Any]],
    shortfall_data: Dict[str, Any],
    emergency_data: Dict[str, Any]
) -> bytes:
    """Generate multi-tab formatted Excel report as bytes."""
    wb = Workbook()

    # Styling Tokens
    header_fill = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    sub_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    bold_font = Font(name="Calibri", size=10, bold=True)
    regular_font = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    # ---------------- SHEET 1: OVERVIEW ----------------
    ws1 = wb.active
    ws1.title = "Household Overview"
    ws1.views.sheetView[0].showGridLines = True

    ws1["A1"] = f"Parivar Arth Financial Health Report - {user_name}"
    ws1["A1"].font = Font(name="Calibri", size=14, bold=True, color="0B1F3A")

    ws1["A2"] = "Planning tool only, not financial or medical advice. Predictions are estimates."
    ws1["A2"].font = Font(name="Calibri", size=9, italic=True, color="64748B")

    overview_rows = [
        ("Monthly Take-Home Inflow", status_summary.get("total_income", 0.0)),
        ("Essential Living Obligations", status_summary.get("fixed_obligations", 0.0)),
        ("Monthly Debt Servicing (EMIs)", status_summary.get("total_emis", 0.0)),
        ("Current Monthly Net Surplus", status_summary.get("current_surplus", 0.0)),
        ("Debt-to-Income (DTI) Ratio (%)", f"{status_summary.get('dti', 0)}%"),
        ("Emergency Fund Runway (Months)", f"{emergency_data.get('runway_months', 0)} Months"),
        ("Emergency Fund Target", f"{emergency_data.get('target_months', 6)} Months"),
        ("Emergency Buffer Shortfall", emergency_data.get("shortfall", 0.0)),
        ("Household Risk Status", shortfall_data.get("status", "Safe")),
        ("Projected Month of Shortfall", shortfall_data.get("shortfall_month") or "None (Resilient)"),
        ("Surplus in 12 Months", shortfall_data.get("surplus_12m", 0.0)),
        ("Surplus in 24 Months", shortfall_data.get("surplus_24m", 0.0)),
    ]

    ws1["A4"] = "Metric"
    ws1["B4"] = "Value"
    ws1["A4"].fill = header_fill
    ws1["B4"].fill = header_fill
    ws1["A4"].font = header_font
    ws1["B4"].font = header_font

    for idx, (k, v) in enumerate(overview_rows, start=5):
        ws1[f"A{idx}"] = k
        ws1[f"B{idx}"] = v
        ws1[f"A{idx}"].font = regular_font
        ws1[f"B{idx}"].font = bold_font
        ws1[f"A{idx}"].border = thin_border
        ws1[f"B{idx}"].border = thin_border
        if isinstance(v, (int, float)):
            ws1[f"B{idx}"].number_format = "₹#,##0"

    # ---------------- SHEET 2: 24M PROJECTION ----------------
    ws2 = wb.create_sheet(title="24M Cashflow Projection")
    ws2.views.sheetView[0].showGridLines = True

    df_time = shortfall_data.get("timeline_df")
    if df_time is not None and not df_time.empty:
        headers = ["Month", "Projected Income", "Essential Expenses", "EMIs", "Total Outflows", "Net Surplus", "Is Shortfall"]
        for c_idx, h in enumerate(headers, start=1):
            cell = ws2.cell(row=1, column=c_idx, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        for r_idx, row in df_time.iterrows():
            row_num = r_idx + 2
            ws2.cell(row=row_num, column=1, value=int(row["Month"]))
            ws2.cell(row=row_num, column=2, value=float(row["Projected_Income"]))
            ws2.cell(row=row_num, column=3, value=float(row["Essential_Expenses"]))
            ws2.cell(row=row_num, column=4, value=float(row["EMIs"]))
            ws2.cell(row=row_num, column=5, value=float(row["Total_Outflows"]))
            ws2.cell(row=row_num, column=6, value=float(row["Net_Surplus"]))
            ws2.cell(row=row_num, column=7, value="YES (Deficit)" if row["Is_Shortfall"] else "No")

            for col in range(1, 8):
                c_cell = ws2.cell(row=row_num, column=col)
                c_cell.font = regular_font
                c_cell.border = thin_border
                if col in [2, 3, 4, 5, 6]:
                    c_cell.number_format = "₹#,##0"

    # ---------------- SHEET 3: OBLIGATIONS ----------------
    ws3 = wb.create_sheet(title="Fixed Obligations")
    ws3.views.sheetView[0].showGridLines = True

    headers_ob = ["Category", "Frequency", "Current Monthly Cost (₹)"]
    for c_idx, h in enumerate(headers_ob, start=1):
        cell = ws3.cell(row=1, column=c_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font

    for idx, ob in enumerate(obligations, start=2):
        ws3.cell(row=idx, column=1, value=str(ob.get("category", ""))).border = thin_border
        ws3.cell(row=idx, column=2, value=str(ob.get("frequency", "Monthly"))).border = thin_border
        amt_cell = ws3.cell(row=idx, column=3, value=float(ob.get("amount", 0)))
        amt_cell.border = thin_border
        amt_cell.number_format = "₹#,##0"

    # ---------------- SHEET 4: LOANS ----------------
    ws4 = wb.create_sheet(title="Loan Schedules")
    ws4.views.sheetView[0].showGridLines = True

    headers_ln = ["Loan Type", "Principal Balance (₹)", "Interest Rate (%)", "Monthly EMI (₹)", "Remaining Months", "Rate Type"]
    for c_idx, h in enumerate(headers_ln, start=1):
        cell = ws4.cell(row=1, column=c_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font

    for idx, ln in enumerate(loans, start=2):
        ws4.cell(row=idx, column=1, value=str(ln.get("loan_type", ""))).border = thin_border
        c2 = ws4.cell(row=idx, column=2, value=float(ln.get("balance", 0)))
        c2.number_format = "₹#,##0"
        c2.border = thin_border
        c3 = ws4.cell(row=idx, column=3, value=float(ln.get("interest_rate", 0)))
        c3.number_format = "0.0%"
        c3.border = thin_border
        c4 = ws4.cell(row=idx, column=4, value=float(ln.get("emi", 0)))
        c4.number_format = "₹#,##0"
        c4.border = thin_border
        ws4.cell(row=idx, column=5, value=int(ln.get("remaining_months", 0))).border = thin_border
        ws4.cell(row=idx, column=6, value=str(ln.get("rate_type", "Fixed"))).border = thin_border

    # Adjust column widths automatically
    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
