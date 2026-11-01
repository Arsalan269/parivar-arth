# Codebase Verification Audit & Discrepancies Report

This document records the exact, verified facts inspected directly from the codebase (`parivar-arth`) and contrasts them with outdated or unverified claims found in earlier documentation.

---

## 1. Verified Facts Table

| Area | Code Location | Verified Fact / Implementation Detail |
| :--- | :--- | :--- |
| **Streamlit Pages** | `app/pages/` | Exactly **8 pages**: `1_My_Profile.py`, `2_Monthly_Tracker.py`, `3_Savings_Advisor.py`, `4_Future_Planner.py`, `5_Reduce_Expenses.py`, `6_Loans_Emergency.py`, `7_Yearly_Calendar.py`, `8_Reports.py`. Entrypoint: `Login.py`; forwarder: `main.py`. |
| **Commodity Categories** | `ml/data_sources/mospi_cpi.py` | Exactly **8 categories**: `Headline CPI`, `Food and Beverages`, `Housing`, `Fuel and Light`, `Transport and Communication`, `Health`, `Education`, `Miscellaneous Services`. |
| **CPI Data Source** | `ml/data_sources/mospi_cpi.py` | **Calibrated synthetic fallback** (142 monthly observations: Jan 2015 to Oct 2026), calibrated against historical Indian RBI/MoSPI trends; not live streaming data. |
| **Prediction Intervals** | `ml/evaluate.py`, `ml/forecast.py` | **80% prediction intervals** (`compute_prediction_intervals(..., confidence_level=0.80)`), residual quantile-based. |
| **Autoregressive Lags** | `ml/features.py` | Strictly backward-looking lags: **`lag_1`**, **`lag_2`**, **`lag_3`**, **`lag_12`** (no lag 6). |
| **Rolling Windows** | `ml/features.py` | Rolling statistics: **3-month** and **6-month** mean and standard deviation (`rolling_mean_3m`, `rolling_std_3m`, `rolling_mean_6m`, `rolling_std_6m`). |
| **Seasonal Dummies** | `ml/features.py` | `is_monsoon` (months 6–9), `is_festival` (months 9–11), `is_school_season` (months 4–6). |
| **Exogenous Drivers** | `ml/features.py` | Shifted by 1 month: Crude in INR (`crude_inr_pct_change_12m`), USD/INR (`usd_inr_pct_change_12m`), RBI Repo Rate (`repo_rate`), Rainfall Departure (`rainfall_departure`), Wholesale Inflation (`wpi_YoY`). |
| **Cross-Validation** | `ml/train.py` | 5-fold expanding-window **`TimeSeriesSplit(n_splits=5)`** with zero future lookahead. |
| **Baseline Models** | `ml/train.py` | **Naive Persistence Baseline** (`lag_1`), **Moving Average** (`rolling_mean_6m`), **SARIMA** (`order=(1,1,1), seasonal_order=(0,0,0,0)`). |
| **Random Forest Parameters**| `ml/train.py` | `n_estimators=80`, `max_depth=4`, `min_samples_leaf=3`, `max_features="sqrt"`, `random_state=42`. |
| **XGBoost CV Parameters** | `ml/train.py` | `n_estimators=75`, `max_depth=3`, `learning_rate=0.06`, `reg_lambda=2.0`, `reg_alpha=0.5`, `subsample=0.85`, `colsample_bytree=0.85`, `random_state=42`. |
| **XGBoost Final Production**| `ml/train.py` | `n_estimators=90`, `max_depth=3`, `learning_rate=0.05`, `reg_lambda=2.0`, `reg_alpha=0.5`, `subsample=0.85`, `colsample_bytree=0.85`, `random_state=42`. |
| **Explainability** | `ml/explain.py` | **Feature importance** scores from trained trees; `shap` is neither imported nor in dependencies. |
| **Debt-to-Income (DTI)** | `planner/loans.py` | **Safe**: `<= 30.0%`, **Watch**: `30.0% < DTI <= 45.0%`, **At Risk**: `> 45.0%`. |
| **Housing / Rent Ceiling** | `planner/reduction.py` | Flagged if rent/housing exceeds **32.0% of monthly income** and is greater than **₹15,000/month**. |
| **Peer Rent Benchmarks** | `planner/savings.py` | MoSPI city-tier benchmarks: Metro (Tier-1) **28.0%**, Tier-2/3 **20.0%**, Semi-Urban/Rural **12.0%**. |
| **Emergency Fund Rules** | `planner/emergency.py` | **3 months** for dual stable salaried earners; **6 months** for single earner, variable/gig income, or chronic health dependents. Strictly liquid assets (savings + FDs). |
| **Budget Split Benchmark** | `core/expense_service.py`| Needs (~50%), Wants (~30%), Savings (~20%). Flagged if Needs exceed 60%. |
| **Authentication Security**| `core/auth.py` | `bcrypt` (12 rounds); strength requires min 8 chars, >= 1 letter, >= 1 number. |
| **Brute-Force Lockout** | `core/auth.py` | **5 consecutive failed attempts** (`MAX_FAILED_ATTEMPTS = 5`), lockout duration: **15 minutes** (`LOCKOUT_DURATION_MINUTES = 15`). |
| **Session Inactivity** | `core/auth.py` | **20-minute rolling timeout** (`SESSION_TIMEOUT_MINUTES = 20`). |
| **Password Reset Token** | `core/auth.py` | 32-character token expiring in **30 minutes** (`RESET_TOKEN_EXPIRY_MINUTES = 30`), single-use SHA-256 hashed. |
| **Aether Design Tokens** | `app/styles.py` | Background: `#F5F7FA`, Card: `#FFFFFF`, Primary Accent: `#6C63FF`, Secondary Accent: `#8B83FF`, Soft Purple: `#EFEDFF`, Text: `#202334`, Muted Text: `#73788C`, Border: `#E9EAF0`, Success: `#20B486`, Warning: `#F4B740`, Danger: `#EF6461`. |
| **Automated Test Count** | `tests/` | Exactly **29 tests** across 6 test modules, 100% passing. |

---

## 2. Real Printed Benchmark Leaderboard (`python scripts/train_models.py`)

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

---

## 3. Discrepancies in Old README / Docs (Not Supported by Real Code)

1. **Prediction Interval Level**:
   - *Old Claim*: "95% Confidence Intervals".
   - *Code Reality*: `compute_prediction_intervals(..., confidence_level=0.80)` computes **80% prediction intervals**.
2. **Page Count & Removed Modules**:
   - *Old Claim*: "12 pages" / 13 numbered pages including Inflation Trends, Chat Assistant, User Guide, and Admin.
   - *Code Reality*: Project was deliberately simplified to **8 pages** (`1_My_Profile.py` through `8_Reports.py`) with `Login.py` as entrypoint.
3. **SHAP Claims**:
   - *Old Claim*: "SHAP (SHapley Additive exPlanations) values quantifying impact".
   - *Code Reality*: `shap` is neither imported nor installed in `requirements.txt`. The code computes standard tree `feature_importances_`.
4. **Data Source Transparency**:
   - *Old Claim*: Implied live MoSPI official feeds.
   - *Code Reality*: The project uses a calibrated synthetic monthly dataset (142 observations, 2015–2026) calibrated against Indian historical averages.
5. **Autoregressive Lags**:
   - *Old Claim*: "Lags (1, 2, 3, 6, 12)".
   - *Code Reality*: `ml/features.py` calculates lags `1, 2, 3, 12` (lag 6 is not in the lag loop; 6m is only a rolling window).
6. **Hardcoded Passwords & Admin Seeding**:
   - *Old Claim*: Published admin and demo credentials (`admin@parivararth.in` / `AdminMasterPass999`, etc.).
   - *Code Reality*: Admin seeding has been completely removed. No passwords are published; new users register securely on the Sign In page.
7. **Streamlit Version**:
   - *Old Claim*: Badge displayed `streamlit-1.30+`.
   - *Code Reality*: `requirements.txt` specifies `streamlit>=1.35.0`.
8. **Git Clone URL**:
   - *Old Claim*: `https://github.com/your-username/parivar_arth.git`.
   - *Code Reality*: Correct repository URL is `https://github.com/arsalan269/parivar-arth.git`.
