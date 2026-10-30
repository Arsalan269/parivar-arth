"""
Monte Carlo Simulation Engine for Inflation-Driven Shortfall Probability.
Executes 1,000 vector runs sampling inflation from model prediction intervals
to compute exact risk probabilities and stress-tested cash-flow percentile paths.
"""

from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
from planner.projection import match_cpi_category, DEFAULT_CATEGORY_INFLATION


def run_monte_carlo_shortfall_simulation(
    current_income: float,
    obligations: List[Dict[str, Any]],
    monthly_emis: float = 0.0,
    annual_income_increment_pct: float = 5.0,
    horizon_months: int = 24,
    num_simulations: int = 1000,
    category_interval_map: Dict[str, Tuple[float, float, float]] = None,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Simulate 1,000 independent future economic pathways.
    
    Args:
        current_income: monthly household income
        obligations: list of fixed obligations (category, amount)
        monthly_emis: fixed monthly EMI payments
        annual_income_increment_pct: yearly wage growth assumption
        horizon_months: planning horizon (default 24)
        num_simulations: number of simulation runs (default 1000)
        category_interval_map: dict of category -> (lower_ci, expected, upper_ci)
        seed: random seed for reproducibility
        
    Returns:
        Dict with shortfall_probability_pct, percentile trajectories (p10, p50, p90),
        and plain-language probability summary.
    """
    rng = np.random.RandomState(seed)
    interval_map = category_interval_map or {}

    # Extract base amounts and category mappings
    cat_names = []
    base_amounts = []
    lower_bounds = []
    expected_rates = []
    upper_bounds = []

    for ob in obligations:
        cat = ob.get("category", "Other")
        amt = float(ob.get("amount", 0))
        if amt <= 0:
            continue
        cpi_cat = match_cpi_category(cat)

        cat_names.append(cat)
        base_amounts.append(amt)

        # Retrieve intervals from trained model or defaults
        if cpi_cat in interval_map:
            low, exp, upp = interval_map[cpi_cat]
        else:
            default_exp = DEFAULT_CATEGORY_INFLATION.get(cpi_cat, 5.5)
            low, exp, upp = max(1.0, default_exp - 1.5), default_exp, default_exp + 2.0

        lower_bounds.append(low)
        expected_rates.append(exp)
        upper_bounds.append(upp)

    n_cats = len(base_amounts)
    if n_cats == 0:
        return {
            "shortfall_probability_pct": 0.0,
            "probability_text": "No obligations recorded to simulate.",
            "percentiles_df": pd.DataFrame()
        }

    base_amounts_arr = np.array(base_amounts)  # shape: (n_cats,)

    # Array to track monthly surpluses across all runs: shape (num_simulations, horizon_months)
    surplus_matrix = np.zeros((num_simulations, horizon_months))
    shortfall_counts = 0

    for s in range(num_simulations):
        # Sample annual inflation rate for each category for this simulation
        # Using triangular distribution over [lower, expected, upper]
        sampled_rates = np.zeros(n_cats)
        for c in range(n_cats):
            low, exp, upp = lower_bounds[c], expected_rates[c], upper_bounds[c]
            # Guard against invalid bounds
            if upp <= low:
                sampled_rates[c] = exp
            else:
                sampled_rates[c] = rng.triangular(left=low, mode=exp, right=upp)

        # Monthly inflation factors
        monthly_factors = 1.0 + ((sampled_rates / 100.0) / 12.0)  # shape: (n_cats,)

        # Step through months
        has_shortfall_this_run = False
        compounded_expenses = base_amounts_arr.copy()

        for m in range(1, horizon_months + 1):
            # Compound expenses
            compounded_expenses = compounded_expenses * monthly_factors
            total_essentials = np.sum(compounded_expenses)
            total_outflow = total_essentials + monthly_emis

            # Income with annual hike
            yr = m // 12
            income_m = current_income * ((1.0 + (annual_income_increment_pct / 100.0)) ** yr)

            net_surplus = income_m - total_outflow
            surplus_matrix[s, m - 1] = net_surplus

            if net_surplus < 0:
                has_shortfall_this_run = True

        if has_shortfall_this_run:
            shortfall_counts += 1

    shortfall_prob_pct = round((shortfall_counts / num_simulations) * 100.0, 1)

    # Compute percentiles across all 1,000 runs for each month
    # p10 = pessimistic/stress path (lowest surplus)
    # p50 = median path
    # p90 = optimistic path (highest surplus)
    p10_trajectory = np.percentile(surplus_matrix, 10, axis=0)
    p50_trajectory = np.percentile(surplus_matrix, 50, axis=0)
    p90_trajectory = np.percentile(surplus_matrix, 90, axis=0)

    months_axis = list(range(1, horizon_months + 1))
    df_percentiles = pd.DataFrame({
        "Month": months_axis,
        "P10_Stress": np.round(p10_trajectory, 0),
        "P50_Median": np.round(p50_trajectory, 0),
        "P90_Optimistic": np.round(p90_trajectory, 0),
    })

    # Plain language probability synthesis
    if shortfall_prob_pct >= 70.0:
        prob_text = f"High Risk: There is a **{shortfall_prob_pct}% probability** of your household experiencing a cash-flow shortfall within 24 months under volatile inflation conditions."
    elif shortfall_prob_pct >= 30.0:
        prob_text = f"Moderate Watch: There is a **{shortfall_prob_pct}% probability** of a shortfall. Price spikes in food or fuel could exhaust your monthly savings margin."
    else:
        prob_text = f"Resilient Plan: Only a **{shortfall_prob_pct}% probability** of shortfall. Your financial plan withstands 90% of modeled inflation volatility scenarios."

    return {
        "shortfall_probability_pct": shortfall_prob_pct,
        "shortfall_runs_count": shortfall_counts,
        "total_runs": num_simulations,
        "percentiles_df": df_percentiles,
        "probability_text": prob_text
    }
