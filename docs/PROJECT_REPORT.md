# Parivar Arth (Family Money Planner) — Project Documentation
## BK Birla College of Arts, Science & Commerce (Autonomous), Kalyan
### Department of Information Technology & Data Science
**Programme**: B.Sc. Data Science & IT  
**Academic Year**: 2025–2026  
**Project Title**: Parivar Arth — Multi-User ML-Powered Personal Finance & Category Inflation Planner for Indian Households  
**Author / Developer**: Arsalan ([@Arsalan269](https://github.com/Arsalan269))

---

## 1. Project Abstract & Core Idea
Prices in India rise persistently across distinct commodity baskets (food, education, healthcare, fuel, rent). Traditional personal finance applications either treat prices as static or apply a single, uniform headline inflation rate across all budget items. In reality, private school tuition fees in India rise at 8–10% annually, healthcare expenses outpace CPI at 9–12%, and food items carry extreme seasonal volatility.

**Parivar Arth** introduces an inflation-aware budgeting paradigm:
1. **The Engine**: Machine Learning models (SARIMA, Random Forest, XGBoost) trained on calibrated Indian Consumer Price Index (CPI Base 2012=100) commodity series forecast category-wise inflation 24 months forward with 80% prediction intervals. *Note: CPI time-series data is a calibrated synthetic fallback aligned with historical Indian economic averages (2015–2026), not live MoSPI streaming feeds; forecasts are statistical estimates.*
2. **The Product**: These compounded rates are mapped directly onto each registered family's financial obligations (school fees, chronic medicine, EMIs, grocery estimates, sinking funds) to project the exact month of cash-flow distress, calculate dynamic emergency fund runways, and recommend rupee-ranked reduction levers.

---

## 2. Key Modules & Technical Implementation

### A. Authentication & Multi-Tenant Data Security
- **Salted Password Hashing**: Implemented using `bcrypt` (12 rounds) with strength validation (minimum 8 characters, letters and digits).
- **Brute-Force Lockout**: Automatically locks an account for 15 minutes after 5 consecutive failed attempts.
- **Session Expiry**: 20-minute rolling inactivity timeout via `touch_session()`.
- **Password Reset**: Secure one-time 32-character tokens hashed with SHA-256 expiring in 30 minutes.
- **Multi-Tenant Isolation**: Every database query filters strictly by `user_id` stored in session state, eliminating IDOR vulnerabilities.
- **Cascade Deletion**: Supports user account deletion with `ON DELETE CASCADE` across all relational tables.

### B. Machine Learning Pipeline & Zero Lookahead Validation
- **Data Basket**: Calibrated commodity groups aligned with MoSPI CPI All-India groups:
  1. Headline CPI
  2. Food and Beverages
  3. Housing
  4. Fuel and Light
  5. Transport and Communication
  6. Health
  7. Education
  8. Miscellaneous Services
- **Validation**: 5-fold expanding-window `TimeSeriesSplit` (strictly backward-looking features with zero lookahead leakage).
- **Feature Engineering**: Autoregressive lags (t-1, t-2, t-3, t-12), rolling statistics (3m and 6m mean and standard deviation), 12m base effect, seasonal calendar dummies (Monsoon, Festival, School admission), and lagged exogenous macro drivers (Crude in INR, USD/INR, RBI repo rate, Rainfall departure, WPI).
- **Prediction Uncertainty**: Residual-based 80% prediction intervals (`compute_prediction_intervals`, confidence level 0.80).
- **Explainability**: Technical feature importance scores translated into plain-language economic summaries (`ml/explain.py`).

### C. Household Financial Planning Engines
- **Shortfall Predictor**: Projects compounded essential expenses over 24 months against income adjusted for annual salary increments (`planner/shortfall.py`).
- **1,000-Run Monte Carlo Simulation**: Stochastically samples future inflation from model prediction intervals to calculate the empirical probability of a cash-flow gap (`planner/montecarlo.py`).
- **Debt Optimization**: Debt-to-Income (DTI) tracker (Safe <= 30%, Watch 30–45%, At Risk > 45%), comparison of **Debt Avalanche** (APR-prioritized) vs **Debt Snowball** (balance-prioritized), and floating-rate sensitivity to RBI repo rate hikes (`planner/loans.py`).
- **Dynamic Emergency Fund**: Computes 3 vs 6-month targets based on earner stability, gig income, and chronic illness dependencies; filters strictly for liquid cash assets (`planner/emergency.py`).
- **Expense Reduction Levers**: Surfaces actionable, dignified optimizations (rent ceiling > 32%, electricity slab tariffs, bulk staple purchases, fuel optimization) ranked by monthly rupee impact (`planner/reduction.py`).
- **Sinking Funds**: Smooths irregular annual expenses (school fees, festive travel, insurance premiums) into steady monthly reserves (`planner/sinking_funds.py`).

---

## 3. Application Pages (8 Streamlit Modules)

1. **Login.py**: Authentication gateway (Sign In, Register New Family, Password Reset) and authenticated financial health summary dashboard.
2. **1_My_Profile.py**: Mandatory household onboarding wizard, family composition, versioned expense editing (`effective_from` / `effective_to`), and chronological audit trail.
3. **2_Monthly_Tracker.py**: Daily expense logger, 50/30/20 Needs/Wants/Savings distribution, CSV statement import with auto-categorization, and personal z-score overspending anomaly detection.
4. **3_Savings_Advisor.py**: Prioritized savings levers ranked by rupee impact, MoSPI Household Consumption Expenditure Survey peer benchmarks, and inflation-adjusted goal calculator.
5. **4_Future_Planner.py**: Flagship 24-month shortfall timeline, 1,000-run Monte Carlo volatility simulation, what-if stress tests, and children's education milestones.
6. **5_Reduce_Expenses.py**: Practical expense reduction levers with interactive monthly cash flow reclaim simulator.
7. **6_Loans_Emergency.py**: Emergency runway tracker, liquid vs illiquid asset filtering, DTI health analysis, Avalanche vs Snowball debt payoff, and RBI repo rate shock modeling.
8. **7_Yearly_Calendar.py**: 12-month outflow calendar heatmap, heavy expenditure spike detection, and monthly sinking fund allocations.
9. **8_Reports.py**: Executive statement generation with one-click exportable PDF statements (`fpdf2`) and multi-tab Excel financial workbooks (`openpyxl`).

---

## 4. Presentation & Demonstration Outline (PPT Guide)
1. **Slide 1**: Title, Author, BK Birla College Kalyan, B.Sc. Data Science & IT.
2. **Slide 2**: Problem Statement — Why standard static budgets fail Indian families under category inflation.
3. **Slide 3**: The Innovation — ML category forecasting engine connected directly to personal family balance sheets.
4. **Slide 4**: System Architecture — Streamlit 8-page multipage app, Aether FinTech UI, SQLAlchemy 2.0 ORM, XGBoost, Plotly visualizations.
5. **Slide 5**: ML Model Performance & Walk-Forward Benchmark (XGBoost, Random Forest, SARIMA, Moving Average, Naive Baseline).
6. **Slide 6**: Live Platform Walkthrough — Onboarding wizard, 24-month shortfall timeline, Monte Carlo fan chart, and sinking funds.
7. **Slide 7**: Security & Ethics — bcrypt (12 rounds), 5-attempt brute-force lockout, multi-tenant session isolation, data privacy.
8. **Slide 8**: Conclusion & Summary — 29 automated tests passing with zero errors.
