"""
Unit Tests for Planner Core Calculations:
- Debt-to-Income (DTI) and Floating Rate Repo Shock
- Sinking Funds with Category-Specific Compounding
- Emergency Fund Runway with Strict Liquidity Filtering
- Overspending Anomaly Detection via Personal z-Scores
"""

from datetime import date
import pytest
import numpy as np

from planner.loans import calculate_dti, compute_standard_emi, simulate_floating_repo_shock, rank_debt_prepayments
from planner.emergency import determine_emergency_fund_target_months, calculate_liquid_emergency_fund
from planner.sinking_funds import compute_sinking_funds, generate_12_month_cashflow_matrix
from core.expense_service import compute_needs_wants_savings_split, auto_categorize_description


def test_dti_calculation_and_thresholds():
    """Verify DTI formula and Indian risk boundaries."""
    # Safe boundary: 25% DTI
    dti, status, _ = calculate_dti(monthly_emis=25000.0, monthly_income=100000.0)
    assert dti == 25.0
    assert status == "Safe"

    # Watch boundary: 38% DTI
    dti, status, _ = calculate_dti(monthly_emis=38000.0, monthly_income=100000.0)
    assert dti == 38.0
    assert status == "Watch"

    # At Risk boundary: 52% DTI
    dti, status, _ = calculate_dti(monthly_emis=52000.0, monthly_income=100000.0)
    assert dti == 52.0
    assert status == "At Risk"


def test_floating_loan_repo_shock_arithmetic():
    """
    Hand-verified calculation:
    Home Loan: Principal = ₹40,00,000, 8.5% p.a., 240 months (20 years)
    Current EMI = 4000000 * (0.085/12) * (1 + 0.085/12)^240 / ((1 + 0.085/12)^240 - 1)
    = ₹34,713.06
    When Repo hikes by 50 bps (+0.50%):
    New Rate = 9.0% p.a.
    New EMI = 4000000 * (0.09/12) * (1 + 0.09/12)^240 / ((1 + 0.09/12)^240 - 1)
    = ₹35,989.04
    Increase = ₹1,275.98 (~₹1,276)
    """
    principal = 4000000.0
    rate = 8.5
    tenure = 240

    old_emi = compute_standard_emi(principal, rate, tenure)
    assert old_emi == pytest.approx(34713.06, abs=1.0)

    shock = simulate_floating_repo_shock(
        principal_balance=principal,
        current_annual_rate=rate,
        remaining_months=tenure,
        repo_change_bps=50.0
    )

    assert shock["new_rate"] == 9.0
    assert shock["new_emi"] == pytest.approx(35989.04, abs=1.0)
    assert shock["emi_increase"] == pytest.approx(1275.98, abs=1.0)
    assert shock["tenure_extension_months"] > 0


def test_emergency_fund_target_and_liquid_filter():
    """Verify dynamic 3 vs 6 month target and strict liquidity exclusion."""
    # Dual earner stable -> 3 months
    target_months, _ = determine_emergency_fund_target_months(
        is_single_earner=False,
        has_variable_income=False,
        has_chronic_dependents=False
    )
    assert target_months == 3

    # Single earner with variable income -> 6 months
    target_months, _ = determine_emergency_fund_target_months(
        is_single_earner=True,
        has_variable_income=True,
        has_chronic_dependents=False
    )
    assert target_months == 6

    # Verify liquidity filtering
    assets = [
        {"type": "Savings Account", "amount": 100000.0, "is_liquid": True},
        {"type": "Bank Fixed Deposit", "amount": 200000.0, "is_liquid": True},
        {"type": "Physical Gold Jewellery", "amount": 500000.0, "is_liquid": False},
        {"type": "Plot of Land / Real Estate", "amount": 2500000.0, "is_liquid": False}
    ]
    monthly_essentials = 60000.0

    ef = calculate_liquid_emergency_fund(assets, monthly_essentials, target_months=6)

    # Only 1L + 2L = 3L should be counted as liquid
    assert ef["total_liquid"] == 300000.0
    assert ef["illiquid_total"] == 3000000.0
    assert ef["runway_months"] == 5.0  # 3,00,000 / 60,000 = 5.0 months
    assert ef["status"] == "Watch"  # 5.0 < target 6.0


def test_sinking_fund_calculation_with_inflation():
    """
    Hand-verified calculation:
    Annual School Admission Fees = ₹60,000 due in April.
    Category Forecast Inflation (Education) = 8.0%.
    Inflated Due Amount = 60,000 * 1.08 = ₹64,800.
    Monthly Sinking Reserve = ₹64,800 / 12 = ₹5,400.
    """
    recurring = [{
        "name": "School Admission Fees",
        "amount": 60000.0,
        "frequency": "Annual",
        "due_month": 4,
        "category": "Education"
    }]
    inf_map = {"Education": 8.0}

    sinking = compute_sinking_funds(recurring, current_month=4, category_inflation_map=inf_map)

    assert len(sinking) == 1
    assert sinking[0]["inflated_due_amount"] == 64800.0
    assert sinking[0]["smoothed_monthly_reserve"] == 5400.0


def test_needs_wants_savings_split():
    """Verify Needs/Wants/Savings distribution on Indian expenditure baskets."""
    income = 100000.0
    fixed_needs = 45000.0  # Rent + Groceries + Bills

    # Mock expenses
    class MockExp:
        def __init__(self, category, amount):
            self.category = category
            self.amount = amount

    var_expenses = [
        MockExp("Groceries", 15000.0),      # Needs
        MockExp("Dining Out", 8000.0),      # Wants
        MockExp("Shopping", 7000.0),        # Wants
        MockExp("Commute", 5000.0)          # Needs
    ]

    split = compute_needs_wants_savings_split(income, fixed_needs, var_expenses)

    # Needs = 45000 + 15000 + 5000 = 65000 (65%)
    # Wants = 8000 + 7000 = 15000 (15%)
    # Savings = 100000 - (65000 + 15000) = 20000 (20%)
    assert split["needs_amount"] == 65000.0
    assert split["wants_amount"] == 15000.0
    assert split["savings_amount"] == 20000.0
    assert split["needs_pct"] == 65.0
    assert split["wants_pct"] == 15.0
    assert split["savings_pct"] == 20.0
    assert split["is_high_needs"] is True


def test_merchant_auto_categorization():
    """Verify rule-based Indian merchant string classification."""
    assert auto_categorize_description("UPI-SWIGGY-BANGALORE") == "Dining Out"
    assert auto_categorize_description("POS DMART MUMBAI") == "Groceries"
    assert auto_categorize_description("HPCL PETROL PUMP PUNE") == "Commute"
    assert auto_categorize_description("APOLLO PHARMACY HYD") == "Health"
    assert auto_categorize_description("NETFLIX ENTERTAINMENT IN") == "Entertainment"
    assert auto_categorize_description("MYNTRA FASHION DEL") == "Shopping"
