"""
User Guide, Interactive Glossary & 1-Click Demo Loader for Parivar Arth.
Includes:
1. Step-by-step workflow guide
2. Comprehensive Indian personal finance glossary
3. 'Load Sample Family' demo loader for instant evaluation
4. System limitations and statutory disclaimers
"""

import os
import sys
import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import get_db_session
from core.models import User, Profile, FamilyMember, IncomeSource, FixedObligation, Loan, Asset
from core.security import touch_session, get_current_user_id
from core.profile_service import save_initial_onboarding
from app.styles import apply_theme, render_header, render_footer, PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY


def seed_demo_household(user_id: int, archetype: str):
    """Seed one of three realistic synthetic Indian households."""
    with get_db_session() as db:
        # Clear existing personal data for this user
        db.query(FixedObligation).filter(FixedObligation.user_id == user_id).delete()
        db.query(IncomeSource).filter(IncomeSource.user_id == user_id).delete()
        db.query(FamilyMember).filter(FamilyMember.user_id == user_id).delete()
        db.query(Loan).filter(Loan.user_id == user_id).delete()
        db.query(Asset).filter(Asset.user_id == user_id).delete()
        db.commit()

        if archetype == "sharma":
            # Salaried couple with 2 children and home loan in Metro
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
                {"type": "EPF / Mutual Funds", "amount": 850000.0, "is_liquid": False}
            ]
            help_data = [{"role": "Maid & Cook", "monthly_cost": 5000.0}]
            save_initial_onboarding(db, user_id, "Maharashtra", "Metro (Tier-1)", 4, members, incomes, obligations, loans, assets, help_data)

        elif archetype == "patel":
            # Single earner supporting elderly parents with high medical costs
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
            save_initial_onboarding(db, user_id, "Gujarat", "Tier-2 / Tier-3 City", 3, members, incomes, obligations, loans, assets, [])

        elif archetype == "verma":
            # Gig worker with variable income renting in metro
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
                {"type": "UPI Digital Wallet / Bank", "amount": 28000.0, "is_liquid": True}
            ]
            save_initial_onboarding(db, user_id, "Delhi (NCR)", "Metro (Tier-1)", 1, members, incomes, obligations, loans, assets, [])


def show_user_guide_page():
    st.set_page_config(page_title="User Guide & Glossary - Parivar Arth", page_icon="📖", layout="centered")
    apply_theme()
    touch_session()

    user_id = get_current_user_id()

    render_header(
        title="User Guide & Financial Glossary",
        subtitle="Learn how to navigate Parivar Arth and test with sample family profiles",
        icon="📖"
    )

    tab_demo, tab_guide, tab_glossary, tab_disclaimer = st.tabs([
        "🚀 1-Click Demo Profiles",
        "🗺️ How to Use Parivar Arth",
        "📚 Indian Financial Glossary",
        "⚖️ Limitations & Disclaimers"
    ])

    # ---------------- TAB 1: DEMO PROFILES ----------------
    with tab_demo:
        st.markdown("#### Test Platform with Realistic Pre-Configured Families")
        st.caption("Load a synthetic Indian household archetype to explore all features instantly:")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                """
                **1. The Sharma Family (Metro)**  
                • Dual Salaried (₹1.5 Lakh/mo)  
                • 2 School Children (High fees)  
                • ₹38L Floating Home Loan  
                • ₹4.5L Liquid Savings  
                """
            )
            if user_id and st.button("Load Sharma Family", use_container_width=True, type="primary"):
                seed_demo_household(user_id, "sharma")
                st.success("Loaded Sharma Family! Visit 'Future Shortfall Predictor' to see their plan.")
                st.rerun()

        with col2:
            st.markdown(
                """
                **2. The Patel Household (Tier-2)**  
                • Single Earner (₹68K/mo)  
                • Elderly Parents with Chronic Illness  
                • High Medical Outgo (₹9.5K/mo)  
                • Vulnerable Emergency Runway  
                """
            )
            if user_id and st.button("Load Patel Household", use_container_width=True):
                seed_demo_household(user_id, "patel")
                st.success("Loaded Patel Household! Check 'Loans & Emergency Fund' to view their buffer.")
                st.rerun()

        with col3:
            st.markdown(
                """
                **3. The Verma Household (Gig Worker)**  
                • Single Earner with Variable Income  
                • Freelance / Deliveries (₹42K/mo)  
                • Renting in Delhi NCR  
                • Thin Margin for Inflation Shocks  
                """
            )
            if user_id and st.button("Load Verma Household", use_container_width=True):
                seed_demo_household(user_id, "verma")
                st.success("Loaded Verma Household! Check 'Monthly Tracker' and 'Monte Carlo'.")
                st.rerun()

    # ---------------- TAB 2: STEP GUIDE ----------------
    with tab_guide:
        st.markdown("#### 5-Step Workflow for Family Money Clarity")

        st.markdown(
            """
            1. **Step 1: Set Up Your Household Profile (`My Household Profile`)**  
               Enter your earners, dependent children, elderly parents, housing rent/EMI, and grocery estimates. Profile modifications are automatically versioned to protect your past records.
            
            2. **Step 2: Inspect Machine Learning Inflation Forecasts (`Inflation Trends`)**  
               Explore 24-month forecasts for Food, Education, Health, and Fuel with 80% prediction interval bands and plain-language economic explanations.
            
            3. **Step 3: Track Monthly Spending & Check Overspending (`Monthly Tracker`)**  
               Log daily variable expenses. Our personal z-score monitor will alert you if your spending in any category surges significantly above your own family's history.
            
            4. **Step 4: Check Your Shortfall Month & Monte Carlo Risk (`Future Planner`)**  
               See whether your salary increment outpaces inflation or if you face a shortfall. Run 1,000 Monte Carlo paths to determine your exact shortfall probability.
            
            5. **Step 5: Adopt High-Rupee Reduction Levers & Sinking Funds (`Reduce Expenses` & `Calendar`)**  
               Convert heavy school admission fees into smoothed monthly sinking funds and adopt practical reduction levers (like home loan refinancing) to reclaim monthly cash flow.
            """
        )

    # ---------------- TAB 3: GLOSSARY ----------------
    with tab_glossary:
        st.markdown("#### Indian Personal Finance & Data Science Glossary")

        glossary_items = [
            ("CPI (Consumer Price Index)", "A measure of the average change over time in the prices paid by urban and rural consumers for a basket of goods and services (Base 2012=100 published by MoSPI)."),
            ("WPI (Wholesale Price Index)", "Tracks price movements of goods at the wholesale/producer stage before reaching retail stores (published by Office of the Economic Adviser)."),
            ("Sinking Fund", "A designated monthly savings pool created to gradually accumulate the funds needed to pay a known future lump-sum expense (e.g. school annual fees, car insurance)."),
            ("Debt-to-Income (DTI) Ratio", "The percentage of your monthly gross/net income dedicated to paying debt obligations. Indian financial guidelines advise keeping DTI below 30-40%."),
            ("Emergency Fund Runway", "The number of months your household can continue paying essential living costs using only strictly liquid cash/bank deposits if all income ceases."),
            ("Monte Carlo Simulation", "A computational statistical algorithm that simulates 1,000 potential future pathways by repeatedly sampling variables (inflation, food spikes) from mathematical probability distributions."),
            ("Base Effect", "The distortion in a monthly inflation figure caused by unusually high or low price levels during the corresponding base month of the previous year."),
            ("Z-Score Anomaly", "A statistical measure indicating how many standard deviations an observation differs from the historical mean. Used to detect personal overspending spikes.")
        ]

        for term, definition in glossary_items:
            with st.expander(f"📌 {term}"):
                st.write(definition)

    # ---------------- TAB 4: DISCLAIMER ----------------
    with tab_disclaimer:
        st.markdown("#### System Assumptions & Statutory Limitations")
        st.markdown(
            """
            - **Educational Planning Tool**: Parivar Arth is built strictly as a personal finance budgeting and econometric forecasting simulator. It does **not** provide SEBI-registered investment advisory services, tax filing services, or clinical healthcare diagnosis.
            - **Forecast Uncertainty**: All category inflation rates are probabilistic estimates produced by time-series models (XGBoost, Random Forest, SARIMA) evaluated on historical data. External geopolitical events, natural calamities, or policy interventions can alter actual economic outcomes.
            - **Privacy and Multi-Tenancy**: Financial profiles are strictly partitioned per authenticated session. We never transmit individual raw transaction records to third-party commercial marketing platforms.
            """
        )

    render_footer()


if __name__ == "__main__":
    show_user_guide_page()
