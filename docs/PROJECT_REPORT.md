# Parivar Arth (Family Money Planner) — Project Documentation
## BK Birla College of Arts, Science & Commerce (Autonomous), Kalyan
### Department of Information Technology & Data Science
**Programme**: B.Sc. Data Science & IT  
**Academic Year**: 2025–2026  
**Project Title**: Parivar Arth (परिवार अर्थ) — Multi-User ML-Powered Personal Finance & Category Inflation Planner for Indian Households  
**Author / Developer**: Arsalan ([@Arsalan269](https://github.com/Arsalan269))

---

## 1. Project Abstract & Core Idea
Prices in India rise persistently across distinct commodity baskets (food, education, healthcare, fuel, rent). Traditional personal finance applications either treat prices as static or apply a single, uniform headline inflation rate across all budget items. In reality, private school tuition fees in India rise at 8–10% annually, healthcare expenses outpace CPI at 9–12%, and food items carry extreme seasonal volatility.

**Parivar Arth** introduces an inflation-aware budgeting paradigm:
1. **The Engine**: Machine Learning models (SARIMA, Random Forest, XGBoost) trained on official Ministry of Statistics and Programme Implementation (MoSPI) CPI indices forecast category-wise inflation 24 months forward.
2. **The Product**: These compounded rates are mapped directly onto each registered family's financial obligations (school fees, chronic medicine, EMIs, grocery estimates, sinking funds) to project the exact month of cash-flow distress, calculate dynamic emergency fund runways, and recommend rupee-ranked reduction levers.

---

## 2. Key Modules & Technical Implementation

### A. Authentication & Multi-Tenant Data Security
- **Salted Password Hashing**: Implemented using `bcrypt` (12 rounds).
- **Brute-Force Lockout**: Automatically locks an account for 15 minutes after 5 consecutive failed attempts.
- **Session Expiry**: 20-minute rolling inactivity timeout.
- **Multi-Tenant Isolation**: Every database query filters strictly by `user_id` stored in the server session (`st.session_state`), eliminating IDOR vulnerabilities.
- **Cascade Deletion**: Supports user account deletion with `ON DELETE CASCADE` across all relational tables.

### B. Machine Learning Pipeline & Zero Lookahead Validation
- **Data Basket**: 6 MoSPI Consumer Price Index (Base 2012=100) commodity groups:
  1. Food and Beverages (Weight: 45.86%)
  2. Housing / Urban Rent (Weight: 10.07%)
  3. Fuel and Light (Weight: 6.84%)
  4. Health & Medical Care (Weight: 5.89%)
  5. Education & Tuition (Weight: 4.46%)
  6. Transport & Personal Services (Weight: 8.59%)
- **Validation**: Expanding-window walk-forward cross validation (no future lookahead leakage).
- **Explainability**: SHAP (SHapley Additive exPlanations) values quantifying the impact of historical lags and macro drivers (Brent crude, USD/INR, RBI repo rate).

### C. Household Financial Planning Engines
- **Shortfall Predictor**: Projects compounded essential expenses over 24 months vs projected annual salary increments.
- **1,000-Run Monte Carlo Simulation**: Stochastically samples future inflation from model prediction intervals to calculate the empirical probability of a cash-flow gap.
- **Debt Optimization**: Debt-to-Income (DTI) tracker, comparison of **Debt Avalanche** (rate-prioritized) vs **Debt Snowball** (balance-prioritized), and floating-rate sensitivity to RBI repo rate hikes.
- **Dynamic Emergency Fund**: Computes 3 vs 6-month targets based on family structure and filters strictly for liquid cash assets.
- **Sinking Funds**: Smooths irregular annual expenses (Diwali/Eid festivals, school admission, insurance premiums) into steady monthly reserves.

---

## 3. Presentation & Demonstration Outline (PPT Guide)
1. **Slide 1**: Title, Author, BK Birla College Kalyan, B.Sc. Data Science & IT.
2. **Slide 2**: Problem Statement — Why standard 50/30/20 budgets fail Indian families under category inflation.
3. **Slide 3**: The Innovation — ML category forecasting engine connected to personal family balance sheets.
4. **Slide 4**: System Architecture — Streamlit multipage, SQLAlchemy ORM, XGBoost, Plotly charts.
5. **Slide 5**: ML Model Performance & Walk-Forward Benchmark (XGBoost vs RF vs SARIMA vs Naive).
6. **Slide 6**: Live Demo Walkthrough — The Sharma Family (Salaried), Patel Household (Business), Verma Household (Gig Worker).
7. **Slide 7**: Security & Ethics — bcrypt, brute-force defense, multi-tenant isolation, data privacy.
8. **Slide 8**: Conclusion & Future Scope (Bank statement open banking integration, vernacular language support).
