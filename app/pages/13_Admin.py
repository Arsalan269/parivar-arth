"""
System Administration & ML Performance Dashboard for Parivar Arth.
Visible strictly to role == 'admin'.
Enforces strict privacy: Admin NEVER sees individual household financial records.
"""

import os
import sys
import streamlit as st
import pandas as pd
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import get_db_session
from core.models import User, ModelRun, Forecast, AuditLog
from core.security import touch_session, get_current_user_id, is_admin_user
from ml.pipeline import build_unified_dataset
from ml.train import train_all_categories
from ml.forecast import generate_multi_period_forecasts, save_forecasts_to_db
from app.styles import apply_theme, render_header, render_footer, PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY


def show_admin_page():
    st.set_page_config(page_title="Admin Console - Parivar Arth", page_icon="⚙️", layout="centered")
    apply_theme()
    touch_session()

    # 1. Strict Role Guard
    if not is_admin_user():
        render_header(
            title="Access Restricted",
            subtitle="Administrator privileges required",
            icon="🔒"
        )
        st.error("⛔ 403 Forbidden: You do not have administrative privileges to access this console.")
        st.info("Log in as an administrator (e.g. `admin@parivararth.in`) to view system-level telemetry.")
        render_footer()
        st.stop()

    render_header(
        title="Admin System Telemetry",
        subtitle="System metrics, machine learning performance & security audit logs",
        icon="⚙️"
    )

    # Privacy Guarantee Banner
    st.markdown(
        f"""
        <div style="background-color: #FEF3C7; border-left: 4px solid {ACCENT_SAFFRON}; padding: 10px 14px; border-radius: 6px; font-size: 0.85rem; color: #78350F; margin-bottom: 1.25rem;">
            <strong>Privacy Enforcement:</strong> In accordance with Parivar Arth security specifications, 
            this dashboard displays <strong>system-level telemetry only</strong>. Individual household budgets, salaries, and transactions are completely masked.
        </div>
        """,
        unsafe_allow_html=True
    )

    with get_db_session() as db:
        user_count = db.query(User).count()
        model_runs = db.query(ModelRun).order_by(ModelRun.trained_at.desc()).all()
        forecasts = db.query(Forecast).all()
        audit_logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(50).all()

    tab_overview, tab_models, tab_audit, tab_actions = st.tabs([
        "📈 System Metrics",
        "🏆 Model Leaderboard",
        "🛡️ Audit Trail",
        "🔄 Model Retrain & Maintenance"
    ])

    # ---------------- TAB 1: SYSTEM METRICS ----------------
    with tab_overview:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Registered Households", user_count)
        with col2:
            st.metric("Active Published Forecasts", len(forecasts))
        with col3:
            last_train = model_runs[0].trained_at.strftime("%d %b %Y, %I:%M %p") if model_runs else "Never"
            st.metric("Last Model Retrain", last_train)

        st.markdown("#### 📊 Category Forecast Index Summary")
        if forecasts:
            df_fc = pd.DataFrame([{
                "Category": f.category,
                "Target Month": f.target_month.strftime("%b %Y"),
                "Expected Inflation (%)": f.predicted_inflation,
                "80% Lower CI (%)": f.lower_ci,
                "80% Upper CI (%)": f.upper_ci,
                "Model Version": f.model_version
            } for f in forecasts])
            st.dataframe(df_fc.head(24), use_container_width=True)
        else:
            st.warning("No forecasts currently in database.")

    # ---------------- TAB 2: MODEL PERFORMANCE ----------------
    with tab_models:
        st.markdown("#### 🏆 Out-of-Fold Model Leaderboard (Walk-Forward Validation)")
        st.caption("Real calculated metrics comparing Random Forest, XGBoost, and SARIMA against the Naive persistence baseline.")

        if model_runs:
            df_runs = pd.DataFrame([{
                "Category": r.target_category,
                "Model Selected": r.model_type,
                "RMSE": round(r.rmse, 3),
                "MAE": round(r.mae, 3),
                "Model MAPE": f"{r.mape:.1f}%",
                "Baseline MAPE": f"{r.baseline_mape:.1f}%",
                "Improvement vs Naive": f"{((1 - r.mape/r.baseline_mape)*100):.1f}%" if r.baseline_mape > 0 else "0.0%",
                "Version": r.version,
                "Trained At": r.trained_at.strftime("%d %b %H:%M")
            } for r in model_runs])
            st.dataframe(df_runs, use_container_width=True)
        else:
            st.info("No recorded model runs found. Use the 'Model Retrain' tab to initiate training.")

    # ---------------- TAB 3: AUDIT TRAIL ----------------
    with tab_audit:
        st.markdown("#### 🛡️ Security & Lifecycle Audit Log")
        st.caption("Chronological record of account events (logins, lockouts, registrations, deletions).")

        if audit_logs:
            df_audit = pd.DataFrame([{
                "Timestamp": a.timestamp.strftime("%d %b %Y, %H:%M:%S"),
                "Actor": a.actor,
                "Action": a.action,
                "Details": a.details
            } for a in audit_logs])
            st.dataframe(df_audit, use_container_width=True)
        else:
            st.info("No audit logs recorded.")

    # ---------------- TAB 4: ACTIONS ----------------
    with tab_actions:
        st.markdown("#### 🔄 Trigger Automated Pipeline & Model Retrain")
        st.markdown(
            """
            This action will:
            1. Pull recent macro series from the data pipeline
            2. Re-execute walk-forward time-series splits
            3. Train regularized Random Forest and XGBoost models
            4. Re-populate the 24-month `forecasts` table with updated prediction intervals
            """
        )

        if st.button("🚀 Re-Run ML Training & Refresh Forecasts", type="primary"):
            with st.spinner("Executing pipeline and training walk-forward models across 8 categories..."):
                try:
                    df, meta = build_unified_dataset()
                    results = train_all_categories(df)
                    fc_records = generate_multi_period_forecasts(results, df, horizon_months=24)
                    save_forecasts_to_db(fc_records)
                    st.success("✅ Machine Learning Pipeline and 24-Month Forecasts refreshed successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error during training pipeline: {e}")

    render_footer()


if __name__ == "__main__":
    show_admin_page()
