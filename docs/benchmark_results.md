# Model Benchmark Results (Walk-Forward Time-Series Cross-Validation)

Generated from `python scripts/train_models.py` across 5-fold TimeSeriesSplit on calibrated monthly inflation data.

```text
==================================================
 PARIVAR ARTH - ML PIPELINE & FORECAST TRAINING 
==================================================

[Step 1/4] Ingesting and Harmonizing CPI & Macro Datasets...
 -> Ingestion complete: 142 monthly observations (2015-01-01 to 2026-10-01)
 -> Synthetic data indicator: True (Calibrated synthetic fallback for MoSPI CPI All-India (Clearly labeled: Not live data))
 -> Validation Passed: True

[Step 2/4] Executing Walk-Forward CV across 5 Model Architectures...
--> Training and evaluating models for: Headline CPI...
--> Training and evaluating models for: Food and Beverages...
--> Training and evaluating models for: Housing...
--> Training and evaluating models for: Fuel and Light...
--> Training and evaluating models for: Transport and Communication...
--> Training and evaluating models for: Health...
--> Training and evaluating models for: Education...
--> Training and evaluating models for: Miscellaneous Services...

[Step 3/4] Model Evaluation Summary vs Naive Baseline:
--------------------------------------------------------------------------------
Category                       | Best Model      | RMSE   | MAPE   | Improvement
--------------------------------------------------------------------------------
Headline CPI                   | Random Forest   | 0.677  | 9.9  % | +18.54%
Food and Beverages             | XGBoost         | 1.685  | 28.8 % | +2.72%
Housing                        | Random Forest   | 0.676  | 11.5 % | +14.25%
Fuel and Light                 | Naive Baseline  | 1.501  | 27.6 % | +0.01%
Transport and Communication    | Naive Baseline  | 1.526  | 24.0 % | +0.02%
Health                         | XGBoost         | 0.813  | 8.0  % | +21.61%
Education                      | XGBoost         | 0.720  | 7.5  % | +18.82%
Miscellaneous Services         | XGBoost         | 0.618  | 8.9  % | +21.15%
--------------------------------------------------------------------------------

[Step 4/4] Generating 24-Month Forward Predictions with 80% Intervals...
Successfully saved 192 forecast records to database.

[SUCCESS] Machine Learning Pipeline & Forecast Refresh Completed Successfully!
```

## Formatted Leaderboard

| Category | Best Model | Out-of-Fold RMSE | Out-of-Fold MAPE | Improvement vs Naive Baseline |
| :--- | :--- | :--- | :--- | :--- |
| **Headline CPI** | Random Forest | 0.677 | 9.9% | +18.54% |
| **Food and Beverages** | XGBoost | 1.685 | 28.8% | +2.72% |
| **Housing** | Random Forest | 0.676 | 11.5% | +14.25% |
| **Fuel and Light** | Naive Baseline | 1.501 | 27.6% | +0.01% |
| **Transport and Communication** | Naive Baseline | 1.526 | 24.0% | +0.02% |
| **Health** | XGBoost | 0.813 | 8.0% | +21.61% |
| **Education** | XGBoost | 0.720 | 7.5% | +18.82% |
| **Miscellaneous Services** | XGBoost | 0.618 | 8.9% | +21.15% |
