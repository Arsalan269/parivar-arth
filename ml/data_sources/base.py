"""
Abstract Base Fetcher for Parivar Arth Data Science Pipeline.
Guarantees a 3-tier resilient data interface:
1. Live Fetch (APIs / Web)
2. Manual CSV Drop in data/raw/
3. Calibrated Synthetic Sample Fallback (Prominently labeled)
"""

from abc import ABC, abstractmethod
import os
import pandas as pd
from typing import Tuple


class BaseDataSource(ABC):
    def __init__(self, name: str, raw_filename: str):
        self.name = name
        self.raw_filename = raw_filename
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.raw_dir = os.path.join(self.base_dir, "data", "raw")
        self.sample_dir = os.path.join(self.base_dir, "data", "sample")
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.sample_dir, exist_ok=True)

    @abstractmethod
    def fetch_live(self) -> pd.DataFrame:
        """Attempt to fetch live data from public source/API."""
        pass

    @abstractmethod
    def generate_synthetic_fallback(self) -> pd.DataFrame:
        """Generate a statistically calibrated synthetic fallback based on published RBI/MoSPI trends."""
        pass

    def load_csv_drop(self) -> pd.DataFrame:
        """Attempt to load user-dropped raw CSV."""
        filepath = os.path.join(self.raw_dir, self.raw_filename)
        if os.path.exists(filepath):
            return pd.read_csv(filepath)
        return pd.DataFrame()

    def get_data(self) -> Tuple[pd.DataFrame, bool, str]:
        """
        Retrieval precedence:
        1. User manual CSV drop
        2. Live fetch
        3. Synthetic fallback (clearly labeled)
        
        Returns:
            (DataFrame, is_synthetic: bool, source_description: str)
        """
        # 1. Manual drop
        try:
            df_drop = self.load_csv_drop()
            if not df_drop.empty:
                return df_drop, False, f"Loaded from manual CSV drop: {self.raw_filename}"
        except Exception:
            pass

        # 2. Live fetch
        try:
            df_live = self.fetch_live()
            if not df_live.empty:
                return df_live, False, f"Live fetch successful from {self.name}"
        except Exception:
            pass

        # 3. Documented synthetic fallback
        df_synthetic = self.generate_synthetic_fallback()
        return df_synthetic, True, f"Calibrated synthetic fallback for {self.name} (Clearly labeled: Not live data)"
