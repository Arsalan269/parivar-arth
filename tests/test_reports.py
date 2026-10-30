"""
Unit tests for Report Generation (PDF & Excel) and Offline Chatbot Agent.
"""

import pytest
from reports.pdf_generator import generate_household_pdf_report
from reports.excel_generator import generate_household_excel_workbook
from chatbot.faq import OfflineFaqMatcher
from chatbot.agent import ParivarChatbotAgent


def test_pdf_report_generation():
    """Verify that PDF generator returns a valid non-empty PDF byte stream."""
    summary = {
        "total_income": 95000.0,
        "fixed_obligations": 42000.0,
        "total_emis": 15000.0,
        "current_surplus": 38000.0,
        "dti": 15.8
    }
    obs = [
        {"category": "Rent/EMI", "frequency": "Monthly", "amount": 25000.0},
        {"category": "Groceries", "frequency": "Monthly", "amount": 12000.0},
        {"category": "Utilities", "frequency": "Monthly", "amount": 5000.0}
    ]
    loans = [
        {"loan_type": "Car Loan", "balance": 350000.0, "interest_rate": 8.9, "emi": 15000.0, "remaining_months": 24, "rate_type": "Fixed"}
    ]
    shortfall = {
        "status": "Safe",
        "explanation": "Healthy surplus comfortably absorbs inflation.",
        "shortfall_month": None,
        "surplus_6m": 36000.0,
        "surplus_12m": 35000.0,
        "surplus_18m": 34000.0,
        "surplus_24m": 33000.0
    }
    emergency = {
        "runway_months": 5.2,
        "target_months": 3,
        "status": "Safe"
    }

    pdf_bytes = generate_household_pdf_report(
        user_name="Aarav Sharma",
        email="aarav@sharma.in",
        status_summary=summary,
        obligations=obs,
        loans=loans,
        shortfall_data=shortfall,
        emergency_data=emergency
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # Standard PDF magic header
    assert pdf_bytes.startswith(b"%PDF-")


def test_excel_workbook_generation():
    """Verify that Excel generator returns a valid non-empty OpenXML byte stream."""
    import pandas as pd
    summary = {
        "total_income": 95000.0,
        "fixed_obligations": 42000.0,
        "total_emis": 15000.0,
        "current_surplus": 38000.0,
        "dti": 15.8
    }
    obs = [{"category": "Rent", "amount": 25000.0}]
    loans = [{"loan_type": "Car Loan", "balance": 350000.0, "interest_rate": 8.9, "emi": 15000.0, "remaining_months": 24, "rate_type": "Fixed"}]
    shortfall = {
        "status": "Safe",
        "shortfall_month": None,
        "surplus_12m": 35000.0,
        "surplus_24m": 33000.0,
        "timeline_df": pd.DataFrame([{"Month": 1, "Projected_Income": 95000.0, "Essential_Expenses": 42000.0, "EMIs": 15000.0, "Total_Outflows": 57000.0, "Net_Surplus": 38000.0, "Is_Shortfall": False}])
    }
    emergency = {"runway_months": 5.0, "target_months": 3, "shortfall": 0.0}

    excel_bytes = generate_household_excel_workbook(
        user_name="Aarav Sharma",
        status_summary=summary,
        obligations=obs,
        loans=loans,
        shortfall_data=shortfall,
        emergency_data=emergency
    )

    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 2000
    # OpenXML zip file signature
    assert excel_bytes.startswith(b"PK\x03\x04")


def test_offline_faq_retrieval():
    """Verify TF-IDF cosine similarity retrieval on core Indian financial concepts."""
    matcher = OfflineFaqMatcher()

    ans, score = matcher.find_best_match("What is a sinking fund?")
    assert ans is not None
    assert "sinking fund" in ans.lower()
    assert score > 0.4

    ans2, score2 = matcher.find_best_match("How is my emergency fund target calculated?")
    assert ans2 is not None
    assert "emergency" in ans2.lower()
    assert score2 > 0.3


def test_chatbot_guardrails_refusal():
    """Verify chatbot refuses out-of-scope stock and medical requests."""
    agent = ParivarChatbotAgent()

    # Stock trading guard
    stock_reply = agent.process_message(user_id=1, user_message="Which multibagger stock should I buy for 10x returns?")
    assert "disclaimer" in stock_reply.lower() or "sebi" in stock_reply.lower()

    # Medical diagnosis guard
    medical_reply = agent.process_message(user_id=1, user_message="Please prescribe medicine for high fever and cough")
    assert "medical" in medical_reply.lower() or "practitioner" in medical_reply.lower()
