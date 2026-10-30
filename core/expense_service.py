"""
Expense Tracker Management, Anomaly Detection & Needs/Wants/Savings Analysis.
"""

from datetime import date, datetime
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from core.models import Expense, AuditLog


# Standard Indian Household Needs vs. Wants Mapping
NEEDS_CATEGORIES = {
    "Groceries", "Food & Groceries", "Rent", "Housing", "Utilities",
    "Electricity & Water", "Child Education", "School Fees",
    "Health", "Parent Medical", "Medicines", "Commute", "Fuel", "EMIs"
}

WANTS_CATEGORIES = {
    "Dining Out", "Shopping", "Entertainment", "Movies", "Subscriptions",
    "Electronics", "Vacation", "Hobbies", "Gifts", "Salon & Personal Care"
}

# Rule-based transaction classifier for bank/statement drops
KEYWORD_CATEGORY_RULES = {
    "swiggy": "Dining Out",
    "zomato": "Dining Out",
    "mcdonald": "Dining Out",
    "dmart": "Groceries",
    "blinkit": "Groceries",
    "zepto": "Groceries",
    "bigbasket": "Groceries",
    "nature basket": "Groceries",
    "supermarket": "Groceries",
    "uber": "Commute",
    "ola": "Commute",
    "fuel": "Commute",
    "petrol": "Commute",
    "hpcl": "Commute",
    "bpcl": "Commute",
    "ioc": "Commute",
    "metro": "Commute",
    "apollo": "Health",
    "pharmacy": "Health",
    "medplus": "Health",
    "netmeds": "Health",
    "1mg": "Health",
    "hospital": "Health",
    "clinic": "Health",
    "school": "Child Education",
    "tuition": "Child Education",
    "college": "Child Education",
    "netflix": "Entertainment",
    "hotstar": "Entertainment",
    "prime": "Entertainment",
    "pvr": "Entertainment",
    "inox": "Entertainment",
    "amazon": "Shopping",
    "flipkart": "Shopping",
    "myntra": "Shopping",
    "zara": "Shopping",
    "electricity": "Utilities",
    "bescom": "Utilities",
    "mahadiscom": "Utilities",
    "torrent": "Utilities",
    "tatapower": "Utilities",
    "lpg": "Utilities",
    "indane": "Utilities",
    "hp gas": "Utilities",
}


def add_expense(
    db: Session,
    user_id: int,
    expense_date: date,
    category: str,
    amount: float,
    note: str = ""
) -> Tuple[bool, str]:
    """Add a new daily/variable expense record."""
    if amount <= 0:
        return False, "Expense amount must be greater than zero."

    exp = Expense(
        user_id=user_id,
        date=expense_date,
        category=category,
        amount=round(float(amount), 2),
        note=note.strip()
    )
    db.add(exp)
    db.commit()
    return True, "Expense recorded successfully."


def delete_expense(db: Session, user_id: int, expense_id: int) -> Tuple[bool, str]:
    """Delete an expense record with strict user_id tenant ownership check."""
    exp = db.query(Expense).filter(Expense.id == expense_id, Expense.user_id == user_id).first()
    if not exp:
        return False, "Expense not found or unauthorized."

    db.delete(exp)
    db.commit()
    return True, "Expense deleted."


def get_user_expenses(
    db: Session,
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Expense]:
    """Fetch tracked expenses within an optional date range."""
    q = db.query(Expense).filter(Expense.user_id == user_id)
    if start_date:
        q = q.filter(Expense.date >= start_date)
    if end_date:
        q = q.filter(Expense.date <= end_date)
    return q.order_by(Expense.date.desc()).all()


def compute_needs_wants_savings_split(
    monthly_income: float,
    fixed_obligations_total: float,
    monthly_expenses: List[Expense]
) -> Dict[str, Any]:
    """
    Calculate the household's actual Needs vs. Wants vs. Savings distribution.
    Compares against the conventional 50/30/20 guideline, highlighting Indian realities (>60% needs).
    """
    needs_spend = fixed_obligations_total
    wants_spend = 0.0

    for exp in monthly_expenses:
        cat = exp.category
        if cat in NEEDS_CATEGORIES or any(n.lower() in cat.lower() for n in ["grocery", "rent", "util", "health", "medic", "edu", "school", "commute", "fuel"]):
            needs_spend += exp.amount
        else:
            wants_spend += exp.amount

    total_outflow = needs_spend + wants_spend
    savings_amount = max(0.0, monthly_income - total_outflow)

    if monthly_income > 0:
        needs_pct = round((needs_spend / monthly_income) * 100.0, 1)
        wants_pct = round((wants_spend / monthly_income) * 100.0, 1)
        savings_pct = round((savings_amount / monthly_income) * 100.0, 1)
    else:
        needs_pct, wants_pct, savings_pct = 0.0, 0.0, 0.0

    return {
        "monthly_income": monthly_income,
        "needs_amount": needs_spend,
        "wants_amount": wants_spend,
        "savings_amount": savings_amount,
        "needs_pct": needs_pct,
        "wants_pct": wants_pct,
        "savings_pct": savings_pct,
        "is_high_needs": needs_pct > 60.0
    }


def detect_overspending_anomalies(
    db: Session,
    user_id: int,
    current_month_date: Optional[date] = None,
    z_threshold: float = 1.8
) -> List[Dict[str, Any]]:
    """
    Detect overspending using z-scores on each family's OWN personal spending history.
    Formula: z = (current_month_spend - historical_mean) / historical_std
    """
    if current_month_date is None:
        current_month_date = date.today()

    curr_year = current_month_date.year
    curr_month = current_month_date.month

    expenses = db.query(Expense).filter(Expense.user_id == user_id).all()
    if not expenses:
        return []

    # Build monthly category aggregates
    records = []
    for exp in expenses:
        records.append({
            "year_month": f"{exp.date.year}-{exp.date.month:02d}",
            "category": exp.category,
            "amount": exp.amount,
            "is_current": (exp.date.year == curr_year and exp.date.month == curr_month)
        })

    df = pd.DataFrame(records)
    if df.empty:
        return []

    # Group by month and category
    monthly_cat = df.groupby(["year_month", "category"])["amount"].sum().reset_index()

    current_ym = f"{curr_year}-{curr_month:02d}"
    anomalies = []

    for cat in monthly_cat["category"].unique():
        cat_data = monthly_cat[monthly_cat["category"] == cat]
        
        # Historical months excluding current
        hist_data = cat_data[cat_data["year_month"] != current_ym]
        curr_row = cat_data[cat_data["year_month"] == current_ym]

        if len(hist_data) >= 2 and not curr_row.empty:
            mean = float(hist_data["amount"].mean())
            std = float(hist_data["amount"].std())
            curr_val = float(curr_row["amount"].iloc[0])

            if std > 0:
                z = (curr_val - mean) / std
                if z >= z_threshold:
                    anomalies.append({
                        "category": cat,
                        "current_amount": curr_val,
                        "historical_mean": round(mean, 0),
                        "z_score": round(z, 2),
                        "surge_pct": round(((curr_val - mean) / mean) * 100.0, 1),
                        "message": (
                            f"Spending on '{cat}' is ₹{curr_val:,.0f} this month—"
                            f"{((curr_val - mean) / mean) * 100.0:.0f}% higher than your family's normal average of ₹{mean:,.0f}."
                        )
                    })

    return anomalies


def auto_categorize_description(description: str) -> str:
    """Classify transaction string based on Indian consumer merchant rules."""
    text = str(description).lower()
    for kw, cat in KEYWORD_CATEGORY_RULES.items():
        if kw in text:
            return cat
    return "Other"
