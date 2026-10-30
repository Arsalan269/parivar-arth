"""
Tool-Calling Functions for Parivar Arth AI Assistant.
Queries live aggregated figures and model projections for the authenticated user,
ensuring zero leakage of raw transaction logs or sensitive personal details.
"""

from typing import Dict, Any, List
from core.db import get_db_session
from core.profile_service import get_household_profile
from planner.shortfall import compute_shortfall_timeline
from planner.loans import calculate_dti, simulate_floating_repo_shock
from planner.emergency import determine_emergency_fund_target_months, calculate_liquid_emergency_fund
from planner.reduction import evaluate_necessary_expense_reductions
from app.components.formatters import format_inr


def tool_get_financial_status(user_id: int) -> Dict[str, Any]:
    """Return aggregated high-level financial health summary for the user."""
    with get_db_session() as db:
        data = get_household_profile(db, user_id)

    total_income = sum(i.amount for i in data["incomes"])
    monthly_fixed = sum(o.amount for o in data["obligations"])
    total_emis = sum(l.emi for l in data["loans"])
    monthly_essentials = monthly_fixed + total_emis
    current_surplus = total_income - monthly_essentials

    obligation_dicts = [{"category": o.category, "amount": o.amount} for o in data["obligations"]]
    shortfall = compute_shortfall_timeline(total_income, obligation_dicts, monthly_emis=total_emis)

    dti_val, dti_stat, _ = calculate_dti(total_emis, total_income)

    target_m, _ = determine_emergency_fund_target_months(
        is_single_earner=len(data["incomes"]) <= 1,
        has_variable_income=any(i.is_variable for i in data["incomes"]),
        has_chronic_dependents=any(m.has_chronic_condition for m in data["members"])
    )
    asset_dicts = [{"type": a.type, "amount": a.amount, "is_liquid": a.is_liquid} for a in data["assets"]]
    ef = calculate_liquid_emergency_fund(asset_dicts, monthly_essentials, target_months=target_m)

    return {
        "monthly_income": format_inr(total_income),
        "essential_outflows": format_inr(monthly_essentials),
        "current_monthly_surplus": format_inr(current_surplus),
        "status": shortfall["status"],
        "shortfall_month": shortfall["shortfall_month"] or "No shortfall within 24 months",
        "dti_ratio": f"{dti_val}% ({dti_stat})",
        "emergency_runway": f"{ef['runway_months']} Months (Target: {target_m} Months)",
        "explanation": shortfall["explanation"]
    }


def tool_project_expenses(user_id: int, months_ahead: int = 12) -> Dict[str, Any]:
    """Project future essential living expenses N months ahead."""
    with get_db_session() as db:
        data = get_household_profile(db, user_id)

    total_income = sum(i.amount for i in data["incomes"])
    monthly_emis = sum(l.emi for l in data["loans"])
    obligation_dicts = [{"category": o.category, "amount": o.amount} for o in data["obligations"]]

    shortfall = compute_shortfall_timeline(total_income, obligation_dicts, monthly_emis=monthly_emis, horizon_months=max(6, months_ahead))
    df = shortfall["timeline_df"]

    target_row = df[df["Month"] == months_ahead]
    if not target_row.empty:
        proj_exp = float(target_row["Essential_Expenses"].iloc[0])
        proj_surplus = float(target_row["Net_Surplus"].iloc[0])
    else:
        proj_exp = float(df["Essential_Expenses"].iloc[-1])
        proj_surplus = float(df["Net_Surplus"].iloc[-1])

    return {
        "months_ahead": months_ahead,
        "projected_monthly_essential_costs": format_inr(proj_exp),
        "projected_monthly_surplus": format_inr(proj_surplus),
        "shortfall_detected": proj_surplus < 0
    }


def tool_simulate_what_if(user_id: int, scenario_type: str, parameter_value: float = 0.0) -> Dict[str, Any]:
    """Simulate a what-if shock (e.g. repo hike, salary hike, job loss)."""
    with get_db_session() as db:
        data = get_household_profile(db, user_id)

    total_income = sum(i.amount for i in data["incomes"])
    total_emis = sum(l.emi for l in data["loans"])
    obligation_dicts = [{"category": o.category, "amount": o.amount} for o in data["obligations"]]

    norm = scenario_type.lower()
    if "salary" in norm or "hike" in norm:
        hike = parameter_value if parameter_value > 0 else 8.0
        shortfall = compute_shortfall_timeline(total_income, obligation_dicts, monthly_emis=total_emis, annual_income_increment_pct=hike)
        return {
            "scenario": f"Salary Increment of {hike}% per year",
            "status": shortfall["status"],
            "shortfall_month": shortfall["shortfall_month"] or "None (Comfortable surplus)",
            "surplus_at_24m": format_inr(shortfall["surplus_24m"])
        }
    elif "repo" in norm or "rate" in norm:
        bps = parameter_value if parameter_value > 0 else 50.0
        floating_loans = [l for l in data["loans"] if "home" in str(l.loan_type).lower() or l.rate_type == "Floating"]
        if floating_loans:
            sim = simulate_floating_repo_shock(floating_loans[0].balance, floating_loans[0].interest_rate, floating_loans[0].remaining_months, repo_change_bps=bps)
            return {
                "scenario": f"RBI Repo Rate Hike of +{bps} bps (+{bps/100:.2f}%)",
                "monthly_emi_increase": format_inr(sim["emi_increase"]),
                "new_emi": format_inr(sim["new_emi"]),
                "tenure_extension_months": f"+{sim['tenure_extension_months']} Months"
            }
        return {"scenario": "Repo Shock", "note": "No active floating loans registered to simulate."}
    else:
        # Default job loss simulation
        liquid = sum(a.amount for a in data["assets"] if a.is_liquid)
        monthly_cost = sum(o.amount for o in data["obligations"]) + total_emis
        runway = round(liquid / monthly_cost, 1) if monthly_cost > 0 else 0
        return {
            "scenario": "3-Month Income Stoppage",
            "liquid_buffer": format_inr(liquid),
            "monthly_burn_rate": format_inr(monthly_cost),
            "runway_months": f"{runway} Months",
            "absorbs_3_months": runway >= 3.0
        }
