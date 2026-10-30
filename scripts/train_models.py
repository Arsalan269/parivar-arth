"""
CLI Runner to Execute Data Pipeline, Model Training, Cross-Validation,
and Forecast Table Database Population.
Run command: python scripts/train_models.py
"""

import os
import sys

# Ensure root is on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import init_db
from ml.pipeline import build_unified_dataset
from ml.train import train_all_categories
from ml.forecast import generate_multi_period_forecasts, save_forecasts_to_db


def main():
    print("==================================================")
    print(" PARIVAR ARTH - ML PIPELINE & FORECAST TRAINING ")
    print("==================================================")
    
    # Initialize DB
    init_db()

    print("\n[Step 1/4] Ingesting and Harmonizing CPI & Macro Datasets...")
    df, meta = build_unified_dataset()
    print(f" -> Ingestion complete: {meta['rows']} monthly observations ({meta['start_date']} to {meta['end_date']})")
    print(f" -> Synthetic data indicator: {meta['is_synthetic']} ({meta['cpi_source']})")
    print(f" -> Validation Passed: {meta['validation_passed']}")

    print("\n[Step 2/4] Executing Walk-Forward CV across 5 Model Architectures...")
    results = train_all_categories(df)

    print("\n[Step 3/4] Model Evaluation Summary vs Naive Baseline:")
    print("--------------------------------------------------------------------------------")
    print(f"{'Category':<30} | {'Best Model':<15} | {'RMSE':<6} | {'MAPE':<6} | {'Improvement'}")
    print("--------------------------------------------------------------------------------")
    for cat, res in results.items():
        leaderboard = res["leaderboard"]
        best = leaderboard.iloc[0]
        imp_str = f"+{best['improvement_pct']}%" if best["improvement_pct"] > 0 else f"{best['improvement_pct']}%"
        print(f"{cat:<30} | {best['model']:<15} | {best['rmse']:<6.3f} | {best['mape']:<5.1f}% | {imp_str}")
    print("--------------------------------------------------------------------------------")

    print("\n[Step 4/4] Generating 24-Month Forward Predictions with 80% Intervals...")
    forecasts = generate_multi_period_forecasts(results, df, horizon_months=24)
    save_forecasts_to_db(forecasts)

    print("\n[SUCCESS] Machine Learning Pipeline & Forecast Refresh Completed Successfully!\n")


if __name__ == "__main__":
    main()
