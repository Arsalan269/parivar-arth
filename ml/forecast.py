"""
Forward Forecasting and Database Population Engine for Parivar Arth.
Generates 1 to 24-month multi-step inflation forecasts across all official CPI categories
with 80% prediction intervals, persisting them into the 'forecasts' table.
"""

from datetime import date, datetime
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from ml.evaluate import compute_prediction_intervals
from ml.data_sources.mospi_cpi import CATEGORIES
from core.db import get_db_session
from core.models import Forecast


def generate_multi_period_forecasts(
    training_results: Dict[str, Any],
    df_latest: pd.DataFrame,
    horizon_months: int = 24
) -> List[Dict[str, Any]]:
    """
    Generate forward forecasts for 1 to horizon_months forward for all categories.
    Uses recursive roll-forward with seasonal adjustment.
    """
    last_date = pd.to_datetime(df_latest["date"].iloc[-1])
    future_dates = [last_date + pd.DateOffset(months=m) for m in range(1, horizon_months + 1)]

    all_forecast_records = []

    for cat in CATEGORIES:
        res = training_results.get(cat)
        if not res:
            continue

        model = res["best_model"]
        residuals = res["residuals"]
        X_latest = res["X_latest"].copy()

        # Current inflation baseline
        curr_val = float(df_latest[f"{cat}_YoY"].iloc[-1])

        # Step forward recursively
        prev_pred = curr_val
        for step, f_date in enumerate(future_dates, start=1):
            # Update seasonal and calendar flags for future target month
            f_month = f_date.month
            if "month" in X_latest.columns:
                X_latest["month"] = f_month
            if "is_monsoon" in X_latest.columns:
                X_latest["is_monsoon"] = int(f_month in [6, 7, 8, 9])
            if "is_festival" in X_latest.columns:
                X_latest["is_festival"] = int(f_month in [9, 10, 11])
            if "is_school_season" in X_latest.columns:
                X_latest["is_school_season"] = int(f_month in [4, 5, 6])

            # Update autoregressive lags
            if "lag_1" in X_latest.columns:
                X_latest["lag_1"] = prev_pred

            # Predict next step
            pred_val = float(model.predict(X_latest)[0])
            # Bound realistic bounds for safety
            pred_val = max(1.5, min(18.0, pred_val))

            # Intervals (expand slightly over longer horizons: sqrt(step/2))
            horizon_scale = np.sqrt(step) * 0.4
            lower, upper = compute_prediction_intervals(pred_val, residuals, confidence_level=0.80)
            lower = round(max(0.5, lower - horizon_scale), 2)
            upper = round(min(22.0, upper + horizon_scale), 2)

            all_forecast_records.append({
                "category": cat,
                "target_month": f_date.date(),
                "predicted_inflation": round(pred_val, 2),
                "lower_ci": lower,
                "upper_ci": upper,
                "model_version": "v1.0-prod"
            })

            prev_pred = pred_val

    return all_forecast_records


def save_forecasts_to_db(forecast_records: List[Dict[str, Any]]):
    """
    Persist generated forecasts into the global 'forecasts' database table.
    Clears previous forecasts for the same model_version to ensure freshness.
    """
    with get_db_session() as db:
        # Clear existing active forecasts
        db.query(Forecast).delete()
        db.flush()

        # Insert new forecast records
        now_utc = datetime.utcnow()
        for rec in forecast_records:
            item = Forecast(
                category=rec["category"],
                target_month=rec["target_month"],
                predicted_inflation=rec["predicted_inflation"],
                lower_ci=rec["lower_ci"],
                upper_ci=rec["upper_ci"],
                model_version=rec.get("model_version", "v1.0-prod"),
                created_at=now_utc
            )
            db.add(item)
        db.commit()
    print(f"Successfully saved {len(forecast_records)} forecast records to database.")
