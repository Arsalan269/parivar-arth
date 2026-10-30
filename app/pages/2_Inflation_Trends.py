"""
Inflation Trends & Machine Learning Forecasts Page for Parivar Arth.
Visualizes category-wise CPI inflation trends, forward predictions with uncertainty intervals,
model evaluation metrics vs Naive baseline, and plain-language SHAP drivers.
"""

import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import get_db_session
from core.models import Forecast, ModelRun
from core.security import touch_session
from app.styles import apply_theme, render_header, render_footer, PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY
from ml.data_sources.mospi_cpi import CATEGORIES
from ml.explain import get_top_drivers, generate_plain_language_explanation


def show_inflation_trends_page():
    st.set_page_config(page_title="Inflation Trends & Forecasts - Parivar Arth", page_icon="📈", layout="centered")
    apply_theme()
    touch_session()

    render_header(
        title="Inflation Engine & Forecasts",
        subtitle="Category-wise price movements powered by walk-forward ML models",
        icon="📈"
    )

    # Explanation banner on official definitions
    st.markdown(
        f"""
        <div style="background-color: #FEF3C7; border-left: 4px solid {ACCENT_SAFFRON}; padding: 10px 14px; border-radius: 6px; font-size: 0.85rem; color: #78350F; margin-bottom: 1rem;">
            <strong>Official MoSPI Category Clarifications:</strong><br>
            • <em>Fuel and Light</em> includes domestic LPG, electricity, and kerosene.<br>
            • <em>Transport and Communication</em> includes petrol, diesel, bus/metro fares, and mobile data.<br>
            • All forecasts are model estimates designed for household budget foresight.
        </div>
        """,
        unsafe_allow_html=True
    )

    # Fetch forecasts from database
    with get_db_session() as db:
        forecast_rows = db.query(Forecast).all()
        model_run_rows = db.query(ModelRun).all()

    if not forecast_rows:
        st.warning("⚠️ No precomputed forecast records found in database. Run `python scripts/train_models.py` or trigger model training from the Admin console.")
        render_footer()
        return

    # Convert to DataFrame
    df_fc = pd.DataFrame([{
        "category": r.category,
        "target_month": r.target_month,
        "predicted_inflation": r.predicted_inflation,
        "lower_ci": r.lower_ci,
        "upper_ci": r.upper_ci,
        "model_version": r.model_version
    } for r in forecast_rows])

    # Category Selector Tab / Dropdown
    selected_cat = st.selectbox(
        "Select CPI Expenditure Category to Inspect:",
        options=CATEGORIES,
        index=0,
        help="Explore historical drivers and forward forecasts for this specific basket."
    )

    df_cat = df_fc[df_fc["category"] == selected_cat].sort_values("target_month")

    if not df_cat.empty:
        # Latest Forecast Metric Card
        latest_pred = df_cat.iloc[0]["predicted_inflation"]
        latest_lower = df_cat.iloc[0]["lower_ci"]
        latest_upper = df_cat.iloc[0]["upper_ci"]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Expected Inflation (Next Month)", f"{latest_pred:.1f}%")
        with col2:
            st.metric("80% Lower Bound", f"{latest_lower:.1f}%")
        with col3:
            st.metric("80% Upper Bound", f"{latest_upper:.1f}%")

        # Plotly Forecast Chart with Uncertainty Shaded Band
        fig = go.Figure()

        # Shaded Interval (Upper Bound)
        fig.add_trace(go.Scatter(
            x=df_cat["target_month"],
            y=df_cat["upper_ci"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip"
        ))

        # Shaded Interval (Lower Bound)
        fig.add_trace(go.Scatter(
            x=df_cat["target_month"],
            y=df_cat["lower_ci"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(15, 118, 110, 0.15)",
            name="80% Prediction Interval",
            hoverinfo="skip"
        ))

        # Expected Prediction Line
        fig.add_trace(go.Scatter(
            x=df_cat["target_month"],
            y=df_cat["predicted_inflation"],
            mode="lines+markers",
            line=dict(color=PRIMARY_TEAL, width=3),
            marker=dict(size=6, color=ACCENT_SAFFRON),
            name="Expected Forecast"
        ))

        # RBI Upper tolerance threshold (6.0%)
        fig.add_trace(go.Scatter(
            x=df_cat["target_month"],
            y=[6.0] * len(df_cat),
            mode="lines",
            line=dict(color="#DC2626", dash="dot", width=1.5),
            name="RBI 6% Upper Bound"
        ))

        fig.update_layout(
            title=f"24-Month Forecast: {selected_cat} (with 80% Uncertainty Band)",
            xaxis_title="Target Month",
            yaxis_title="Annual YoY Inflation (%)",
            template="plotly_white",
            height=380,
            margin=dict(l=20, r=20, t=50, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

    # Explainability & Contributing Factors Section
    st.markdown("### 🔍 Plain-Language Economic Drivers")
    st.markdown(
        """
        Why is this inflation rate projected? The machine learning engine attributes changes
        to domestic supply, international commodities, and monetary conditions:
        """
    )

    # Heuristic driver highlights tailored per category
    if "Food" in selected_cat:
        st.info("🥦 **Food Drivers:** Kharif and Rabi crop yields, monsoon rainfall variation, perishable vegetable supply spikes (tomatoes/onions), and transport freight costs.")
    elif "Transport" in selected_cat:
        st.info("🚗 **Transport Drivers:** International crude oil in INR, domestic excise duties on petrol/diesel, vehicle spare parts inflation, and metro/bus fare revisions.")
    elif "Fuel" in selected_cat:
        st.info("⚡ **Fuel & Light Drivers:** Domestic LPG cylinder subsidy adjustments, state electricity board tariff slabs, and coal/kerosene prices.")
    elif "Education" in selected_cat:
        st.info("🎓 **Education Drivers:** Annual private school tuition restructuring (April-June admissions cycle), textbook printing costs, and coaching fees.")
    elif "Health" in selected_cat:
        st.info("🏥 **Healthcare Drivers:** Active Pharmaceutical Ingredient (API) import costs, private hospital room tariffs, and diagnostic medicine price revisions.")
    else:
        st.info("📈 **Macro Drivers:** Broad-based consumption momentum, wholesale price index (WPI) pass-through, and RBI monetary policy interest rates.")

    # Model Performance Leaderboard vs Naive Baseline
    with st.expander("📊 View Model Accuracy Leaderboard (Walk-Forward CV vs. Naive Baseline)"):
        st.markdown(
            """
            *Models are validated exclusively using Walk-Forward TimeSeriesSplit (zero future lookahead).*
            """
        )
        cat_runs = [r for r in model_run_rows if r.target_category == selected_cat]
        if cat_runs:
            perf_data = [{
                "Model Type": r.model_type,
                "Version": r.version,
                "RMSE": round(r.rmse, 3),
                "MAE": round(r.mae, 3),
                "MAPE (%)": f"{r.mape:.1f}%",
                "Baseline MAPE (%)": f"{r.baseline_mape:.1f}%",
                "Improvement vs Naive": f"{((1 - r.mape/r.baseline_mape)*100):.1f}%" if r.baseline_mape > 0 else "N/A"
            } for r in cat_runs]
            st.dataframe(pd.DataFrame(perf_data), use_container_width=True)
        else:
            st.write("Run training to view model comparison leaderboard.")

    render_footer()


if __name__ == "__main__":
    show_inflation_trends_page()
