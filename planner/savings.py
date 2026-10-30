"""
Savings Advisor Rule Engine & Benchmark Comparison for Parivar Arth.
Includes:
1. Rupee-impact ranked savings levers
2. Peer benchmark comparison against Indian Household Consumption Survey data
3. Generic idle cash deployment options with strict statutory disclaimers
"""

from typing import List, Dict, Any, Tuple
import numpy as np


def generate_savings_recommendations(
    monthly_income: float,
    monthly_expenses: float,
    liquid_emergency_fund: float,
    loans: List[Dict[str, Any]],
    wants_spending: float = 0.0,
    top_spending_categories: List[Tuple[str, float]] = None
) -> List[Dict[str, Any]]:
    """
    Execute rule engine ranking actionable savings recommendations by rupee impact.
    """
    if monthly_income <= 0:
        return []

    recommendations = []
    savings_amount = max(0.0, monthly_income - monthly_expenses)
    savings_rate = (savings_amount / monthly_income) * 100.0

    # Lever 1: High Interest Debt (Credit Cards / Personal Loans > 12%)
    high_int_loans = [l for l in loans if float(l.get("interest_rate", 0)) >= 12.0]
    if high_int_loans:
        highest_rate = max(l["interest_rate"] for l in high_int_loans)
        total_high_balance = sum(l.get("balance", 0) for l in high_int_loans)
        est_annual_rupee_loss = total_high_balance * (highest_rate / 100.0)
        recommendations.append({
            "category": "Debt Optimization",
            "priority": 1,
            "title": f"Prepay High-Cost Debt ({highest_rate}% APR)",
            "rupee_impact": round(est_annual_rupee_loss / 12.0, 0),
            "advice": (
                f"You have loans accumulating interest at {highest_rate}% APR. "
                f"Every ₹10,000 prepaid directly saves ~₹{highest_rate * 100:,.0f}/year in guaranteed interest outgo. "
                "Prioritize clearing this before allocating fresh money to low-return fixed deposits or mutual funds."
            )
        })

    # Lever 2: Emergency Fund Deficit
    target_ef = monthly_expenses * 3.0
    if liquid_emergency_fund < target_ef:
        ef_shortfall = target_ef - liquid_emergency_fund
        monthly_ef_sip = round(ef_shortfall / 12.0, 0)
        recommendations.append({
            "category": "Safety Net",
            "priority": 2,
            "title": "Establish 3-Month Liquid Emergency Buffer",
            "rupee_impact": monthly_ef_sip,
            "advice": (
                f"Your liquid emergency reserves (₹{liquid_emergency_fund:,.0f}) are below the minimum 3-month safety mark (₹{target_ef:,.0f}). "
                f"Set up an automatic monthly transfer of ₹{monthly_ef_sip:,.0f} into a sweep-in savings account or liquid fund."
            )
        })

    # Lever 3: Wants Exceeding 30% of Income
    wants_pct = (wants_spending / monthly_income) * 100.0 if monthly_income > 0 else 0
    if wants_pct > 30.0:
        excess_wants = wants_spending - (monthly_income * 0.30)
        recommendations.append({
            "category": "Discretionary Spending",
            "priority": 3,
            "title": "Cap Discretionary Wants at 30%",
            "rupee_impact": round(excess_wants, 0),
            "advice": (
                f"Discretionary spending (dining out, shopping, OTT, entertainment) is currently {wants_pct:.1f}% of income (₹{wants_spending:,.0f}). "
                f"Capping this at the standard 30% threshold immediately unlocks ₹{excess_wants:,.0f}/month for investments."
            )
        })

    # Lever 4: Low Savings Rate (< 10%)
    if savings_rate < 10.0:
        needed_saving = (monthly_income * 0.15) - savings_amount
        top_cats = top_spending_categories[:2] if top_spending_categories else [("Groceries", 0), ("Utilities", 0)]
        cat_names = ", ".join([c[0] for c in top_cats])
        recommendations.append({
            "category": "Core Budgeting",
            "priority": 4,
            "title": f"Elevate Household Savings Rate (Currently {savings_rate:.1f}%)",
            "rupee_impact": round(needed_saving, 0),
            "advice": (
                f"Your current savings rate ({savings_rate:.1f}%) is below the recommended 10-20% Indian household baseline. "
                f"Review spending in your top categories ({cat_names}) to recapture ₹{needed_saving:,.0f}/month."
            )
        })

    # Lever 5: Idle Cash Deployment
    if liquid_emergency_fund > (monthly_expenses * 6.0):
        surplus_idle = liquid_emergency_fund - (monthly_expenses * 6.0)
        recommendations.append({
            "category": "Wealth Accumulation",
            "priority": 5,
            "title": "Deploy Excess Idle Savings Above 6-Month Emergency Runway",
            "rupee_impact": round(surplus_idle * 0.07 / 12.0, 0),
            "advice": (
                f"You hold ₹{surplus_idle:,.0f} in liquid accounts above a conservative 6-month buffer. "
                "Money lingering in 3.0% savings accounts loses purchasing power to 6% inflation. "
                "Explore generic long-term options like Recurring Deposits (RD), Fixed Deposits (FD), Public Provident Fund (PPF), "
                "or index Mutual Fund SIPs. *Disclaimer: For educational planning only; consult a SEBI registered investment advisor.*"
            )
        })

    # Sort strictly by estimated rupee impact descending
    recommendations.sort(key=lambda x: x["rupee_impact"], reverse=True)
    return recommendations


def compare_with_consumption_benchmarks(
    city_type: str,
    household_size: int,
    monthly_income: float,
    current_food_spend: float,
    current_rent_spend: float
) -> Dict[str, Any]:
    """
    Compare family spending against NSSO / Household Consumption Survey benchmarks.
    Clearly labeled as approximate survey reference figures.
    """
    # Benchmarks as approximate % of monthly expenditure:
    # Metro: Food ~30-35%, Housing ~25-35%, Others ~35%
    # Tier-2/3: Food ~38-45%, Housing ~18-25%, Others ~35%
    # Rural: Food ~48-55%, Housing ~10-15%, Others ~35%
    c_lower = city_type.lower()
    if "metro" in c_lower or "tier-1" in c_lower:
        bench_food_pct = 32.0
        bench_rent_pct = 28.0
    elif "tier-2" in c_lower or "tier-3" in c_lower:
        bench_food_pct = 40.0
        bench_rent_pct = 20.0
    else:  # Rural
        bench_food_pct = 48.0
        bench_rent_pct = 12.0

    actual_food_pct = round((current_food_spend / monthly_income) * 100.0, 1) if monthly_income > 0 else 0
    actual_rent_pct = round((current_rent_spend / monthly_income) * 100.0, 1) if monthly_income > 0 else 0

    return {
        "city_type": city_type,
        "benchmark_food_pct": bench_food_pct,
        "actual_food_pct": actual_food_pct,
        "food_diff_pct": round(actual_food_pct - bench_food_pct, 1),
        "benchmark_rent_pct": bench_rent_pct,
        "actual_rent_pct": actual_rent_pct,
        "rent_diff_pct": round(actual_rent_pct - bench_rent_pct, 1),
        "note": "Reference figures based on MoSPI Household Consumption Expenditure Survey (HCES) averages. Approximate indicator only."
    }
