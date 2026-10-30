"""
'Reduce My Necessary Expenses' Engine for Parivar Arth.
Identifies realistic room to reduce essential costs without making unrealistic promises.
Ranks actionable category-specific levers strictly by monthly rupee impact.
"""

from typing import List, Dict, Any, Tuple


def evaluate_necessary_expense_reductions(
    monthly_income: float,
    obligations: List[Dict[str, Any]],
    loans: List[Dict[str, Any]],
    food_inflation_forecast: float = 6.0
) -> List[Dict[str, Any]]:
    """
    Examine core obligations and surface category-specific reduction opportunities
    ranked by monthly rupee impact.
    """
    if monthly_income <= 0:
        return []

    reduction_levers = []
    ob_map = {ob.get("category"): float(ob.get("amount", 0)) for ob in obligations}

    # 1. Housing / Rent (Flag if > 30-35% of income)
    rent_val = ob_map.get("Rent/EMI") or ob_map.get("Housing") or ob_map.get("Rent") or 0.0
    rent_pct = (rent_val / monthly_income) * 100.0 if monthly_income > 0 else 0
    if rent_pct > 32.0 and rent_val > 15000:
        # Realistic room to reduce via renegotiation, lease extension, or relocating 2-3km out
        est_save_pct = 12.0
        est_save_rupees = round(rent_val * (est_save_pct / 100.0), 0)
        reduction_levers.append({
            "category": "Housing & Rent",
            "current_spend": rent_val,
            "est_monthly_saving": est_save_rupees,
            "title": f"Renegotiate or Rationalize Housing (Currently {rent_pct:.0f}% of Income)",
            "action": (
                f"Rent/Housing occupies ₹{rent_val:,.0f} ({rent_pct:.0f}% of income), well above the healthy 30% ceiling. "
                "Practical actions: (1) Request a lease renewal freeze instead of standard 10% annual escalation, "
                "(2) Explore residential clusters within 2-4 km connected by Metro/commute, which typically save 10-15%."
            ),
            "difficulty": "Medium-High"
        })

    # 2. Loan Refinancing / Balance Transfer
    for ln in loans:
        rate = float(ln.get("interest_rate", 0))
        balance = float(ln.get("balance", 0))
        l_type = str(ln.get("loan_type", "")).lower()

        # Home loans above 9.0% or Personal loans above 14% have refinancing potential
        if "home" in l_type and rate > 9.0 and balance > 1500000:
            # 50-75 bps balance transfer saving
            rate_delta = 0.65
            monthly_saving = round(balance * (rate_delta / 100.0) / 12.0, 0)
            reduction_levers.append({
                "category": "Home Loan Refinancing",
                "current_spend": float(ln.get("emi", 0)),
                "est_monthly_saving": monthly_saving,
                "title": f"Refinance Home Loan (Switch from {rate}% to current market ~8.5%)",
                "action": (
                    f"Your outstanding balance of ₹{balance:,.0f} is priced at {rate}% APR. "
                    f"Executing an external benchmark balance transfer to top-tier lenders at 8.45-8.60% "
                    f"saves approximately ₹{monthly_saving:,.0f}/month in interest outgo."
                ),
                "difficulty": "Medium"
            })

    # 3. Electricity & Utilities Slab Optimization
    util_val = ob_map.get("Utilities", 0.0)
    if util_val >= 3500:
        # Indian state discom slabs have steep tariffs past 200/300 units
        est_util_save = round(util_val * 0.18, 0)
        reduction_levers.append({
            "category": "Electricity & Utilities",
            "current_spend": util_val,
            "est_monthly_saving": est_util_save,
            "title": "Discom Tariff Slab Awareness & Appliance Optimization",
            "action": (
                f"Utility bills (₹{util_val:,.0f}) often cross higher tariff slabs during peak summer AC months. "
                "Actions: (1) Set inverter AC thermostats to 24°C-25°C (each degree lower increases bill by 6%), "
                "(2) Clean condenser coils, (3) Transition to induction cooktops when piped LPG tariffs rise."
            ),
            "difficulty": "Easy"
        })

    # 4. Groceries: Seasonal Substitution During Forecast Spikes
    groc_val = ob_map.get("Groceries", 0.0)
    if groc_val >= 10000:
        est_groc_save = round(groc_val * 0.12, 0)
        spike_warning = f" (ML Forecast: Food inflation is running high at {food_inflation_forecast:.1f}%)" if food_inflation_forecast > 6.0 else ""
        reduction_levers.append({
            "category": "Groceries & Food",
            "current_spend": groc_val,
            "est_monthly_saving": est_groc_save,
            "title": f"Seasonal Vegetable & Grain Substitution{spike_warning}",
            "action": (
                f"Grocery spend is ₹{groc_val:,.0f}/month. "
                "Actions: (1) Buy seasonal local greens instead of off-season items during monsoon vegetable spikes, "
                "(2) Purchase monthly staples (atta, dal, rice, cooking oil) in 10-25 kg wholesale bags from wholesale markets/D-Mart, "
                "(3) Substitute expensive pulses during crop supply deficits."
            ),
            "difficulty": "Easy"
        })

    # 5. Commute & Fuel Rationalization
    commute_val = ob_map.get("Commute", 0.0)
    if commute_val >= 4000:
        est_commute_save = round(commute_val * 0.20, 0)
        reduction_levers.append({
            "category": "Commute & Fuel",
            "current_spend": commute_val,
            "est_monthly_saving": est_commute_save,
            "title": "Hybrid Commuting & Carpooling",
            "action": (
                f"Transport fuel costs ₹{commute_val:,.0f}/month. "
                "Actions: (1) Switch 2 days a week to Metro or office shared cab pools, "
                "(2) Maintain optimal two-wheeler/car tyre pressure (saves 5-7% on mileage), "
                "(3) Batch errands to avoid single-destination car trips."
            ),
            "difficulty": "Medium"
        })

    # Sort levers strictly by monthly rupee impact descending
    reduction_levers.sort(key=lambda x: x["est_monthly_saving"], reverse=True)
    return reduction_levers
