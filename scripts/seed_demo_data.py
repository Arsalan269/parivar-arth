"""
Database Seeding Script for Parivar Arth.
Initializes database tables and ensures calibrated ML category forecasts exist.
Does not seed any administrator accounts or published-password accounts.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import init_db, get_db_session
from core.models import Forecast
from ml.pipeline import build_unified_dataset
from ml.train import train_all_categories
from ml.forecast import generate_multi_period_forecasts, save_forecasts_to_db


def seed_database():
    print("==================================================")
    print(" PARIVAR ARTH - DATABASE INITIALIZATION ENGINE ")
    print("==================================================")
    init_db()

    with get_db_session() as db:
        # Check if forecasts exist
        fc_count = db.query(Forecast).count()
        if fc_count == 0:
            print("\n -> No forecasts found in database. Running ML training pipeline...")
            df_pipe, meta = build_unified_dataset()
            train_res = train_all_categories(df_pipe)
            forecasts = generate_multi_period_forecasts(train_res, df_pipe, horizon_months=24)
            save_forecasts_to_db(forecasts)
            print(f"\n -> Successfully seeded {len(forecasts)} forecast records.")
        else:
            print(f"\n -> {fc_count} active forecast records present in database.")

    print("\n[SUCCESS] Initialization Complete! Database ready for user registration.\n")


if __name__ == "__main__":
    seed_database()
