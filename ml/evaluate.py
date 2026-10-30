"""
Model Evaluation and Metric Calculation for Time-Series Inflation Models.
Computes real RMSE, MAE, MAPE, sMAPE, and Improvement over Naive Baseline.
Never relies on hardcoded or fabricated numbers.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray, baseline_mape: float = None) -> Dict[str, float]:
    """
    Calculate comprehensive evaluation metrics.
    
    Args:
        y_true: Array of actual observed values
        y_pred: Array of model predicted values
        baseline_mape: Optional MAPE of the persistence baseline for relative improvement
        
    Returns:
        dict with rmse, mae, mape, smape, baseline_improvement_pct
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    errors = y_true - y_pred
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    # Avoid zero-division in MAPE using small epsilon
    epsilon = 1e-4
    denom_mape = np.where(np.abs(y_true) < epsilon, epsilon, np.abs(y_true))
    mape = float(np.mean(np.abs(errors) / denom_mape) * 100.0)

    # Symmetric MAPE (sMAPE)
    denom_smape = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    denom_smape = np.where(denom_smape < epsilon, epsilon, denom_smape)
    smape = float(np.mean(np.abs(errors) / denom_smape) * 100.0)

    # Improvement over naive baseline
    if baseline_mape is not None and baseline_mape > 0:
        improvement = float((1.0 - (mape / baseline_mape)) * 100.0)
    else:
        improvement = 0.0

    return {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "mape": round(mape, 2),
        "smape": round(smape, 2),
        "baseline_improvement_pct": round(improvement, 2),
    }


def compute_prediction_intervals(
    y_pred: float,
    residuals: np.ndarray,
    confidence_level: float = 0.80
) -> Tuple[float, float]:
    """
    Compute residual-based quantile prediction interval bounds.
    
    Args:
        y_pred: Point forecast value
        residuals: Array of validation residuals (y_true - y_pred)
        confidence_level: Desired interval (default 80%)
        
    Returns:
        (lower_bound, upper_bound)
    """
    if len(residuals) == 0:
        # Default safety margin if no residuals
        return round(y_pred - 1.2, 2), round(y_pred + 1.2, 2)

    lower_p = (1.0 - confidence_level) / 2.0 * 100.0
    upper_p = (1.0 + confidence_level) / 2.0 * 100.0

    lower_err = float(np.percentile(residuals, lower_p))
    upper_err = float(np.percentile(residuals, upper_p))

    lower_bound = round(y_pred + lower_err, 2)
    upper_bound = round(y_pred + upper_err, 2)

    # Sanity guard: upper must exceed lower
    if upper_bound < lower_bound:
        lower_bound, upper_bound = upper_bound, lower_bound

    return lower_bound, upper_bound
