"""
Hand-Verified Arithmetic Unit Tests for Parivar Arth.
Includes step-by-step worked mathematical proofs for:
1. Category-specific compound inflation projection
2. Annual sinking fund smoothing allocation
3. Exact shortfall month detection and cash-flow gap equation
"""

import pytest
import numpy as np

from planner.projection import project_expense_item
from planner.sinking_funds import compute_sinking_funds
from planner.shortfall import compute_shortfall_timeline
from planner.montecarlo import run_monte_carlo_shortfall_simulation


def test_hand_verified_case_1_inflation_compounding():
    """
    CASE 1: Hand-Calculated Inflation Compounding
    ---------------------------------------------
    Base monthly groceries: ₹20,000
    Annual food inflation: 6.0% p.a.
    Monthly rate r = 0.06 / 12 = 0.005 (0.5% per month)
    
    Worked Arithmetic:
    Month 1: 20,000 * (1.005)^1 = ₹20,100.00
    Month 2: 20,000 * (1.005)^2 = ₹20,200.50
    Month 3: 20,000 * (1.005)^3 = ₹20,301.50
    Month 6: 20,000 * (1.005)^6 = 20,000 * 1.0303775 = ₹20,607.55 (~₹20,608)
    """
    base_cost = 20000.0
    category = "Food and Beverages"
    annual_rate = 6.0

    # Month 1
    cost_m1 = project_expense_item(base_cost, category, months_ahead=1, annual_rate_override=annual_rate)
    assert cost_m1 == pytest.approx(20100.00, abs=0.5)

    # Month 6
    cost_m6 = project_expense_item(base_cost, category, months_ahead=6, annual_rate_override=annual_rate)
    assert cost_m6 == pytest.approx(20607.55, abs=1.0)


def test_hand_verified_case_2_sinking_fund_reserve():
    """
    CASE 2: Hand-Calculated Sinking Fund Reserve
    --------------------------------------------
    Annual Term Life Insurance: ₹24,000 base due in 10 months
    Category Forecast Inflation (Health): 0.0% (for pure hand validation check)
    
    Worked Arithmetic:
    Due amount = ₹24,000
    Months remaining = 10
    Monthly catch-up allocation = ₹24,000 / 10 = ₹2,400.00 / month
    Smoothed 12-month allocation = ₹24,000 / 12 = ₹2,000.00 / month
    """
    recurring = [{
        "name": "Term Life Insurance",
        "amount": 24000.0,
        "frequency": "Annual",
        "due_month": 11,
        "category": "Health"
    }]
    # Current month = 1 (Jan), due in month 11 (Nov) -> 10 months left
    sinking = compute_sinking_funds(recurring, current_month=1, category_inflation_map={"Health": 0.0})

    assert len(sinking) == 1
    assert sinking[0]["months_left"] == 10
    assert sinking[0]["catch_up_monthly_reserve"] == 2400.00
    assert sinking[0]["smoothed_monthly_reserve"] == 2000.00


def test_hand_verified_case_3_exact_shortfall_month():
    """
    CASE 3: Exact Month of Shortfall Verification
    ----------------------------------------------
    Fixed take-home salary: ₹60,000/month (0% annual increment)
    Current essential outflows: ₹56,000/month
    Uniform monthly inflation: 0.5% per month (6.0% p.a.)
    
    Worked Arithmetic:
    Outflow(m) = 56,000 * (1.005)^m
    Month 1:  56,000 * (1.005)^1  = ₹56,280.00  (Surplus: +₹3,720.00)
    Month 6:  56,000 * (1.005)^6  = ₹57,701.14  (Surplus: +₹2,298.86)
    Month 12: 56,000 * (1.005)^12 = ₹59,453.64  (Surplus: +₹546.36)
    Month 13: 56,000 * (1.005)^13 = ₹59,750.91  (Surplus: +₹249.09)
    Month 14: 56,000 * (1.005)^14 = ₹60,049.66  (Surplus: -₹49.66 -> SHORTFALL!)
    
    Shortfall Month MUST strictly equal 14.
    """
    income = 60000.0
    obligations = [{"category": "Miscellaneous Services", "amount": 56000.0}]

    # Force 6% inflation map across categories
    flat_inf_map = {"Miscellaneous Services": [6.0] * 24}

    res = compute_shortfall_timeline(
        current_monthly_income=income,
        obligations=obligations,
        monthly_emis=0.0,
        annual_income_increment_pct=0.0,
        min_savings_target_pct=0.0,  # test pure zero-line crossing
        horizon_months=24,
        category_forecast_map=flat_inf_map
    )

    assert res["shortfall_month"] == 14
    df_t = res["timeline_df"]
    # Month 13 surplus is positive
    assert float(df_t.loc[df_t["Month"] == 13, "Net_Surplus"].iloc[0]) > 0
    # Month 14 surplus turns negative
    assert float(df_t.loc[df_t["Month"] == 14, "Net_Surplus"].iloc[0]) < 0


def test_monte_carlo_probability_bounds():
    """Verify Monte Carlo simulation bounds between 0% and 100%."""
    income = 80000.0
    obligations = [
        {"category": "Groceries", "amount": 25000.0},
        {"category": "Rent/EMI", "amount": 30000.0}
    ]
    mc = run_monte_carlo_shortfall_simulation(
        current_income=income,
        obligations=obligations,
        monthly_emis=10000.0,
        annual_income_increment_pct=5.0,
        num_simulations=200,  # fast test run
        seed=123
    )

    assert 0.0 <= mc["shortfall_probability_pct"] <= 100.0
    assert not mc["percentiles_df"].empty
    # Stress (P10) surplus must be <= Optimistic (P90) surplus
    p10_final = mc["percentiles_df"]["P10_Stress"].iloc[-1]
    p90_final = mc["percentiles_df"]["P90_Optimistic"].iloc[-1]
    assert p10_final <= p90_final
