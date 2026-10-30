"""
Tests for Conditional Mandatory Profile Validation and Versioned Profile Updates.
"""

from datetime import date
import pytest
from core.models import Profile, FamilyMember, IncomeSource, FixedObligation
from core.profile_service import (
    validate_profile_completeness, save_initial_onboarding,
    update_obligation_versioned, update_income_versioned, get_version_history,
    get_household_profile
)


def test_conditional_mandatory_validation():
    """Verify conditional validation rules based on family composition."""
    base_prof = {"state": "Maharashtra", "city_type": "Metro", "household_size": 3}
    base_incomes = [{"amount": 80000}]
    base_obligations = [
        {"category": "Rent/EMI", "amount": 25000},
        {"category": "Groceries", "amount": 12000},
        {"category": "Utilities", "amount": 4000}
    ]

    # Case 1: Simple couple without children or elderly parents -> Valid
    members_couple = [{"name": "Self", "relation": "Self"}, {"name": "Spouse", "relation": "Spouse"}]
    is_valid, errors = validate_profile_completeness(base_prof, members_couple, base_incomes, base_obligations)
    assert is_valid is True
    assert len(errors) == 0

    # Case 2: Child added without education fees -> Must fail
    members_with_child = members_couple + [{"name": "Aarav", "relation": "Child"}]
    is_valid, errors = validate_profile_completeness(base_prof, members_with_child, base_incomes, base_obligations)
    assert is_valid is False
    assert any("education" in err.lower() for err in errors)

    # Case 3: Parent added without medical provision -> Must fail
    members_with_parent = members_couple + [{"name": "Father", "relation": "Parent"}]
    is_valid, errors = validate_profile_completeness(base_prof, members_with_parent, base_incomes, base_obligations)
    assert is_valid is False
    assert any("medical" in err.lower() for err in errors)

    # Case 4: Income missing -> Must fail
    is_valid, errors = validate_profile_completeness(base_prof, members_couple, [], base_obligations)
    assert is_valid is False
    assert any("income" in err.lower() for err in errors)


def test_versioned_obligation_update(test_db, user_a):
    """
    Verify strict financial versioning:
    Modifying rent must NOT overwrite historical row; it closes old row
    with effective_to and inserts new row with effective_from.
    """
    user_id = user_a.user_id
    today = date.today()

    # Step 1: Initial onboarding
    members = [{"name": "Self", "relation": "Self", "age": 35}]
    incomes = [{"earner_name": "Self", "source_type": "Salary", "amount": 90000}]
    obligations = [
        {"category": "Rent/EMI", "amount": 22000, "frequency": "Monthly"},
        {"category": "Groceries", "amount": 15000, "frequency": "Monthly"},
        {"category": "Utilities", "amount": 5000, "frequency": "Monthly"}
    ]

    ok, msg = save_initial_onboarding(
        db=test_db,
        user_id=user_id,
        state="Karnataka",
        city_type="Metro",
        household_size=2,
        members_data=members,
        incomes_data=incomes,
        obligations_data=obligations
    )
    assert ok is True

    # Confirm initial active row
    initial_rent = (
        test_db.query(FixedObligation)
        .filter(FixedObligation.user_id == user_id, FixedObligation.category == "Rent/EMI", FixedObligation.effective_to == None)
        .first()
    )
    assert initial_rent is not None
    assert initial_rent.amount == 22000
    assert initial_rent.effective_from == today
    assert initial_rent.effective_to is None

    # Step 2: Rent increased to ₹26,000 (annual landlord renewal)
    ok_upd, msg_upd = update_obligation_versioned(
        db=test_db,
        user_id=user_id,
        category="Rent/EMI",
        new_amount=26000,
        frequency="Monthly"
    )
    assert ok_upd is True

    # Step 3: Check database records
    # Total Rent records in DB must be 2 (old + new preserved)
    all_rents = (
        test_db.query(FixedObligation)
        .filter(FixedObligation.user_id == user_id, FixedObligation.category == "Rent/EMI")
        .order_by(FixedObligation.id)
        .all()
    )
    assert len(all_rents) == 2

    old_row, new_row = all_rents[0], all_rents[1]
    # Old row is closed
    assert old_row.amount == 22000
    assert old_row.effective_to == today

    # New row is active
    assert new_row.amount == 26000
    assert new_row.effective_from == today
    assert new_row.effective_to is None

    # Active profile query returns only the current ₹26,000
    profile_data = get_household_profile(test_db, user_id)
    active_rent_obs = [o for o in profile_data["obligations"] if o.category == "Rent/EMI"]
    assert len(active_rent_obs) == 1
    assert active_rent_obs[0].amount == 26000


def test_what_changed_audit_history(test_db, user_a):
    """Verify that get_version_history accurately tracks active and superseded rows."""
    user_id = user_a.user_id

    # Seed initial
    members = [{"name": "Self", "relation": "Self", "age": 30}]
    incomes = [{"earner_name": "Self", "source_type": "Salary", "amount": 60000}]
    obligations = [
        {"category": "Rent/EMI", "amount": 18000, "frequency": "Monthly"},
        {"category": "Groceries", "amount": 10000, "frequency": "Monthly"},
        {"category": "Utilities", "amount": 3000, "frequency": "Monthly"}
    ]
    save_initial_onboarding(
        db=test_db,
        user_id=user_id,
        state="Delhi (NCR)",
        city_type="Metro",
        household_size=1,
        members_data=members,
        incomes_data=incomes,
        obligations_data=obligations
    )

    # Modify groceries from 10000 to 12500
    update_obligation_versioned(test_db, user_id, "Groceries", 12500)

    # Check history
    hist = get_version_history(test_db, user_id)
    grocery_events = [h for h in hist if h["item"] == "Groceries"]
    assert len(grocery_events) == 2

    statuses = [g["status"] for g in grocery_events]
    assert "Active" in statuses
    assert any("Ended" in s for s in statuses)
