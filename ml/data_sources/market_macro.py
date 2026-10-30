"""
Macroeconomic and Market Drivers Data Source for Parivar Arth:
- Crude Oil (Brent) converted to INR
- USD/INR Exchange Rate
- Gold Price in INR
- RBI Repo Rate (%)
- IMD Monsoon Rainfall Departure Index (%)
- Wholesale Price Index (WPI)
"""

import socket
import numpy as np
import pandas as pd
from datetime import datetime
from ml.data_sources.base import BaseDataSource


def has_internet_connection() -> bool:
    """Fast non-blocking socket test to check if external DNS/network is reachable."""
    try:
        # Check standard public DNS server with 0.8s timeout
        socket.setdefaulttimeout(0.8)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("8.8.8.8", 53))
        s.close()
        return True
    except Exception:
        return False


class MarketMacroDataSource(BaseDataSource):
    def __init__(self):
        super().__init__(name="RBI, yfinance & IMD Macro Drivers", raw_filename="market_macro_drivers.csv")

    def fetch_live(self) -> pd.DataFrame:
        """Attempt to fetch live financial series from yfinance if network is available."""
        if not has_internet_connection():
            # Skip instantly without curl DNS timeouts in sandbox/offline mode
            return pd.DataFrame()

        try:
            import yfinance as yf
            # Brent Crude: 'BZ=F', USD/INR: 'INR=X', Gold: 'GC=F'
            tickers = ["BZ=F", "INR=X", "GC=F"]
            raw = yf.download(tickers, start="2014-01-01", interval="1mo", progress=False, timeout=3)
            if not raw.empty and "Close" in raw:
                close = raw["Close"].resample("MS").last().ffill()
                close.reset_index(inplace=True)
                close.rename(columns={
                    "Date": "date",
                    "BZ=F": "crude_usd",
                    "INR=X": "usd_inr",
                    "GC=F": "gold_usd"
                }, inplace=True)
                close["crude_inr"] = close["crude_usd"] * close["usd_inr"]
                return close
        except Exception:
            pass
        return pd.DataFrame()

    def generate_synthetic_fallback(self) -> pd.DataFrame:
        """
        Generates calibrated macro historical monthly time-series matching
        Indian economic milestones from Jan 2014 to Oct 2026.
        """
        dates = pd.date_range(start="2014-01-01", end="2026-10-01", freq="MS")
        n = len(dates)
        rng = np.random.RandomState(101)

        # 1. USD/INR exchange rate (drift from 62.0 to ~84.0)
        years = dates.year + (dates.month - 1) / 12.0
        usd_inr = 62.0 + (years - 2014) * 1.75 + rng.normal(0, 0.6, size=n)
        usd_inr = np.clip(usd_inr, 60.0, 85.0)

        # 2. Brent Crude Oil in USD ($40 to $125/bbl)
        crude_usd = np.zeros(n)
        for i, d in enumerate(dates):
            yr = d.year
            if yr in [2014]:
                crude_usd[i] = 95.0 - (d.month * 4.0)  # Plunge from $105 to $60
            elif yr in [2015, 2016]:
                crude_usd[i] = 45.0 + rng.normal(0, 4.0)
            elif yr in [2017, 2018, 2019]:
                crude_usd[i] = 65.0 + rng.normal(0, 5.0)
            elif yr == 2020:
                crude_usd[i] = 25.0 if d.month in [4, 5] else 42.0  # COVID crash
            elif yr == 2021:
                crude_usd[i] = 70.0 + (d.month * 1.5)
            elif yr == 2022:
                crude_usd[i] = 110.0 if d.month in [3, 4, 5, 6] else 88.0  # Ukraine peak
            elif yr in [2023, 2024]:
                crude_usd[i] = 82.0 + rng.normal(0, 4.0)
            else:  # 2025-2026
                crude_usd[i] = 78.0 + rng.normal(0, 3.5)

        crude_inr = np.round(crude_usd * usd_inr, 2)

        # 3. RBI Policy Repo Rate (%)
        # 8.0% in 2014 -> 6.0% in 2017 -> 4.0% in 2020 (COVID easing) -> 6.5% in 2023-2026
        repo_rate = np.zeros(n)
        for i, d in enumerate(dates):
            yr = d.year
            if yr == 2014:
                repo_rate[i] = 8.00
            elif yr in [2015, 2016]:
                repo_rate[i] = 6.75
            elif yr in [2017, 2018, 2019]:
                repo_rate[i] = 6.00
            elif yr in [2020, 2021]:
                repo_rate[i] = 4.00
            elif yr == 2022:
                repo_rate[i] = 4.90 if d.month < 8 else 5.90
            else:  # 2023-2026
                repo_rate[i] = 6.50

        # 4. IMD Monsoon Rainfall Departure Index (% from Long Period Average)
        # Monsoons occur in June-September (months 6, 7, 8, 9)
        rainfall_departure = np.zeros(n)
        for i, d in enumerate(dates):
            if d.month in [6, 7, 8, 9]:
                if d.year in [2014, 2015]:
                    rainfall_departure[i] = -14.0 + rng.normal(0, 3.0)  # Drought years
                elif d.year in [2019, 2020]:
                    rainfall_departure[i] = 10.0 + rng.normal(0, 2.5)   # Excess rain
                elif d.year == 2023:
                    rainfall_departure[i] = -6.0 + rng.normal(0, 2.0)   # El Nino deficit
                else:
                    rainfall_departure[i] = 1.0 + rng.normal(0, 3.0)    # Normal

        # 5. Wholesale Price Index (WPI All-Commodities, Base 2011-12=100)
        wpi_base = 112.0
        wpi_drift = (1 + 0.042) ** (1 / 12) - 1
        wpi = wpi_base * ((1 + wpi_drift) ** np.arange(n)) * (1 + rng.normal(0, 0.005, size=n))

        return pd.DataFrame({
            "date": dates,
            "usd_inr": np.round(usd_inr, 2),
            "crude_usd": np.round(crude_usd, 2),
            "crude_inr": crude_inr,
            "repo_rate": repo_rate,
            "rainfall_departure": np.round(rainfall_departure, 1),
            "wpi": np.round(wpi, 2)
        })
