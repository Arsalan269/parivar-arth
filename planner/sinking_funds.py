"""
Sinking Funds & 12-Month Cash-Flow Calendar Engine for Parivar Arth.
Converts annual/lump-sum obligations (school fees, term insurance, car servicing, festival travel)
into smoothed monthly sinking funds, applying category inflation forecasts.
"""

from datetime import date, datetime
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np


def compute_sinking_funds(
    recurring_items: List[Dict[str, Any]],
    current_month: int = None,
    category_inflation_map: Dict[str, float] = None
) -> List[Dict[str, Any]]:
    """
    Calculate required monthly reserve for recurring or annual expenses.
    
    Args:
        recurring_items: list of recurring expenses (name, amount, frequency, due_month, category)
        current_month: current calendar month (1-12)
        category_inflation_map: dict of category -> forecasted inflation rate % (e.g. {"Education": 7.5})
    """
    if current_month is None:
        current_month = date.today().month

    inflation_map = category_inflation_map or {}
    sinking_funds = []

    for item in recurring_items:
        raw_amt = float(item.get("amount", 0))
        freq = str(item.get("frequency", "Annual")).lower()
        due_m = item.get("due_month") or 12
        cat = item.get("category", "Miscellaneous Services")

        # Apply category inflation forecast
        inf_rate = inflation_map.get(cat, 6.0)
        inflated_due_amt = round(raw_amt * (1.0 + (inf_rate / 100.0)), 2)

        # Months remaining until due
        if due_m >= current_month:
            months_left = max(1, due_m - current_month)
        else:
            months_left = max(1, (12 - current_month) + due_m)

        # Sinking fund monthly allocation
        if "annual" in freq or "yearly" in freq:
            monthly_reserve = round(inflated_due_amt / 12.0, 2)
            urgent_monthly_reserve = round(inflated_due_amt / months_left, 2)
        elif "quarterly" in freq:
            monthly_reserve = round(inflated_due_amt / 3.0, 2)
            urgent_monthly_reserve = monthly_reserve
        elif "half" in freq:
            monthly_reserve = round(inflated_due_amt / 6.0, 2)
            urgent_monthly_reserve = monthly_reserve
        else:
            monthly_reserve = inflated_due_amt
            urgent_monthly_reserve = inflated_due_amt

        sinking_funds.append({
            "name": item.get("name", "Expense"),
            "category": cat,
            "base_amount": raw_amt,
            "inflated_due_amount": inflated_due_amt,
            "inflation_rate": inf_rate,
            "due_month": due_m,
            "months_left": months_left,
            "smoothed_monthly_reserve": monthly_reserve,
            "catch_up_monthly_reserve": urgent_monthly_reserve
        })

    return sinking_funds


def generate_12_month_cashflow_matrix(
    fixed_obligations: List[Dict[str, Any]],
    recurring_items: List[Dict[str, Any]],
    monthly_incomes: float,
    start_month_date: date = None,
    category_inflation_map: Dict[str, float] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Build a 12-month forward cash-flow projection matrix highlighting
    heavy expenditure months (admissions, festivals, renewals).
    """
    if start_month_date is None:
        start_month_date = date.today().replace(day=1)

    inflation_map = category_inflation_map or {}
    
    # Generate 12 forward month dates
    months = [start_month_date + pd.DateOffset(months=m) for m in range(12)]
    month_names = [m.strftime("%b %Y") for m in months]

    # Fixed core baseline
    base_fixed_monthly = sum(float(o.get("amount", 0)) for o in fixed_obligations)

    monthly_records = []
    heavy_months = []

    for idx, m_date in enumerate(months):
        cal_month = m_date.month

        # Month-specific lump sums due in cal_month
        lump_sum_total = 0.0
        lump_details = []

        for rec in recurring_items:
            rec_due = rec.get("due_month") or 12
            freq = str(rec.get("frequency", "Annual")).lower()

            is_due_this_month = False
            if "annual" in freq and rec_due == cal_month:
                is_due_this_month = True
            elif "quarterly" in freq and (cal_month % 3 == rec_due % 3):
                is_due_this_month = True
            elif "half" in freq and (cal_month % 6 == rec_due % 6):
                is_due_this_month = True

            if is_due_this_month:
                cat = rec.get("category", "Miscellaneous Services")
                inf = inflation_map.get(cat, 6.0)
                # Compounded for horizon
                compounded = float(rec.get("amount", 0)) * (1.0 + (inf / 100.0) * ((idx + 1) / 12.0))
                lump_sum_total += compounded
                lump_details.append(f"{rec.get('name')}: ₹{compounded:,.0f}")

        # Slight inflation creep on base monthly
        creep_factor = 1.0 + (0.055 * (idx / 12.0))
        projected_fixed = base_fixed_monthly * creep_factor

        total_outflow = round(projected_fixed + lump_sum_total, 2)
        net_surplus = round(monthly_incomes - total_outflow, 2)

        # Flag heavy months (outflow > 90% of income or lump sums > 30% of base)
        is_heavy = (total_outflow > (monthly_incomes * 0.90)) or (lump_sum_total > (base_fixed_monthly * 0.35))
        if is_heavy:
            heavy_months.append({
                "month": m_date.strftime("%B %Y"),
                "total_outflow": total_outflow,
                "net_surplus": net_surplus,
                "items": lump_details
            })

        monthly_records.append({
            "Month": m_date.strftime("%b %Y"),
            "Month_Num": cal_month,
            "Base_Fixed_Costs": round(projected_fixed, 2),
            "Lump_Sums_Due": round(lump_sum_total, 2),
            "Total_Outflow": total_outflow,
            "Projected_Income": round(monthly_incomes, 2),
            "Net_Surplus": net_surplus,
            "Is_Heavy_Month": is_heavy,
            "Lump_Details": "; ".join(lump_details) if lump_details else "Regular spending"
        })

    df_matrix = pd.DataFrame(monthly_records)
    summary = {
        "heavy_months_count": len(heavy_months),
        "heavy_months": heavy_months,
        "lowest_surplus_month": df_matrix.loc[df_matrix["Net_Surplus"].idxmin()]["Month"],
        "min_surplus": df_matrix["Net_Surplus"].min(),
        "total_annual_outflow": df_matrix["Total_Outflow"].sum(),
    }

    return df_matrix, summary
