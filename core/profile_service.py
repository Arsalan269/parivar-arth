"""
Household Profile & Financial Versioning Service for Parivar Arth.
Implements:
1. Conditional mandatory profile validation logic based on family structure
2. Versioned financial profile editing (closing old row via effective_to, inserting new via effective_from)
3. Audit history retrieval for 'What Changed' user transparency
"""

from datetime import date, datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from core.models import (
    Profile, FamilyMember, IncomeSource, FixedObligation,
    RecurringExpense, HouseholdHelp, Loan, Asset, AuditLog
)


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)



def get_household_profile(db: Session, user_id: int) -> Dict[str, Any]:
    """Retrieve full active profile and all associated financial records for user."""
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    members = db.query(FamilyMember).filter(FamilyMember.user_id == user_id).all()
    
    # Active incomes (effective_to is NULL or strictly in future)
    today = date.today()
    incomes = (
        db.query(IncomeSource)
        .filter(IncomeSource.user_id == user_id, (IncomeSource.effective_to == None) | (IncomeSource.effective_to > today))
        .all()
    )
    
    # Active fixed obligations (effective_to is NULL or strictly in future)
    obligations = (
        db.query(FixedObligation)
        .filter(FixedObligation.user_id == user_id, (FixedObligation.effective_to == None) | (FixedObligation.effective_to > today))
        .all()
    )
    
    recurring = db.query(RecurringExpense).filter(RecurringExpense.user_id == user_id).all()
    help_records = db.query(HouseholdHelp).filter(HouseholdHelp.user_id == user_id).all()
    loans = db.query(Loan).filter(Loan.user_id == user_id).all()
    assets = db.query(Asset).filter(Asset.user_id == user_id).all()

    return {
        "profile": profile,
        "members": members,
        "incomes": incomes,
        "obligations": obligations,
        "recurring": recurring,
        "household_help": help_records,
        "loans": loans,
        "assets": assets
    }


def validate_profile_completeness(
    profile_data: Dict[str, Any],
    members: List[Dict[str, Any]],
    incomes: List[Dict[str, Any]],
    obligations: List[Dict[str, Any]]
) -> Tuple[bool, List[str]]:
    """
    Validate mandatory logic conditionally dependent on family composition:
    - Always mandatory: state, city_type, household_size >= 1
    - Always mandatory: at least one earner with monthly income > 0
    - Always mandatory: Rent/EMI obligation (0 allowed if ancestral/owned free)
    - Always mandatory: Groceries and Utilities obligations (>= 0)
    - Conditional: If a child is present -> Children's education fees mandatory
    - Conditional: If a parent is present -> Parents' medical expenses mandatory
    """
    errors = []

    # 1. Geographic & household size
    if not profile_data.get("state"):
        errors.append("Please select your State of residence.")
    if not profile_data.get("city_type"):
        errors.append("Please specify city classification (Metro, Tier-1, etc.).")
    hh_size = profile_data.get("household_size", 0)
    if hh_size < 1:
        errors.append("Household size must be at least 1 person.")

    # 2. Earner check
    active_incomes = [inc for inc in incomes if float(inc.get("amount", 0)) > 0]
    if not active_incomes:
        errors.append("At least one active earner with monthly income > ₹0 is required.")

    # 3. Always mandatory expense categories
    categories = {ob.get("category") for ob in obligations}
    if "Rent/EMI" not in categories and "Housing" not in categories and "Rent" not in categories:
        errors.append("Housing cost (Rent or EMI) is mandatory (enter 0 if self-owned without loan).")
    if "Groceries" not in categories:
        errors.append("Monthly groceries estimate is mandatory.")
    if "Utilities" not in categories:
        errors.append("Monthly utilities estimate (electricity, water, LPG) is mandatory.")

    # 4. Conditional logic based on family members
    has_child = any(m.get("relation") == "Child" for m in members)
    has_parent = any(m.get("relation") == "Parent" for m in members)

    if has_child:
        if "Child Education" not in categories:
            errors.append("Children's education fees are required when dependent children are added.")

    if has_parent:
        if "Parent Medical" not in categories:
            errors.append("Parents' medical provision is required when dependent parents are added.")

    return len(errors) == 0, errors


def save_initial_onboarding(
    db: Session,
    user_id: int,
    state: str,
    city_type: str,
    household_size: int,
    members_data: List[Dict[str, Any]],
    incomes_data: List[Dict[str, Any]],
    obligations_data: List[Dict[str, Any]],
    loans_data: Optional[List[Dict[str, Any]]] = None,
    assets_data: Optional[List[Dict[str, Any]]] = None,
    help_data: Optional[List[Dict[str, Any]]] = None
) -> Tuple[bool, str]:
    """Persist initial onboarding profile and financial entities."""
    # Validation
    is_valid, errors = validate_profile_completeness(
        {"state": state, "city_type": city_type, "household_size": household_size},
        members_data,
        incomes_data,
        obligations_data
    )
    if not is_valid:
        return False, " | ".join(errors)

    today = date.today()

    # 1. Profile
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        profile = Profile(
            user_id=user_id,
            state=state,
            city_type=city_type,
            household_size=household_size,
            is_onboarding_completed=True
        )
        db.add(profile)
    else:
        profile.state = state
        profile.city_type = city_type
        profile.household_size = household_size
        profile.is_onboarding_completed = True

    # 2. Family Members
    # Map created members for earner and dependent foreign keys
    member_map = {}
    for m in members_data:
        fam = FamilyMember(
            user_id=user_id,
            name=m["name"].strip(),
            relation=m["relation"],
            age=int(m["age"]),
            has_chronic_condition=bool(m.get("has_chronic_condition", False))
        )
        db.add(fam)
        db.flush()
        member_map[fam.name] = fam.id

    # 3. Income Sources
    for inc in incomes_data:
        earner_id = member_map.get(inc.get("earner_name"))
        db.add(IncomeSource(
            user_id=user_id,
            earner_id=earner_id,
            source_type=inc.get("source_type", "Salary"),
            amount=float(inc["amount"]),
            is_variable=bool(inc.get("is_variable", False)),
            effective_from=today,
            effective_to=None
        ))

    # 4. Fixed Obligations
    for ob in obligations_data:
        db.add(FixedObligation(
            user_id=user_id,
            category=ob["category"],
            amount=float(ob["amount"]),
            frequency=ob.get("frequency", "Monthly"),
            effective_from=today,
            effective_to=None
        ))

    # 5. Loans (Optional)
    if loans_data:
        for ln in loans_data:
            if float(ln.get("balance", 0)) > 0:
                db.add(Loan(
                    user_id=user_id,
                    loan_type=ln.get("loan_type", "Personal Loan"),
                    balance=float(ln["balance"]),
                    interest_rate=float(ln.get("interest_rate", 9.0)),
                    emi=float(ln["emi"]),
                    remaining_months=int(ln.get("remaining_months", 12)),
                    rate_type=ln.get("rate_type", "Fixed")
                ))

    # 6. Assets (Optional)
    if assets_data:
        for ast in assets_data:
            if float(ast.get("amount", 0)) > 0:
                db.add(Asset(
                    user_id=user_id,
                    type=ast.get("type", "Savings Account"),
                    amount=float(ast["amount"]),
                    is_liquid=bool(ast.get("is_liquid", True))
                ))

    # 7. Household Help (Optional)
    if help_data:
        for hl in help_data:
            if float(hl.get("monthly_cost", 0)) > 0:
                db.add(HouseholdHelp(
                    user_id=user_id,
                    role=hl.get("role", "Maid"),
                    monthly_cost=float(hl["monthly_cost"]),
                    growth_override=hl.get("growth_override")
                ))

    db.add(AuditLog(
        actor=f"user_{user_id}",
        action="ONBOARDING_COMPLETED",
        timestamp=get_utc_now(),
        details=f"State: {state}, City: {city_type}, Size: {household_size}"
    ))

    db.commit()
    return True, "Onboarding profile saved successfully!"


def update_obligation_versioned(
    db: Session,
    user_id: int,
    category: str,
    new_amount: float,
    frequency: str = "Monthly"
) -> Tuple[bool, str]:
    """
    Update a fixed obligation using strict versioning:
    - Closes active row by setting effective_to = today
    - Inserts a new row with effective_from = today and effective_to = NULL
    Never overwrites historical data.
    """
    today = date.today()
    active_row = (
        db.query(FixedObligation)
        .filter(FixedObligation.user_id == user_id, FixedObligation.category == category, FixedObligation.effective_to == None)
        .first()
    )

    if active_row:
        if abs(active_row.amount - new_amount) < 0.01 and active_row.frequency == frequency:
            return True, "No change detected in amount or frequency."
        # Close old row
        active_row.effective_to = today

    # Insert new row
    new_row = FixedObligation(
        user_id=user_id,
        category=category,
        amount=new_amount,
        frequency=frequency,
        effective_from=today,
        effective_to=None
    )
    db.add(new_row)
    db.add(AuditLog(
        actor=f"user_{user_id}",
        action="OBLIGATION_VERSION_UPDATED",
        timestamp=get_utc_now(),
        details=f"Category: {category}, Old: {active_row.amount if active_row else 0}, New: {new_amount}"
    ))
    db.commit()
    return True, f"Updated {category} to ₹{new_amount:,.0f} (previous version preserved)."


def update_income_versioned(
    db: Session,
    user_id: int,
    income_id: int,
    new_amount: float,
    is_variable: bool
) -> Tuple[bool, str]:
    """
    Update an income source using strict versioning.
    """
    today = date.today()
    active_row = db.query(IncomeSource).filter(IncomeSource.id == income_id, IncomeSource.user_id == user_id).first()

    if not active_row:
        return False, "Income record not found."

    if abs(active_row.amount - new_amount) < 0.01 and active_row.is_variable == is_variable:
        return True, "No change detected."

    old_amount = active_row.amount
    # Close old row
    active_row.effective_to = today

    # Insert new versioned row
    new_row = IncomeSource(
        user_id=user_id,
        earner_id=active_row.earner_id,
        source_type=active_row.source_type,
        amount=new_amount,
        is_variable=is_variable,
        effective_from=today,
        effective_to=None
    )
    db.add(new_row)
    db.add(AuditLog(
        actor=f"user_{user_id}",
        action="INCOME_VERSION_UPDATED",
        timestamp=get_utc_now(),
        details=f"Type: {active_row.source_type}, Old: {old_amount}, New: {new_amount}"
    ))
    db.commit()
    return True, f"Updated {active_row.source_type} to ₹{new_amount:,.0f} (version preserved)."


def get_version_history(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """Retrieve full chronological audit history of profile changes for the user."""
    history = []

    # Obligations history
    obligations = (
        db.query(FixedObligation)
        .filter(FixedObligation.user_id == user_id)
        .order_by(FixedObligation.category, FixedObligation.effective_from.desc())
        .all()
    )

    for ob in obligations:
        status = "Active" if ob.effective_to is None else f"Ended {ob.effective_to.strftime('%d %b %Y')}"
        history.append({
            "type": "Fixed Obligation",
            "item": ob.category,
            "amount": ob.amount,
            "frequency": ob.frequency,
            "effective_from": ob.effective_from.strftime("%d %b %Y"),
            "effective_to": ob.effective_to.strftime("%d %b %Y") if ob.effective_to else "Current",
            "status": status
        })

    # Incomes history
    incomes = (
        db.query(IncomeSource)
        .filter(IncomeSource.user_id == user_id)
        .order_by(IncomeSource.source_type, IncomeSource.effective_from.desc())
        .all()
    )

    for inc in incomes:
        status = "Active" if inc.effective_to is None else f"Ended {inc.effective_to.strftime('%d %b %Y')}"
        history.append({
            "type": "Income Source",
            "item": inc.source_type,
            "amount": inc.amount,
            "frequency": "Monthly",
            "effective_from": inc.effective_from.strftime("%d %b %Y"),
            "effective_to": inc.effective_to.strftime("%d %b %Y") if inc.effective_to else "Current",
            "status": status
        })

    return history
