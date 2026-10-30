"""
Seed Script for Parivar Arth.
Initializes:
1. System Administrator account (admin@parivararth.in / AdminMasterPass999)
2. Three realistic synthetic Indian households:
   - Salaried couple with 2 kids and home loan (Sharma Family)
   - Single earner supporting elderly parents with chronic medical needs (Patel Household)
   - Gig worker with variable income (Verma Household)
3. Historical tracker expenses for anomaly detection demonstration
"""

import os
import sys
from datetime import date, timedelta

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import init_db, get_db_session
from core.models import User, Expense, Forecast
from core.auth import register_user
from core.profile_service import save_initial_onboarding
from core.expense_service import add_expense
from ml.pipeline import build_unified_dataset
from ml.train import train_all_categories
from ml.forecast import generate_multi_period_forecasts, save_forecasts_to_db


def seed_database():
    print("==================================================")
    print(" PARIVAR ARTH - DATABASE SEEDING ENGINE ")
    print("==================================================")
    init_db()

    with get_db_session() as db:
        # 1. Admin Account
        admin = db.query(User).filter(User.email == "admin@parivararth.in").first()
        if not admin:
            admin, _ = register_user(
                db=db,
                name="System Administrator",
                email="admin@parivararth.in",
                password="AdminMasterPass999",
                role="admin"
            )
            print(" -> Created Admin user: admin@parivararth.in (password: AdminMasterPass999)")
        else:
            print(" -> Admin user already exists.")

        # 2. Household 1: The Sharma Family (Salaried couple, 2 kids, home loan, Metro)
        sharma = db.query(User).filter(User.email == "aarav@sharma.in").first()
        if not sharma:
            sharma, _ = register_user(
                db=db,
                name="Rajesh Sharma",
                email="aarav@sharma.in",
                password="SharmaFamily123",
                role="user"
            )
            members = [
                {"name": "Rajesh Sharma", "relation": "Self", "age": 38},
                {"name": "Pooja Sharma", "relation": "Spouse", "age": 36},
                {"name": "Aarav Sharma", "relation": "Child", "age": 9},
                {"name": "Ananya Sharma", "relation": "Child", "age": 6}
            ]
            incomes = [
                {"earner_name": "Rajesh Sharma", "source_type": "Primary Salary", "amount": 95000.0, "is_variable": False},
                {"earner_name": "Pooja Sharma", "source_type": "Secondary Salary", "amount": 55000.0, "is_variable": False}
            ]
            obligations = [
                {"category": "Rent/EMI", "amount": 34000.0, "frequency": "Monthly"},
                {"category": "Groceries", "amount": 18000.0, "frequency": "Monthly"},
                {"category": "Utilities", "amount": 5500.0, "frequency": "Monthly"},
                {"category": "Child Education", "amount": 14000.0, "frequency": "Monthly"},
                {"category": "Commute", "amount": 6000.0, "frequency": "Monthly"},
            ]
            loans = [
                {"loan_type": "Home Loan", "balance": 3800000.0, "interest_rate": 8.5, "emi": 33000.0, "remaining_months": 210, "rate_type": "Floating"}
            ]
            assets = [
                {"type": "Savings Account & FDs", "amount": 450000.0, "is_liquid": True},
                {"type": "EPF & Mutual Funds", "amount": 850000.0, "is_liquid": False}
            ]
            help_data = [{"role": "Maid & Cook", "monthly_cost": 5000.0}]
            save_initial_onboarding(db, sharma.user_id, "Maharashtra", "Metro (Tier-1)", 4, members, incomes, obligations, loans, assets, help_data)

            # Seed variable expense history for anomaly detection
            today = date.today()
            # 2 past months of normal dining out (avg ~₹4,000)
            add_expense(db, sharma.user_id, today - timedelta(days=60), "Dining Out", 3800.0, "Family dinner")
            add_expense(db, sharma.user_id, today - timedelta(days=35), "Dining Out", 4200.0, "Weekend restaurant")
            # Current month surge (₹14,000 -> triggers z-score alert)
            add_expense(db, sharma.user_id, today - timedelta(days=5), "Dining Out", 14000.0, "Birthday celebration party")
            print(" -> Created Sharma Family: aarav@sharma.in (password: SharmaFamily123)")

        # 3. Household 2: The Patel Household (Single earner, elderly parents with chronic medical needs)
        patel = db.query(User).filter(User.email == "ketan@patel.in").first()
        if not patel:
            patel, _ = register_user(
                db=db,
                name="Ketan Patel",
                email="ketan@patel.in",
                password="PatelFamily123",
                role="user"
            )
            members = [
                {"name": "Ketan Patel", "relation": "Self", "age": 34},
                {"name": "Ramesh Patel", "relation": "Parent", "age": 68, "has_chronic_condition": True},
                {"name": "Geeta Patel", "relation": "Parent", "age": 64, "has_chronic_condition": True}
            ]
            incomes = [
                {"earner_name": "Ketan Patel", "source_type": "Salary", "amount": 68000.0, "is_variable": False}
            ]
            obligations = [
                {"category": "Rent/EMI", "amount": 16000.0, "frequency": "Monthly"},
                {"category": "Groceries", "amount": 13000.0, "frequency": "Monthly"},
                {"category": "Utilities", "amount": 4000.0, "frequency": "Monthly"},
                {"category": "Parent Medical", "amount": 9500.0, "frequency": "Monthly"},
                {"category": "Commute", "amount": 3500.0, "frequency": "Monthly"},
            ]
            loans = [
                {"loan_type": "Personal Loan (Medical)", "balance": 180000.0, "interest_rate": 13.5, "emi": 6200.0, "remaining_months": 28, "rate_type": "Fixed"}
            ]
            assets = [
                {"type": "Savings Account", "amount": 85000.0, "is_liquid": True}
            ]
            save_initial_onboarding(db, patel.user_id, "Gujarat", "Tier-2 / Tier-3 City", 3, members, incomes, obligations, loans, assets, [])
            print(" -> Created Patel Household: ketan@patel.in (password: PatelFamily123)")

        # 4. Household 3: The Verma Household (Gig worker with variable income)
        verma = db.query(User).filter(User.email == "amit@verma.in").first()
        if not verma:
            verma, _ = register_user(
                db=db,
                name="Amit Verma",
                email="amit@verma.in",
                password="VermaFamily123",
                role="user"
            )
            members = [
                {"name": "Amit Verma", "relation": "Self", "age": 28}
            ]
            incomes = [
                {"earner_name": "Amit Verma", "source_type": "Freelance / Gig Deliveries", "amount": 42000.0, "is_variable": True}
            ]
            obligations = [
                {"category": "Rent/EMI", "amount": 12000.0, "frequency": "Monthly"},
                {"category": "Groceries", "amount": 8500.0, "frequency": "Monthly"},
                {"category": "Utilities", "amount": 2500.0, "frequency": "Monthly"},
                {"category": "Commute", "amount": 4500.0, "frequency": "Monthly"},
            ]
            loans = [
                {"loan_type": "Two-Wheeler Loan", "balance": 45000.0, "interest_rate": 12.0, "emi": 2400.0, "remaining_months": 18, "rate_type": "Fixed"}
            ]
            assets = [
                {"type": "UPI Wallet / Bank", "amount": 28000.0, "is_liquid": True}
            ]
            save_initial_onboarding(db, verma.user_id, "Delhi (NCR)", "Metro (Tier-1)", 1, members, incomes, obligations, loans, assets, [])
            print(" -> Created Verma Household: amit@verma.in (password: VermaFamily123)")

        # Check if forecasts exist
        fc_count = db.query(Forecast).count()
        if fc_count == 0:
            print("\n -> No forecasts found in database. Running ML training pipeline...")
            df_pipe, meta = build_unified_dataset()
            train_res = train_all_categories(df_pipe)
            forecasts = generate_multi_period_forecasts(train_res, df_pipe, horizon_months=24)
            save_forecasts_to_db(forecasts)
        else:
            print(f" -> {fc_count} active forecast records present in database.")

    print("\n[SUCCESS] Seeding Complete! All 3 synthetic households & Admin user ready.\n")


if __name__ == "__main__":
    seed_database()
