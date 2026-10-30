"""
Time-Series Cross-Validation and Data Leakage Guard Tests.
Verifies that:
1. Training indices strictly precede test indices (t_train < t_test).
2. Features are strictly backward-looking with zero lookahead leakage.
3. Computed evaluation metrics satisfy mathematical invariants (RMSE >= MAE >= 0).
4. Prediction intervals are valid (upper >= lower).
"""

import pytest
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from ml.pipeline import build_unified_dataset
from ml.features import create_feature_matrix
from ml.evaluate import calculate_metrics, compute_prediction_intervals
from ml.data_sources.mospi_cpi import CATEGORIES


@pytest.fixture(scope="module")
def sample_dataset():
    """Build unified dataset once for tests."""
    df, meta = build_unified_dataset()
    return df


def test_time_series_split_strictly_forward(sample_dataset):
    """
    Ensure walk-forward splits adhere to temporal ordering:
    max(train_idx) < min(test_idx) for every single split.
    Guarantees no future data leaks into the training set.
    """
    X, y, _ = create_feature_matrix(sample_dataset, target_category="Food and Beverages")
    tscv = TimeSeriesSplit(n_splits=5)

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        max_train = np.max(train_idx)
        min_test = np.min(test_idx)
        assert max_train < min_test, (
            f"Leakage detected in fold {fold}: max train index {max_train} >= min test index {min_test}"
        )
        assert len(train_idx) > 0
        assert len(test_idx) > 0


def test_zero_lookahead_in_feature_matrix(sample_dataset):
    """
    Verify that features at time t only depend on observations at or before time t.
    Specifically, lag_1 at row k must exactly equal the target series at row k-1.
    """
    cat = "Headline CPI"
    target_col = f"{cat}_YoY"
    X, y, feature_names = create_feature_matrix(sample_dataset, target_category=cat, forecast_horizon=1)

    # In create_feature_matrix, lag_1 is the target series at the current row
    # and y is the target series shifted by -forecast_horizon (-1)
    assert "lag_1" in feature_names
    assert "lag_12" in feature_names
    assert "base_effect_12m" in feature_names

    # Check that y is indeed 1 step ahead of lag_1
    # y[i] is Target[t+1], while lag_1[i] is Target[t]
    for i in range(len(X) - 1):
        assert X.loc[i + 1, "lag_1"] == pytest.approx(y.iloc[i], abs=1e-5)


def test_metric_calculation_invariants():
    """Verify RMSE >= MAE >= 0 and non-trivial MAPE calculation."""
    y_true = np.array([4.5, 5.2, 6.1, 5.8, 4.9])
    y_pred = np.array([4.8, 5.0, 6.5, 5.4, 5.1])

    metrics = calculate_metrics(y_true, y_pred, baseline_mape=12.0)

    assert metrics["rmse"] >= metrics["mae"] >= 0.0
    assert metrics["mape"] > 0.0
    assert metrics["smape"] > 0.0
    assert -100.0 <= metrics["baseline_improvement_pct"] <= 100.0


def test_prediction_intervals_bounds():
    """Verify that prediction intervals always satisfy upper >= lower."""
    residuals = np.array([-0.8, -0.4, 0.1, 0.5, 1.2, -0.2, 0.3])
    point_forecast = 5.5

    lower, upper = compute_prediction_intervals(point_forecast, residuals, confidence_level=0.80)
    assert upper >= lower
    assert lower <= point_forecast <= upper
