"""
Unified Data Processing Pipeline for Parivar Arth.
Harmonizes CPI indices, computes YoY inflation rates, merges macro drivers,
and performs rigorous data validation checks.
"""

import os
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any
from ml.data_sources.mospi_cpi import MospiCpiDataSource, CATEGORIES
from ml.data_sources.market_macro import MarketMacroDataSource


def build_unified_dataset() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Execute full ingestion and harmonization pipeline.
    
    Returns:
        (df_unified, metadata_dict)
    """
    cpi_source = MospiCpiDataSource()
    macro_source = MarketMacroDataSource()

    df_cpi, cpi_is_syn, cpi_desc = cpi_source.get_data()
    df_macro, macro_is_syn, macro_desc = macro_source.get_data()

    # Ensure datetime format
    df_cpi["date"] = pd.to_datetime(df_cpi["date"])
    df_macro["date"] = pd.to_datetime(df_macro["date"])

    # Merge on month start date
    df = pd.merge(df_cpi, df_macro, on="date", how="inner")
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Compute Year-over-Year (YoY) inflation rates for each category
    # Formula: (CPI_t - CPI_{t-12}) / CPI_{t-12} * 100
    for cat in CATEGORIES:
        col_name = f"{cat}_YoY"
        df[col_name] = ((df[cat] - df[cat].shift(12)) / df[cat].shift(12)) * 100

    # Macro driver transforms
    df["crude_inr_pct_change_12m"] = ((df["crude_inr"] - df["crude_inr"].shift(12)) / df["crude_inr"].shift(12)) * 100
    df["usd_inr_pct_change_12m"] = ((df["usd_inr"] - df["usd_inr"].shift(12)) / df["usd_inr"].shift(12)) * 100
    df["wpi_YoY"] = ((df["wpi"] - df["wpi"].shift(12)) / df["wpi"].shift(12)) * 100

    # Drop the first 12 warm-up rows that have NaN from shift(12)
    df = df.iloc[12:].reset_index(drop=True)

    # Validation Checks
    validation_passed = True
    validation_errors = []

    # 1. Monotonic date check
    if not df["date"].is_monotonic_increasing:
        validation_passed = False
        validation_errors.append("Dates are not monotonically increasing.")

    # 2. NaN check
    null_counts = df.isnull().sum()
    if null_counts.any():
        validation_passed = False
        validation_errors.append(f"Unexpected NaNs found in columns: {null_counts[null_counts > 0].to_dict()}")

    # 3. Plausible Indian economic range check (-5% to +25% YoY inflation)
    for cat in CATEGORIES:
        yoy_col = f"{cat}_YoY"
        min_val, max_val = df[yoy_col].min(), df[yoy_col].max()
        if min_val < -10.0 or max_val > 30.0:
            validation_passed = False
            validation_errors.append(f"Inflation for {cat} out of bounds: min={min_val:.1f}%, max={max_val:.1f}%")

    # Persist processed dataset
    processed_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
    os.makedirs(processed_dir, exist_ok=True)
    output_path = os.path.join(processed_dir, "monthly_macro_cpi.csv")
    df.to_csv(output_path, index=False)

    metadata = {
        "is_synthetic": cpi_is_syn or macro_is_syn,
        "cpi_source": cpi_desc,
        "macro_source": macro_desc,
        "rows": len(df),
        "start_date": str(df["date"].min().date()),
        "end_date": str(df["date"].max().date()),
        "validation_passed": validation_passed,
        "validation_errors": validation_errors,
        "saved_path": output_path,
    }

    return df, metadata


if __name__ == "__main__":
    df, meta = build_unified_dataset()
    print("Pipeline executed successfully!")
    print(f"Dataset shape: {df.shape}")
    print(f"Synthetic flag: {meta['is_synthetic']}")
    print(f"Validation passed: {meta['validation_passed']}")
