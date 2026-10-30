"""
Feature Engineering for Indian CPI Inflation Time Series.
Generates:
- Autoregressive lags (t-1, t-2, t-3, t-12)
- Rolling window statistics (mean, volatility)
- Seasonal and calendar indicators (Monsoon Kharif dummy, Festival dummy)
- Macro exogenous indicators (Crude in INR, USD/INR, Repo Rate, Rainfall Departure)
"""

import numpy as np
import pandas as pd
from typing import Tuple, List


def create_feature_matrix(
    df: pd.DataFrame,
    target_category: str,
    forecast_horizon: int = 1
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Construct time-series feature matrix with ZERO lookahead.
    
    Args:
        df: Processed master monthly dataframe
        target_category: e.g. "Food and Beverages" or "Headline CPI"
        forecast_horizon: number of months ahead to predict (default 1)
        
    Returns:
        (X, y, feature_names)
    """
    df = df.copy()
    target_col = f"{target_category}_YoY"
    
    if target_col not in df.columns:
        raise ValueError(f"Target column {target_col} not found in dataframe.")

    # Target: inflation rate 'forecast_horizon' months into the future
    # y_t = Target_{t + h}
    y = df[target_col].shift(-forecast_horizon)

    X = pd.DataFrame(index=df.index)

    # 1. Autoregressive Lags (strictly backward-looking)
    for lag in [1, 2, 3, 12]:
        X[f"lag_{lag}"] = df[target_col].shift(lag - 1)

    # 2. Rolling Window Means & Volatility (Standard Deviation)
    # Using shift(0) on historical t-1, t-2, t-3
    s = df[target_col]
    X["rolling_mean_3m"] = s.rolling(window=3).mean()
    X["rolling_std_3m"] = s.rolling(window=3).std().fillna(0)
    X["rolling_mean_6m"] = s.rolling(window=6).mean()
    X["rolling_std_6m"] = s.rolling(window=6).std().fillna(0)

    # 3. Base Effect Indicator (Inflation level 12 months ago)
    X["base_effect_12m"] = df[target_col].shift(12)

    # 4. Seasonal & Calendar Features
    months = df["date"].dt.month
    X["month"] = months
    X["is_monsoon"] = months.isin([6, 7, 8, 9]).astype(int)      # Monsoon impact on vegetables/pulses
    X["is_festival"] = months.isin([9, 10, 11]).astype(int)     # Diwali/Navratri consumption surge
    X["is_school_season"] = months.isin([4, 5, 6]).astype(int)  # School admission fee jumps

    # 5. Exogenous Macro Drivers (lagged by 1 month to reflect reporting delay)
    X["crude_inr_pct_change"] = df["crude_inr_pct_change_12m"].shift(1)
    X["usd_inr_pct_change"] = df["usd_inr_pct_change_12m"].shift(1)
    X["repo_rate"] = df["repo_rate"].shift(1)
    X["rainfall_departure"] = df["rainfall_departure"].shift(1)
    X["wpi_YoY"] = df["wpi_YoY"].shift(1)

    # Drop NaNs from shift operations and future-horizon alignment
    valid_mask = (~X.isna().any(axis=1)) & (~y.isna())
    X_clean = X.loc[valid_mask].reset_index(drop=True)
    y_clean = y.loc[valid_mask].reset_index(drop=True)

    return X_clean, y_clean, list(X_clean.columns)
