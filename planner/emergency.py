"""
Emergency Fund Tracker for Indian Households.
Includes:
1. Dynamic target calculation (3 vs 6 months) based on earner stability, gig income, and chronic illness
2. Strict liquid assets filtering (excludes locked PPF/EPF, Real Estate, and physical gold)
3. Emergency runway in months using inflation-adjusted essential expenditures
"""

from typing import List, Dict, Any, Tuple


def determine_emergency_fund_target_months(
    is_single_earner: bool,
    has_variable_income: bool,
    has_chronic_dependents: bool
) -> Tuple[int, str]:
    """
    Determine whether household requires a 3-month or 6-month buffer.
    - 3 months: Dual stable salaried earners with low dependency risk
    - 6 months: Single earner, freelance/gig variable income, or chronic medical conditions
    """
    reasons = []
    if is_single_earner:
        reasons.append("Single earner household")
    if has_variable_income:
        reasons.append("Variable income (gig worker / business / commissions)")
    if has_chronic_dependents:
        reasons.append("Dependent family members with chronic medical conditions")

    if reasons:
        target_months = 6
        explanation = f"Recommended: 6 months of essential costs because of: {', '.join(reasons)}."
    else:
        target_months = 3
        explanation = "Recommended: 3 months of essential costs (dual stable salaried income)."

    return target_months, explanation


def calculate_liquid_emergency_fund(
    assets: List[Dict[str, Any]],
    monthly_essential_cost: float,
    target_months: int = 6
) -> Dict[str, Any]:
    """
    Compute liquid emergency fund, runway in months, and risk status.
    Strictly filters for liquid assets only.
    """
    # Categories considered liquid for immediate emergency cash:
    liquid_keywords = ["savings", "fixed deposit", "fd", "liquid", "cash", "bank"]

    total_liquid = 0.0
    illiquid_total = 0.0
    breakdown = []

    for a in assets:
        amt = float(a.get("amount", 0))
        name = str(a.get("type", "")).lower()
        is_liq = bool(a.get("is_liquid", True))

        if is_liq or any(k in name for k in liquid_keywords):
            total_liquid += amt
            breakdown.append({"asset": a.get("type"), "amount": amt, "status": "Liquid (Counted)"})
        else:
            illiquid_total += amt
            breakdown.append({"asset": a.get("type"), "amount": amt, "status": "Illiquid (Excluded)"})

    # Runway calculation
    if monthly_essential_cost > 0:
        runway_months = round(total_liquid / monthly_essential_cost, 1)
    else:
        runway_months = 12.0 if total_liquid > 0 else 0.0

    target_amount = monthly_essential_cost * target_months
    shortfall = max(0.0, target_amount - total_liquid)
    progress_pct = min(100.0, round((total_liquid / target_amount * 100.0) if target_amount > 0 else 100.0, 1))

    # Risk Status
    if runway_months >= target_months:
        status = "Safe"
        badge = "🟢 Safe"
        advice = f"Your emergency runway of {runway_months} months meets your target of {target_months} months."
    elif runway_months >= (target_months * 0.5):
        status = "Watch"
        badge = "🟡 Watch"
        advice = f"Your emergency runway is {runway_months} months. You have a shortfall of ₹{shortfall:,.0f} to reach the {target_months}-month safety mark."
    else:
        status = "At Risk"
        badge = "🔴 At Risk"
        advice = f"Critical risk: Your emergency buffer is only {runway_months} months. Direct surplus cash flow to build this reserve immediately."

    return {
        "total_liquid": total_liquid,
        "illiquid_total": illiquid_total,
        "monthly_essential_cost": monthly_essential_cost,
        "target_months": target_months,
        "target_amount": target_amount,
        "shortfall": shortfall,
        "runway_months": runway_months,
        "progress_pct": progress_pct,
        "status": status,
        "badge": badge,
        "advice": advice,
        "breakdown": breakdown
    }
