"""
Shortfall Predictor & Gap Timeline Engine for Parivar Arth.
The flagship planning engine: projects income and compounded category expenditures
to detect the exact month when a family faces cash-flow distress.
"""

from datetime import date
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from planner.projection import project_household_expenses_trajectory, match_cpi_category


def compute_shortfall_timeline(
    current_monthly_income: float,
    obligations: List[Dict[str, Any]],
    monthly_emis: float = 0.0,
    annual_income_increment_pct: float = 5.0,
    min_savings_target_pct: float = 10.0,
    horizon_months: int = 24,
    category_forecast_map: Dict[str, List[float]] = None
) -> Dict[str, Any]:
    """
    Project income and essential expenses over horizon_months to identify cash-flow gaps.
    
    Returns:
        Dict with month-by-month trajectory DataFrame, surplus at 6/12/18/24 months,
        shortfall month, gap amounts, risk status, and plain-language explanation.
    """
    if current_monthly_income <= 0:
        current_monthly_income = 1.0  # guard against zero division

    # Step 1: Project essential expenditures
    df_exp = project_household_expenses_trajectory(
        obligations=obligations,
        horizon_months=horizon_months,
        forecast_map=category_forecast_map
    )

    timeline_records = []
    shortfall_month = None
    max_shortfall_amount = 0.0

    for m in range(1, horizon_months + 1):
        # Income with annual increment step (increments applied every 12 months)
        years_passed = m // 12
        inc_factor = (1.0 + (annual_income_increment_pct / 100.0)) ** years_passed
        proj_income = round(current_monthly_income * inc_factor, 2)

        # Essential expenses for month m
        essentials_m = float(df_exp.loc[df_exp["Month_Num"] == m, "Total_Essential"].iloc[0])
        total_outflow = round(essentials_m + monthly_emis, 2)

        # Minimum savings buffer reserve (e.g. 10% of income)
        savings_reserve = round(proj_income * (min_savings_target_pct / 100.0), 2)
        total_burden = total_outflow + savings_reserve

        # Gap = Income - Outflows
        net_surplus = round(proj_income - total_outflow, 2)
        gap_after_savings = round(proj_income - total_burden, 2)

        is_shortfall = net_surplus < 0
        if is_shortfall and shortfall_month is None:
            shortfall_month = m
            max_shortfall_amount = abs(net_surplus)

        timeline_records.append({
            "Month": m,
            "Projected_Income": proj_income,
            "Essential_Expenses": essentials_m,
            "EMIs": monthly_emis,
            "Total_Outflows": total_outflow,
            "Net_Surplus": net_surplus,
            "Surplus_After_Savings": gap_after_savings,
            "Is_Shortfall": is_shortfall
        })

    df_timeline = pd.DataFrame(timeline_records)

    # Milestones (Surplus now, 6m, 12m, 18m, 24m)
    current_surplus = round(current_monthly_income - (float(df_exp.loc[0, "Total_Essential"]) + monthly_emis), 2)
    surplus_6m = float(df_timeline.loc[df_timeline["Month"] == 6, "Net_Surplus"].iloc[0]) if len(df_timeline) >= 6 else current_surplus
    surplus_12m = float(df_timeline.loc[df_timeline["Month"] == 12, "Net_Surplus"].iloc[0]) if len(df_timeline) >= 12 else current_surplus
    surplus_18m = float(df_timeline.loc[df_timeline["Month"] == 18, "Net_Surplus"].iloc[0]) if len(df_timeline) >= 18 else current_surplus
    surplus_24m = float(df_timeline.loc[df_timeline["Month"] == 24, "Net_Surplus"].iloc[0]) if len(df_timeline) >= 24 else current_surplus

    # Determine Status & Explanation
    if shortfall_month is not None:
        if shortfall_month <= 6:
            status = "At Risk"
            badge = "🔴 At Risk"
            why = (
                f"Immediate deficit detected in Month {shortfall_month}. "
                f"Your compounded expenses (driven by food and housing inflation) exceed income by ₹{max_shortfall_amount:,.0f}."
            )
        else:
            status = "Watch"
            badge = "🟡 Watch"
            why = (
                f"Cash flow turns negative in Month {shortfall_month}. "
                f"While you have surplus today, category inflation (+6-8% across education and medical) "
                f"outpaces your assumed annual salary hike of {annual_income_increment_pct}%."
            )
    else:
        # Check buffer margin
        min_surplus = df_timeline["Net_Surplus"].min()
        if min_surplus < (current_monthly_income * 0.10):
            status = "Watch"
            badge = "🟡 Watch"
            why = (
                f"No outright negative shortfall within 24 months, but your safety surplus thins down to ₹{min_surplus:,.0f}/month. "
                "Any unexpected price surge or medical event could trigger cash-flow distress."
            )
        else:
            status = "Safe"
            badge = "🟢 Safe"
            why = (
                f"Healthy financial headroom! Your projected income increment ({annual_income_increment_pct}%/yr) "
                f"comfortably absorbs forecasted category inflation, retaining a ₹{surplus_24m:,.0f}/month surplus in Year 2."
            )

    # Extra income or cut needed
    needed_cut = max_shortfall_amount if shortfall_month else 0.0

    return {
        "timeline_df": df_timeline,
        "current_surplus": current_surplus,
        "surplus_6m": surplus_6m,
        "surplus_12m": surplus_12m,
        "surplus_18m": surplus_18m,
        "surplus_24m": surplus_24m,
        "shortfall_month": shortfall_month,
        "max_shortfall_amount": needed_cut,
        "status": status,
        "badge": badge,
        "explanation": why,
        "annual_increment_assumed": annual_income_increment_pct
    }
