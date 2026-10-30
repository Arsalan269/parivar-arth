"""
Category Compound Inflation Projection Engine for Parivar Arth.
Projects individual expenditure items over 1 to 36 months using
category-specific inflation forecasts (Food, Housing, Fuel, Transport, Health, Education, Services).
"""

from datetime import date
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd


# Default annualized baseline fallback inflation rates if forecasts missing
DEFAULT_CATEGORY_INFLATION = {
    "Food and Beverages": 5.8,
    "Groceries": 5.8,
    "Food": 5.8,
    "Housing": 4.8,
    "Rent": 4.8,
    "Rent/EMI": 4.8,
    "Fuel and Light": 5.4,
    "Utilities": 5.4,
    "Transport and Communication": 5.2,
    "Commute": 5.2,
    "Fuel": 5.2,
    "Health": 7.0,
    "Parent Medical": 7.0,
    "Education": 7.5,
    "Child Education": 7.5,
    "Miscellaneous Services": 5.5,
    "Household Help": 6.5,
    "Other": 5.0,
}


def match_cpi_category(expense_category: str) -> str:
    """Map user expenditure category to official MoSPI CPI forecast category."""
    norm = str(expense_category).strip().lower()
    if "food" in norm or "groc" in norm or "veg" in norm or "milk" in norm:
        return "Food and Beverages"
    elif "rent" in norm or "hous" in norm:
        return "Housing"
    elif "util" in norm or "elect" in norm or "lpg" in norm or "gas" in norm:
        return "Fuel and Light"
    elif "transport" in norm or "commute" in norm or "fuel" in norm or "petrol" in norm or "diesel" in norm:
        return "Transport and Communication"
    elif "health" in norm or "medic" in norm or "doctor" in norm or "pharma" in norm:
        return "Health"
    elif "edu" in norm or "school" in norm or "college" in norm or "tuition" in norm or "fee" in norm:
        return "Education"
    elif "help" in norm or "maid" in norm or "cook" in norm:
        return "Miscellaneous Services"
    return "Miscellaneous Services"


def project_expense_item(
    current_monthly_cost: float,
    category: str,
    months_ahead: int,
    monthly_inflation_rates: List[float] = None,
    annual_rate_override: float = None
) -> float:
    """
    Project single expense item over N months using compounded monthly inflation:
    Cost(N) = Cost_0 * prod_{m=1}^{N} (1 + MonthlyInflation_m)
    """
    if current_monthly_cost <= 0 or months_ahead <= 0:
        return current_monthly_cost

    cpi_cat = match_cpi_category(category)

    if monthly_inflation_rates and len(monthly_inflation_rates) >= months_ahead:
        compound_factor = 1.0
        for m in range(months_ahead):
            # Monthly rate = annual / 12 / 100
            m_rate = (monthly_inflation_rates[m] / 100.0) / 12.0
            compound_factor *= (1.0 + m_rate)
        return round(current_monthly_cost * compound_factor, 2)
    else:
        # Annualized rate fallback
        annual_rate = annual_rate_override or DEFAULT_CATEGORY_INFLATION.get(cpi_cat, 5.5)
        monthly_rate = (annual_rate / 100.0) / 12.0
        return round(current_monthly_cost * ((1.0 + monthly_rate) ** months_ahead), 2)


def project_household_expenses_trajectory(
    obligations: List[Dict[str, Any]],
    horizon_months: int = 24,
    forecast_map: Dict[str, List[float]] = None
) -> pd.DataFrame:
    """
    Compute month-by-month projected costs across all obligations.
    
    Returns:
        DataFrame with columns [Month_Num, Category_1, ..., Category_K, Total_Essential]
    """
    forecasts = forecast_map or {}
    timeline = []

    for m in range(1, horizon_months + 1):
        row = {"Month_Num": m}
        total_m = 0.0

        for ob in obligations:
            cat = ob.get("category", "Other")
            amt = float(ob.get("amount", 0))
            cpi_cat = match_cpi_category(cat)

            rates = forecasts.get(cpi_cat, [])
            proj_amt = project_expense_item(amt, cat, m, monthly_inflation_rates=rates)
            row[cat] = proj_amt
            total_m += proj_amt

        row["Total_Essential"] = round(total_m, 2)
        timeline.append(row)

    return pd.DataFrame(timeline)
