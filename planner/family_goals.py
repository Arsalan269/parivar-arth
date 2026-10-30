"""
Family Planning & Milestone Projection Engine for Parivar Arth.
Includes:
1. Children's Education Milestones (Class 10, Class 12, Higher Ed) with education inflation compounding
2. Parents' Medical Health Provisions, age-based risk factors, and insurance gap checking
3. Custom Goals Calculator (Home Downpayment, Vehicle, Marriage, Vacation)
"""

from datetime import date
from typing import List, Dict, Any, Tuple
import numpy as np


def compute_education_milestones(
    child_name: str,
    current_age: int,
    current_annual_cost: float,
    education_inflation_rate: float = 7.5
) -> List[Dict[str, Any]]:
    """
    Compute inflation-adjusted milestone costs for Indian children:
    - Milestone 1: High School Boards (Age 15, Class 10)
    - Milestone 2: Senior Secondary & Entrance Coaching (Age 17, Class 12)
    - Milestone 3: Undergraduate Degree (Age 18 - 21)
    - Milestone 4: Post-Graduate Degree / Specialization (Age 22 - 24)
    """
    milestones = [
        {"milestone": "Class 10 Board & Secondary", "target_age": 15, "cost_multiplier": 1.5},
        {"milestone": "Class 12 & Competitive Coaching (JEE/NEET/CLAT)", "target_age": 17, "cost_multiplier": 2.5},
        {"milestone": "4-Year Undergrad Degree (B.Tech / B.Com / MBBS)", "target_age": 18, "cost_multiplier": 6.0},
        {"milestone": "Postgraduate Degree / MBA / Overseas Study", "target_age": 22, "cost_multiplier": 10.0},
    ]

    results = []
    inf_factor = 1.0 + (education_inflation_rate / 100.0)

    for m in milestones:
        t_age = m["target_age"]
        years_left = max(1, t_age - current_age)
        months_left = years_left * 12

        # Future projected cost in Rupees
        base_milestone_cost = current_annual_cost * m["cost_multiplier"]
        inflated_cost = round(base_milestone_cost * (inf_factor ** years_left), 0)

        # Monthly SIP needed (assuming conservative 9% investment growth)
        r_inv = (0.09 / 12.0)
        # Future value factor: FV = PMT * [((1 + r)^n - 1) / r]
        # PMT = FV * r / ((1 + r)^n - 1)
        fv_factor = (((1.0 + r_inv) ** months_left) - 1.0) / r_inv
        monthly_saving_needed = round(inflated_cost / fv_factor, 0)

        results.append({
            "child_name": child_name,
            "milestone": m["milestone"],
            "target_age": t_age,
            "years_away": years_left,
            "inflated_cost": inflated_cost,
            "education_inflation_applied": education_inflation_rate,
            "monthly_investment_needed": monthly_saving_needed
        })

    return results


def evaluate_parent_medical_provision(
    parent_name: str,
    age: int,
    current_monthly_meds: float,
    has_chronic_condition: bool,
    has_health_insurance: bool,
    medical_inflation_rate: float = 7.0
) -> Dict[str, Any]:
    """
    Evaluate elderly healthcare risk and required buffers.
    Incorporates medical inflation, age risk escalation, and insurance gap checking.
    """
    # Age factor: healthcare costs escalate non-linearly with age in India
    if age >= 75:
        age_multiplier = 1.6
    elif age >= 65:
        age_multiplier = 1.3
    else:
        age_multiplier = 1.1

    if has_chronic_condition:
        age_multiplier += 0.3

    adjusted_monthly_cost = round(current_monthly_meds * age_multiplier, 0)
    
    # 5-Year forward medical cost projection
    five_year_projected = round(adjusted_monthly_cost * ((1.0 + (medical_inflation_rate / 100.0)) ** 5), 0)

    # Emergency medical buffer recommendation (e.g. ₹2,00,000 to ₹5,00,000 dedicated reserve)
    recommended_buffer = 400000.0 if has_chronic_condition else 250000.0

    # Insurance gap warning
    insurance_gap = not has_health_insurance
    if insurance_gap:
        advice = (
            f"High Priority Gap: {parent_name} (age {age}) lacks independent health insurance. "
            f"A single hospitalization in Tier-1/2 private hospitals can cost ₹2,00,000–₹5,00,000. "
            "Explore senior citizen health insurance or establish a dedicated medical emergency sinking fund immediately."
        )
    else:
        advice = (
            f"Good Coverage: {parent_name} is covered by health insurance. "
            f"Maintain an out-of-pocket buffer of ₹{recommended_buffer:,.0f} for non-covered pharmacy bills and consumables."
        )

    return {
        "parent_name": parent_name,
        "age": age,
        "current_monthly": current_monthly_meds,
        "risk_adjusted_monthly": adjusted_monthly_cost,
        "five_year_projected_monthly": five_year_projected,
        "recommended_buffer": recommended_buffer,
        "has_insurance": has_health_insurance,
        "has_insurance_gap": insurance_gap,
        "advice": advice
    }


def compute_goal_feasibility(
    goal_name: str,
    target_amount: float,
    target_years: float,
    general_inflation_rate: float = 6.0,
    expected_return_rate: float = 10.0
) -> Dict[str, Any]:
    """Calculate inflation-adjusted goal target and required monthly SIP."""
    months = int(target_years * 12)
    if months <= 0:
        months = 1

    # Future value adjusted for inflation
    inflated_target = round(target_amount * ((1.0 + (general_inflation_rate / 100.0)) ** target_years), 0)

    # Monthly SIP required
    r_inv = (expected_return_rate / 100.0) / 12.0
    fv_factor = (((1.0 + r_inv) ** months) - 1.0) / r_inv
    monthly_sip = round(inflated_target / fv_factor, 0)

    return {
        "goal_name": goal_name,
        "original_target": target_amount,
        "inflated_target": inflated_target,
        "years": target_years,
        "monthly_sip_needed": monthly_sip
    }
