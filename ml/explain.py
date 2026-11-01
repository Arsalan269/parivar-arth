"""
Feature Importance and Attribution Explainability for Parivar Arth.
Translates technical feature importance scores
into plain-language economic explanations for Indian families.
"""

from typing import Dict, List, Any
import numpy as np


FEATURE_FRIENDLY_NAMES = {
    "crude_inr_pct_change": "International Crude Oil (INR)",
    "rainfall_departure": "Monsoon Rainfall Deficit / Surplus",
    "is_monsoon": "Monsoon Season Supply Impact",
    "is_festival": "Festival Season Demand (Diwali / Navratri)",
    "is_school_season": "Annual School Admission / Fee Revision Cycle",
    "repo_rate": "RBI Repo Rate (Cost of Borrowing)",
    "usd_inr_pct_change": "Rupee vs US Dollar Exchange Rate",
    "wpi_YoY": "Wholesale Price Inflation (WPI)",
    "base_effect_12m": "Base Effect from 12 Months Ago",
    "lag_1": "Recent 1-Month Inflation Momentum",
    "lag_12": "Annual Seasonal Cycle",
    "rolling_mean_3m": "Quarterly Inflation Trend",
    "rolling_std_3m": "Price Volatility",
}


def translate_feature_name(raw_name: str) -> str:
    """Return friendly Indian economic explanation for raw feature name."""
    return FEATURE_FRIENDLY_NAMES.get(raw_name, raw_name.replace("_", " ").title())


def generate_plain_language_explanation(
    category: str,
    top_features: List[tuple],
    forecast_value: float,
    current_value: float
) -> str:
    """
    Generate an intuitive, jargon-free summary explaining WHY this category's
    inflation forecast moved up or down.
    """
    direction = "rise" if forecast_value > current_value else "moderate"
    diff = abs(forecast_value - current_value)

    narratives = []
    for feat_name, imp in top_features[:3]:
        friendly = translate_feature_name(feat_name)
        if "crude" in feat_name:
            narratives.append(f"{friendly} moved fuel, LPG, and transport freight costs")
        elif "rainfall" in feat_name or "monsoon" in feat_name:
            narratives.append(f"{friendly} influenced vegetable and crop supply")
        elif "school" in feat_name:
            narratives.append("Annual academic calendar fee restructuring came into effect")
        elif "repo" in feat_name:
            narratives.append("RBI interest rate policy affected consumer demand and borrowing costs")
        elif "base_effect" in feat_name:
            narratives.append("Comparison with price levels from the same month last year (base effect)")
        else:
            narratives.append(f"{friendly} contributed to momentum")

    reasons_str = "; ".join(narratives)
    if not reasons_str:
        reasons_str = "ongoing price momentum and historical seasonality"

    return (
        f"{category} inflation is projected to {direction} to approximately {forecast_value:.1f}% "
        f"(a change of {diff:.1f}% from current levels). Key contributing factors: {reasons_str}."
    )


def get_top_drivers(
    importances: Dict[str, float],
    top_n: int = 5
) -> List[Dict[str, Any]]:
    """Format top N drivers for UI chart rendering."""
    sorted_items = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [
        {
            "feature": translate_feature_name(k),
            "raw_feature": k,
            "importance": round(float(v) * 100, 1)
        }
        for k, v in sorted_items
    ]
