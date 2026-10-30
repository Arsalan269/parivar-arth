"""
Loan and Debt Engine for Parivar Arth.
Includes:
1. Debt-to-Income (DTI) ratio with Indian risk thresholds (>40% Watch, >50% At Risk)
2. Prepayment ranking: Avalanche (highest interest rate first) and Snowball (smallest balance first)
3. Floating rate sensitivity to RBI repo rate changes (EMI and tenure impact)
"""

from typing import List, Dict, Any, Tuple
import numpy as np


def calculate_dti(monthly_emis: float, monthly_income: float) -> Tuple[float, str, str]:
    """
    Calculate Debt-to-Income (DTI) ratio.
    Returns:
        (dti_pct, status_label, advice_note)
    """
    if monthly_income <= 0:
        return 100.0, "At Risk", "No reported income to service existing debts."

    dti = (monthly_emis / monthly_income) * 100.0

    if dti <= 30.0:
        return round(dti, 1), "Safe", "Healthy debt level well within safe Indian banking guidelines (<= 30%)."
    elif dti <= 45.0:
        return round(dti, 1), "Watch", "Moderate debt load (30-45%). Avoid taking fresh unsecured loans or credit card debt."
    else:
        return round(dti, 1), "At Risk", "High debt burden (> 45%). Prioritize debt prepayment to prevent cash-flow distress."


def compute_standard_emi(principal: float, annual_rate_pct: float, tenure_months: int) -> float:
    """Standard reducing balance EMI formula."""
    if principal <= 0 or tenure_months <= 0:
        return 0.0
    if annual_rate_pct <= 0:
        return principal / tenure_months

    r = (annual_rate_pct / 100.0) / 12.0
    emi = principal * r * ((1.0 + r) ** tenure_months) / (((1.0 + r) ** tenure_months) - 1.0)
    return round(float(emi), 2)


def simulate_floating_repo_shock(
    principal_balance: float,
    current_annual_rate: float,
    remaining_months: int,
    repo_change_bps: float = 50.0  # +50 bps = +0.50%
) -> Dict[str, Any]:
    """
    Simulate impact of RBI repo rate change on a floating rate loan (e.g. Home Loan).
    Computes both:
    1. Additional monthly EMI if tenure remains unchanged
    2. Additional months of tenure if EMI remains unchanged
    """
    current_emi = compute_standard_emi(principal_balance, current_annual_rate, remaining_months)
    new_rate = max(1.0, current_annual_rate + (repo_change_bps / 100.0))
    new_emi = compute_standard_emi(principal_balance, new_rate, remaining_months)
    emi_diff = round(new_emi - current_emi, 2)

    # Calculate tenure extension if EMI stays fixed
    r_new = (new_rate / 100.0) / 12.0
    # Formula: n = -log(1 - (P * r) / EMI) / log(1 + r)
    extended_months = remaining_months
    if current_emi > (principal_balance * r_new):
        n_calc = -np.log(1.0 - (principal_balance * r_new / current_emi)) / np.log(1.0 + r_new)
        extended_months = int(np.ceil(n_calc))
    else:
        extended_months = remaining_months + 60  # Negative amortization risk

    tenure_diff_months = max(0, extended_months - remaining_months)

    return {
        "current_rate": current_annual_rate,
        "new_rate": round(new_rate, 2),
        "current_emi": current_emi,
        "new_emi": new_emi,
        "emi_increase": emi_diff,
        "tenure_extension_months": tenure_diff_months,
    }


def rank_debt_prepayments(loans: List[Dict[str, Any]], extra_monthly_prepayment: float = 5000.0) -> Dict[str, Any]:
    """
    Generate Avalanche and Snowball prepayment recommendations.
    Avalanche: orders by interest_rate descending (mathematically maximizes interest saved).
    Snowball: orders by balance ascending (psychological quick wins).
    """
    if not loans:
        return {"avalanche": [], "snowball": [], "total_balance": 0, "total_emi": 0}

    # Clean loan entries
    cleaned_loans = []
    for ln in loans:
        cleaned_loans.append({
            "id": ln.get("id"),
            "loan_type": ln.get("loan_type", "Loan"),
            "balance": float(ln.get("balance", 0)),
            "interest_rate": float(ln.get("interest_rate", 9.0)),
            "emi": float(ln.get("emi", 0)),
            "remaining_months": int(ln.get("remaining_months", 12)),
            "rate_type": ln.get("rate_type", "Fixed")
        })

    total_balance = sum(l["balance"] for l in cleaned_loans)
    total_emi = sum(l["emi"] for l in cleaned_loans)

    # 1. Avalanche: Highest interest rate first
    avalanche_sorted = sorted(cleaned_loans, key=lambda x: x["interest_rate"], reverse=True)
    avalanche_plan = []
    for idx, l in enumerate(avalanche_sorted, start=1):
        # Approximate interest saved on this loan if extra prepayment directed here
        monthly_r = (l["interest_rate"] / 100.0) / 12.0
        est_interest_saved = round(extra_monthly_prepayment * monthly_r * min(l["remaining_months"], 12) * 1.5, 0)
        avalanche_plan.append({
            "priority": idx,
            "loan_type": l["loan_type"],
            "balance": l["balance"],
            "interest_rate": l["interest_rate"],
            "emi": l["emi"],
            "recommendation": f"Priority #{idx}: Prepay first at {l['interest_rate']}% APR. Est. annual interest saved: ₹{est_interest_saved:,.0f}."
        })

    # 2. Snowball: Smallest balance first
    snowball_sorted = sorted(cleaned_loans, key=lambda x: x["balance"])
    snowball_plan = []
    for idx, l in enumerate(snowball_sorted, start=1):
        months_to_clear = int(np.ceil(l["balance"] / (l["emi"] + extra_monthly_prepayment))) if (l["emi"] + extra_monthly_prepayment) > 0 else 0
        snowball_plan.append({
            "priority": idx,
            "loan_type": l["loan_type"],
            "balance": l["balance"],
            "interest_rate": l["interest_rate"],
            "emi": l["emi"],
            "recommendation": f"Priority #{idx}: Pay off {l['loan_type']} in ~{months_to_clear} months for a fast psychological win."
        })

    return {
        "avalanche": avalanche_plan,
        "snowball": snowball_plan,
        "total_balance": total_balance,
        "total_emi": total_emi,
        "extra_prepayment": extra_monthly_prepayment
    }
