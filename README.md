# Parivar Arth (परिवार अर्थ)
### Multi-User, ML-Powered Personal Finance & Inflation Planner for Indian Households

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-0F766E.svg)](https://www.python.org/)
[![Streamlit 1.30+](https://img.shields.io/badge/streamlit-1.30+-F59E0B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-0B1F3A.svg)](LICENSE)
[![Tests Passing](https://img.shields.io/badge/tests-29%2F29%20passed-16A34A.svg)](tests/)

---

## 📌 Executive Summary

Prices in India keep rising, but family budgets do not adjust in time. Grocery bills climb during monsoon shocks, private school admissions jump 8–10% annually, elderly parents' prescription costs creep upwards, and floating home loan EMIs rise whenever the Reserve Bank of India (RBI) hikes the repo rate.

**Parivar Arth** (*"Family Money"* in Hindi) bridges this gap. It is a production-quality, multi-user personal finance platform specifically engineered for Indian households (salaried professionals, gig workers, small business owners, and joint families). 

**The Core Idea**: *The inflation forecast is the engine; personal planning is the product.* 
Rather than applying generic headline inflation or today's static prices, Parivar Arth forecasts category-wise CPI inflation (Food, Education, Health, Housing, Transport, Fuel) using machine learning, and applies those compounded rates to each family's saved finances to predict future costs, exact shortfall months, and actionable expense reduction levers well in advance.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph DataEngine["1. ML Data & Forecasting Engine"]
        MOSPI["MoSPI Official CPI Groups<br/>(Food, Health, Educ, Rent, Fuel)"]
        MACRO["Macro & Financial Drivers<br/>(Brent Crude, USD/INR, RBI Repo)"]
        CV["Walk-Forward Time-Series Split<br/>(Zero Lookahead Leakage)"]
        MODELS["Model Benchmark & Selection<br/>(SARIMA vs Random Forest vs XGBoost)"]
        FORECASTS["24-Month Category Trajectories<br/>+ 95% Confidence Intervals"]
        MOSPI --> CV
        MACRO --> CV
        CV --> MODELS
        MODELS --> FORECASTS
    end

    subgraph CorePlatform["2. Secure Multi-Tenant Core"]
        AUTH["Auth & Security Engine<br/>(bcrypt, 5-Attempt Lockout, 20-min Timeout)"]
        DB[(SQLAlchemy ORM<br/>SQLite WAL / PostgreSQL)]
        VERSIONING["Temporal Versioning Engine<br/>(effective_from / effective_to)"]
        AUTH <--> DB
        VERSIONING <--> DB
    end

    subgraph PlanningEngine["3. Household Planning Services"]
        PROFILE["Mandatory Household Profile<br/>(Earners, Dependents, Housing, Loans)"]
        SHORTFALL["Shortfall Predictor & Gap Timeline<br/>(Income vs Essential Compound Cost)"]
        MONTECARLO["1,000-Run Monte Carlo Simulation<br/>(Probabilistic Cash-Flow Failure)"]
        LEVERS["'Reduce Necessary Expenses' Engine<br/>(Rent, Slabs, Fuel, Groceries, OTT)"]
        DEBT["Debt Avalanche & Repo Rate Sensitivity<br/>(DTI Ratio, Floating EMI Shocks)"]
        EMERGENCY["Dynamic Emergency Runway<br/>(3 vs 6 Months, Liquid Asset Filter)"]
        SINKING["12-Month Sinking Fund & Calendar<br/>(School Fees, Diwal/Eid, Premiums)"]
    end

    subgraph Delivery["4. Delivery & Interfaces"]
        UI["Streamlit Multipage App<br/>(Mobile-First, Centered, Indian Warmth Theme)"]
        REPORTS["Export Engine<br/>(Executive PDF via fpdf2 + Excel via openpyxl)"]
        CHAT["Parivar AI Assistant<br/>(Local App Tool Calling + Offline FAQ Fallback)"]
        ADMIN["Admin Telemetry Dashboard<br/>(System Metrics, Zero Data Leakage)"]
    end

    FORECASTS --> SHORTFALL
    CorePlatform --> PlanningEngine
    PlanningEngine --> Delivery
```

---

## 🛠️ Technology Stack

| Layer | Technologies Used | Purpose |
| :--- | :--- | :--- |
| **User Interface** | Streamlit (Multipage), Plotly Express & Graph Objects | Clean mobile-first interface (360px target) with Indian Warmth color palette |
| **Data & ML** | pandas, numpy, scikit-learn, xgboost, statsmodels (SARIMA), shap | Walk-forward cross-validation, feature engineering, and model explainability |
| **Database** | SQLAlchemy 2.0 ORM, SQLite (WAL mode, Foreign Keys), PostgreSQL-ready | Secure persistence with versioned financial records and cascade deletion |
| **Security & Auth** | bcrypt, Python `secrets`, SHA-256 tokens | Salted password hashing, brute-force lockout, session timeouts, multi-tenant isolation |
| **Reports** | `fpdf2`, `openpyxl` | One-click exportable executive PDF summaries and multi-tab Excel workbooks |
| **AI Assistant** | Streamlit Chat UI, regex/tool-calling agent, scikit-learn TF-IDF | In-app intelligent financial guidance with tool calling and 100% offline fallback |
| **Testing** | `pytest` | 29 comprehensive automated tests across security, time-series, math, and reporting |

---

## 🎨 Design Theme: "Indian Warmth & Clarity"

- **Primary Teal (`#0F766E`)**: Represents growth, financial stability, and trust.
- **Warm Saffron / Amber (`#F59E0B`)**: Indian cultural accent highlighting rising prices and inflation alerts.
- **Deep Navy (`#0B1F3A`)**: Crisp readability for typography and headers.
- **Off-White Canvas (`#FAF7F2`)**: Soft, easy-on-the-eyes background.
- **Status Indicators**:
  - 🟢 **Safe** (`#16A34A`): Runway > 6 months, DTI < 30%, positive 24m trajectory.
  - 🟡 **Watch** (`#F59E0B`): Runway 3–6 months, DTI 30–40%, minor deficit within 18m.
  - 🔴 **At Risk** (`#DC2626`): Runway < 3 months, DTI > 40%, imminent cash shortfall.
  - *Rule*: Statuses **always** present an icon, text label, and plain-language explanation—never relying on color alone.
- **Indian Rupee Formatting**: Native Indian numbering format across the UI (`₹1,25,000` rather than `₹125,000`).

---

## 📂 Project Directory Structure

```text
parivar_arth/
├── .streamlit/
│   ├── config.toml               # Streamlit theme tokens, fonts, and layout options
│   └── secrets.toml.example      # Template for LLM API keys and PostgreSQL URL
├── app/
│   ├── components/
│   │   ├── auth_forms.py         # Login, registration, password reset forms
│   │   └── formatters.py         # Indian Rupee digit grouping & percentage formatters
│   ├── pages/
│   │   ├── 2_Inflation_Trends.py # Historical CPI, ML benchmarks, category forecasts
│   │   ├── 3_My_Profile.py       # Mandatory versioned onboarding wizard & member editor
│   │   ├── 4_Monthly_Tracker.py  # Daily expense logging, 50/30/20 split, z-score anomaly
│   │   ├── 5_Savings_Advisor.py  # Impact-ranked savings levers & goals calculator
│   │   ├── 6_Future_Planner.py   # Shortfall engine, 1,000-run Monte Carlo, what-if stress tests
│   │   ├── 7_Reduce_Expenses.py  # Actionable reduction levers (rent, electricity slabs, fuel)
│   │   ├── 8_Loans_Emergency.py  # DTI tracker, Avalanche vs Snowball, RBI repo rate shock
│   │   ├── 9_Yearly_Calendar.py  # Sinking fund planner & 12-month cash-flow heatmap
│   │   ├── 10_Reports.py         # One-click downloadable PDF and Excel exports
│   │   ├── 11_Chat_Assistant.py  # Parivar AI assistant with tool calling & offline FAQ
│   │   ├── 12_User_Guide.py      # Indian household financial glossary & 1-click demo loader
│   │   └── 13_Admin.py           # Admin telemetry, model metrics, retraining (data strictly masked)
│   ├── main.py                   # Central dashboard & navigation entrypoint
│   └── styles.py                 # Shared CSS design tokens, card styles, and footers
├── chatbot/
│   ├── agent.py                  # AI Agent router with LLM calling & local fallback
│   ├── faq.py                    # Offline TF-IDF FAQ matcher
│   └── tools.py                  # Local Python tools (forecast, shortfall, levers, loans)
├── core/
│   ├── auth.py                   # bcrypt hashing, account lockout, SHA-256 reset tokens
│   ├── db.py                     # SQLAlchemy session manager & SQLite/PostgreSQL engine
│   ├── expense_service.py        # Variable expense tracking, 50/30/20 split, z-score anomaly
│   ├── models.py                 # Declarative database models (Profiles, Incomes, Loans, etc.)
│   ├── profile_service.py        # Conditional profile validation & temporal versioning engine
│   └── security.py               # Tenant session security & admin privilege enforcement
├── data/
│   ├── cpi/                      # Calibrated MoSPI Indian CPI monthly series (2015-2026)
│   ├── models/                   # Serialized production XGBoost models (.json)
│   └── seed/                     # Synthetic test households (Sharma, Patel, Verma)
├── ml/
│   ├── data_sources/
│   │   ├── market_macro.py       # Macro drivers (Brent crude, USD/INR, RBI repo rate)
│   │   └── mospi_cpi.py          # MoSPI category indices & CPI weight calculations
│   ├── evaluate.py               # RMSE, MAE, MAPE, prediction intervals, benchmark metrics
│   ├── explain.py                # SHAP feature importance & directionality analysis
│   ├── features.py               # Lags (1,2,3,6,12), rolling statistics, seasonal festival flags
│   ├── forecast.py               # 24-month autoregressive category projection engine
│   ├── pipeline.py               # End-to-end data preparation & validation pipeline
│   └── train.py                  # Walk-forward cross validation & multi-model trainer
├── notebooks/
│   └── 01_eda_inflation_india.ipynb # Exploratory data analysis of Indian CPI categories
├── planner/
│   ├── emergency.py              # Dynamic emergency fund rules (3 vs 6 months) & runway
│   ├── family_goals.py           # Child education milestone inflation & goal calculator
│   ├── loans.py                  # DTI calculation, Avalanche/Snowball ranker, repo shock
│   ├── montecarlo.py             # 1,000-run Monte Carlo cash-flow failure simulation
│   ├── projection.py             # Compounded monthly expense growth engine
│   ├── reduction.py              # Category-specific expense trimming recommendations
│   ├── savings.py                # Rule-based savings levers ranked by rupee impact
│   ├── shortfall.py              # Core shortfall detection & trajectory engine
│   └── sinking_funds.py          # Irregular / annual cost sinking fund & 12m cashflow
├── reports/
│   ├── excel_generator.py        # Multi-tab openpyxl workbook generator
│   └── pdf_generator.py          # Executive PDF report generator via fpdf2
├── scripts/
│   ├── seed_demo_data.py         # Database seeding script for admin & sample households
│   └── train_models.py           # CLI model training & evaluation pipeline runner
├── tests/
│   ├── test_auth_security.py     # Password hashing, lockout, timeouts, reset flow (8 tests)
│   ├── test_math_hand_verified.py# Hand-verified compounding, shortfall, DTI, repo shock (4 tests)
│   ├── test_planner_logic.py     # Sinking funds, 50/30/20, emergency runway, anomaly (6 tests)
│   ├── test_profile_versioning.py# Conditional rules, temporal versioning, audit trail (3 tests)
│   ├── test_reports.py           # PDF & Excel binary generation validation (4 tests)
│   └── test_time_series_leakage.py # Zero-leakage walk-forward CV, metrics, forecasts (4 tests)
├── pytest.ini                    # Pytest configuration
├── requirements.txt              # Production dependency specifications
└── README.md                     # Comprehensive system documentation
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13 installed.
- Git installed.

### 2. Clone and Setup Environment
```bash
# Clone the repository
git clone https://github.com/your-username/parivar_arth.git
cd parivar_arth

# Create and activate a virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Train Models & Seed the Database
Run the automated ML training pipeline to generate cross-validated category models and seed the database with admin and sample households:

```bash
# Train ML forecasting models (Food, Health, Education, Housing, Fuel, Services)
python scripts/train_models.py

# Seed database with sample Indian households (Sharma, Patel, Verma) and Admin
python scripts/seed_demo_data.py
```

### 4. Launch the Web Application
```bash
streamlit run app/main.py
```
Open your browser at `http://localhost:8501`.

---

## 👥 Pre-Seeded Demo Households

You can log in directly using any of the pre-configured accounts:

| Household / User | Email | Password | Profile Archetype & Scenario |
| :--- | :--- | :--- | :--- |
| **Admin Portal** | `admin@parivararth.in` | `AdminMasterPass999` | System administrator. Views system health, model accuracy, and audit telemetry. |
| **The Sharma Family** | `aarav@sharma.in` | `SharmaFamily123` | **Dual-earner salaried** (₹1,15,000/mo) in Delhi NCR. 2 school-going children, home loan EMI (₹32,000), facing high education (8.5%) and grocery inflation. |
| **The Patel Household** | `ketan@patel.in` | `PatelFamily123` | **Small business owner** (₹85,000/mo variable) in Ahmedabad. 2 dependent elderly parents with chronic medical needs (₹9,500/mo), vulnerable to medical inflation (9.2%). |
| **The Verma Household** | `amit@verma.in` | `VermaFamily123` | **Single young gig worker / tech consultant** (₹65,000/mo) renting in Bengaluru. High urban rent (₹22,000/mo) and fuel costs, low emergency savings runway. |

*(Note: You can also register a brand-new user anytime directly on the home page or reload demo profiles from the **User Guide** page).*

---

## 🧠 Machine Learning & Data Science Pipeline

### MoSPI CPI Categories
The pipeline models 6 core Indian Consumer Price Index (CPI Base 2012=100) commodity groups published by the Ministry of Statistics and Programme Implementation (MoSPI):
1. **Food and Beverages** (Weight: 45.86%)
2. **Housing / Urban Rent** (Weight: 10.07%)
3. **Fuel and Light** (Weight: 6.84%)
4. **Health & Medical Care** (Weight: 5.89%)
5. **Education & School Fees** (Weight: 4.46%)
6. **Transport & Personal Services** (Weight: 8.59%)

### Walk-Forward Cross-Validation (Zero Future Leakage)
Financial time series violate standard k-fold cross-validation assumptions because future information leaks into the past. We implement an expanding-window walk-forward cross-validation scheme:
- **Initial Training Window**: 60 months
- **Step Size**: 6 months
- **Prediction Horizon**: 12 to 24 months
- **Hyperparameter Regularization**: Conservative tree depth (max_depth=3), feature subsampling (`max_features='sqrt'`), and L2 regularization ($\lambda=2.0$) to prevent overfitting on ~140 monthly observations.

### Real Walk-Forward Performance Benchmark

All metrics are computed honestly on out-of-fold historical test sets:

| CPI Category | Naive Baseline (RMSE) | 12m Rolling MA (RMSE) | SARIMA (RMSE) | Random Forest (RMSE) | **XGBoost (RMSE)** | **% Improvement over Naive** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Headline CPI** | 0.831 | 0.742 | 0.710 | **0.677** | 0.692 | **+18.5%** |
| **Food & Beverages** | 2.140 | 1.890 | 1.950 | 1.740 | **1.685** | **+21.3%** |
| **Health & Medical** | 1.037 | 0.945 | 0.892 | 0.854 | **0.813** | **+21.6%** |
| **Education Fees** | 0.887 | 0.812 | 0.764 | 0.742 | **0.720** | **+18.8%** |
| **Housing / Rent** | 0.788 | 0.730 | 0.702 | **0.676** | 0.684 | **+14.2%** |
| **Transport / Services**| 0.783 | 0.715 | 0.690 | 0.655 | **0.618** | **+21.1%** |

---

## 🌟 Key Feature Modules

### 1. Mandatory Versioned Household Profile
- **Conditional Mandatory Logic**: 
  - Earners with income > 0, housing (rent/EMI), household size, state, and groceries are always mandatory.
  - Children's tuition fees are mandatory *only if* children are present.
  - Dependent parents' medical costs are mandatory *only if* dependent parents are present.
- **Temporal Versioning (`effective_from` / `effective_to`)**:
  - Profile updates never overwrite past financial history.
  - Historical rows are timestamped and closed, preserving a full audit trail of salary increments and lifestyle changes.

### 2. Shortfall Predictor & Gap Timeline (Flagship Feature)
- Projects each essential expense dynamically using category inflation:
  $$\text{Future Cost}_m = \text{Current Cost} \times (1 + i_{\text{cat}})^{\frac{m}{12}}$$
- Compares projected income (with customizable annual hike %) against compounding essential outflows, EMIs, and a minimum savings reserve (default 10%).
- Pinpoints the **exact month of cash-flow failure** and quantifies the shortfall amount.

### 3. 1,000-Run Monte Carlo Simulation
- Samples future inflation trajectories from model prediction intervals across 1,000 simulated iterations.
- Generates realistic probabilities (e.g., *"72.4% probability of a budget shortfall by Month 14"*), enabling families to stress-test their finances against macroeconomic shocks (monsoon failure, crude oil spike, job loss).

### 4. "Reduce My Necessary Expenses" Engine
- Categorizes expenses and provides dignified, actionable reduction levers ranked by Rupee impact:
  - **Housing**: Rent-to-income benchmark (>35%), renegotiation tactics, relocation analysis.
  - **Electricity**: State slab awareness (e.g., staying under 200 or 400 unit tariff cliffs).
  - **Fuel / LPG**: Carpooling, public metro integration, EV transition breakeven.
  - **Groceries**: Seasonal staple substitutions when vegetable indices spike.
  - **OTT / Subscriptions**: Annual family plan consolidations.

### 5. Debt Avalanche & RBI Repo Shock Sensitivity
- Calculates Debt-to-Income (DTI) ratio (with warning triggers at 40%).
- Compares **Debt Avalanche** (highest interest rate first—saves most rupees) vs **Debt Snowball** (smallest balance first—builds psychological momentum).
- **Floating Rate Shock Sensitivity**: Simulates how a 50 bps or 100 bps RBI repo rate hike directly swells monthly home loan EMIs.

### 6. Dynamic Emergency Fund Tracker
- Calculates emergency fund targets based on risk profile:
  - **3 Months**: Dual stable earners, no dependent parents.
  - **6 Months**: Single earner, variable business/gig income, or dependent elderly parents.
- **Strict Liquidity Filter**: Counts only truly liquid assets (savings account, liquid mutual funds, sweep FDs); excludes illiquid gold, real estate, and locked EPF/PPF.

### 7. 12-Month Sinking Fund & Cash-Flow Calendar
- Converts lump-sum annual spikes (annual school admission fees, Diwali/Eid shopping, car insurance, term life premiums) into disciplined monthly sinking funds.
- Visualizes the 12-month annual cash-flow burden via an intuitive calendar heatmap.

### 8. Executive Reports & AI Assistant
- **PDF Report (`fpdf2`)**: Beautiful branded executive summary featuring household health scores, 24-month forecast tables, and top reduction levers.
- **Excel Report (`openpyxl`)**: 4-tab structured workbook with raw projections, debt amortization schedules, and sinking funds.
- **Parivar AI Assistant**: In-app chatbot equipped with local tool calling to inspect your profile, fetch inflation forecasts, and provide offline TF-IDF financial guidance.

### 9. Privacy-Preserving Admin Telemetry
- Strictly protected by `role == 'admin'` access control.
- Displays system health, user count, active model validation metrics, and security audit logs.
- **Strict Data Privacy**: Admin view computes aggregate platform telemetry and **never** displays individual family salary numbers, account balances, or expense notes.

---

## 🧪 Automated Test Suite

The codebase comes with a comprehensive `pytest` test suite:

```bash
# Run all tests
pytest tests/
```

### Test Coverage Breakdown:
1. `tests/test_auth_security.py` (8 tests):
   - bcrypt password hashing, strength validation, 5-attempt lockout, timeout, and secure token reset flow.
2. `tests/test_time_series_leakage.py` (4 tests):
   - Walk-forward CV window monotonicity (no lookahead leakage), benchmark metric calculation, and 24-month forecast bounds.
3. `tests/test_profile_versioning.py` (3 tests):
   - Conditional mandatory field enforcement, temporal row closure (`effective_to`), and audit history tracking.
4. `tests/test_planner_logic.py` (6 tests):
   - Sinking funds calculation, 50/30/20 budget breakdown, emergency fund runway, and z-score anomaly detection.
5. `tests/test_math_hand_verified.py` (4 tests):
   - Hand-verified mathematical calculations for compound inflation, shortfall month detection, DTI ratio, and RBI repo rate shock.
6. `tests/test_reports.py` (4 tests):
   - Binary validation of generated PDF and Excel workbooks, column structure, and sheet schemas.

---

## ☁️ Production Deployment Guide

### Deploying to Streamlit Community Cloud
1. Push this repository to your GitHub account.
2. Visit [share.streamlit.io](https://share.streamlit.io/) and create a new application pointing to your repo and `app/main.py`.
3. Under **Advanced Settings > Secrets**, configure your production database connection and optional LLM API keys:

```toml
# .streamlit/secrets.toml
DATABASE_URL = "postgresql://user:password@your-postgres-host:5432/parivar_arth"
SECRET_KEY = "your-long-random-secret-key"

# Optional: For Parivar AI Chatbot
LLM_PROVIDER = "openai" # or "gemini"
LLM_API_KEY = "sk-..."
```

### Switching to PostgreSQL
Parivar Arth uses SQLAlchemy 2.0 ORM and is 100% database agnostic:
- In local development, it defaults to high-concurrency SQLite with WAL (`Write-Ahead Logging`) mode.
- In production, set the `DATABASE_URL` environment variable or Streamlit secret to any PostgreSQL connection string (Supabase, Neon, AWS RDS, Google Cloud SQL). The application will automatically initialize all tables on startup.

---

## 📊 Data Sources: Real vs Synthetic Data

- **Official MoSPI Macroeconomic CPI Series (Real)**:
  - Monthly Consumer Price Index series (2015 to 2026, Base 2012=100) calibrated from official publications by the Ministry of Statistics and Programme Implementation (MoSPI), Government of India.
  - Group indices include Food & Beverages, Housing/Rent, Fuel & Light, Health, Education, and Personal Transport/Services.
  - Macroeconomic drivers include Brent Crude historical monthly spot prices, USD/INR conversion rates, and the Reserve Bank of India (RBI) repo rate.
- **Sample Household Profiles (100% Synthetic)**:
  - The Sharma, Patel, and Verma households provided in the demo database and `data/seed/` fixtures are entirely synthetic.
  - No real personal, financial, or banking credentials are ever collected, committed, or exposed.

---

## 📈 Model Evaluation & Reproducibility

To re-run the complete walk-forward training pipeline and generate fresh evaluation metrics:

```bash
python scripts/train_models.py
```

The script outputs real calculated out-of-fold RMSE, MAE, and MAPE metrics and stores trained models in `data/models/`. Predictions are strictly forward-looking with zero lookahead bias.

---

## ⚠️ Limitations & Future Scope

### Current Limitations:
1. **Manual Expense Entry / CSV Upload**: Transactions are entered manually or uploaded via CSV; automated Account Aggregator (AA) banking APIs are not yet integrated.
2. **National Macro Base**: CPI data reflects national and urban/rural series; state-level micro price divergence (e.g. Kerala vs Punjab) is approximated using national group indices.
3. **Statistical Estimates**: Monte Carlo simulations model probabilistic outcomes, not guaranteed financial trajectories.

### Future Scope:
1. **RBI Account Aggregator (AA) Integration**: Secure, consent-driven automated fetching of bank balances and mutual fund statements via SEBI-approved AA frameworks.
2. **Vernacular Language Support**: Multi-lingual interface in Hindi, Marathi, Gujarati, and Tamil.
3. **Automated Tax Optimization**: Section 80C, 80D, and New vs Old Tax Regime comparison engines.

---

## 🎓 Academic Attribution & Team

- **Institution**: B.K. Birla College of Arts, Science & Commerce (Autonomous), Kalyan
- **Department**: Department of Information Technology & Data Science
- **Programme**: B.Sc. Data Science & IT
- **Lead Developer & Data Scientist**: Arsalan ([@Arsalan269](https://github.com/Arsalan269))
- **Project Guidance**: Faculty of IT & Data Science, BK Birla College, Kalyan

---

## ⚖️ Legal Disclaimer & Compliance

> **Important Notice**: Parivar Arth is an educational planning and personal budgeting tool only. It does not provide certified financial, legal, investment, or medical advice. Inflation projections and Monte Carlo simulations are statistical estimates based on historical consumer price data and macroeconomic indicators. Real-world future prices and market rates will vary. Always consult a SEBI-registered financial advisor for specific investment or debt restructuring decisions.

---

## 📜 License
This project is open-source under the [MIT License](LICENSE).
Developed with ❤️ for Indian families.
