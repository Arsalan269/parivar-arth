"""
Aether FinTech Design System for Parivar-Arth
Premium, minimal, and modern financial intelligence dashboard.
"""

import streamlit as st
import plotly.graph_objects as go

# ==========================================
# AETHER COLOR SYSTEM (Official Tokens)
# ==========================================
PRIMARY_ACCENT = "#6C63FF"       # Electric violet/purple
SECONDARY_ACCENT = "#8B83FF"     # Light purple gradient stop
SOFT_PURPLE = "#EFEDFF"          # Active state & soft pill tint
BG_PRIMARY = "#F5F7FA"           # Soft neutral app background
BG_CARD = "#FFFFFF"              # Crisp white card surface
TEXT_PRIMARY = "#202334"         # Deep slate for high-contrast headers/body
TEXT_SECONDARY = "#73788C"       # Muted slate for metadata & labels
BORDER_COLOR = "#E9EAF0"         # Ultra-subtle divider & card border
COLOR_SUCCESS = "#20B486"        # Fresh fintech green (Growth/Safe)
COLOR_WARNING = "#F4B740"        # Warm amber (Watch/Attention)
COLOR_DANGER = "#EF6461"         # Crisp crimson (Shortfall/Risk)

# Backward Compatibility Aliases for existing imports
PRIMARY_TEAL = PRIMARY_ACCENT
ACCENT_SAFFRON = COLOR_WARNING
TEXT_NAVY = TEXT_PRIMARY
BG_OFFWHITE = BG_PRIMARY
CARD_BG = BG_CARD
CARD_BORDER = BORDER_COLOR
STATUS_SAFE = COLOR_SUCCESS
STATUS_WATCH = COLOR_WARNING
STATUS_AT_RISK = COLOR_DANGER

DISCLAIMER_FOOTER = "Planning tool only, not financial or investment advice. Predictions and projections are estimates based on user data."

# ==========================================
# GLOBAL CSS - AETHER THEME
# ==========================================
CSS_RULES = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* Global Font & Canvas */
html, body, [class*="css"], .stApp {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
}}

/* App Container - Spacious, Modern FinTech Dashboard */
.block-container {{
    max-width: 1080px;
    padding-top: 1.5rem;
    padding-bottom: 3.5rem;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
}}

/* Typography */
h1, h2, h3, h4, h5, h6 {{
    font-family: 'Inter', sans-serif !important;
    color: {TEXT_PRIMARY} !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em !important;
}}

p, span, label, div {{
    font-family: 'Inter', sans-serif;
    color: {TEXT_PRIMARY};
}}

/* Aether Modern Cards */
.parivar-card, .aether-card {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_COLOR};
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}}

.parivar-card:hover, .aether-card:hover {{
    box-shadow: 0 8px 30px rgba(108, 99, 255, 0.06);
    border-color: #D6D2FF;
}}

/* Glassmorphism Highlight Card */
.aether-glass-card {{
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(233, 234, 240, 0.8);
    border-radius: 18px;
    padding: 1.5rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 8px 32px rgba(108, 99, 255, 0.05);
}}

/* Metric Cards */
.aether-metric-card {{
    background: {BG_CARD};
    border: 1px solid {BORDER_COLOR};
    border-radius: 16px;
    padding: 1.25rem 1.4rem;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.03);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 110px;
    transition: transform 0.2s ease;
}}

.aether-metric-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(108, 99, 255, 0.08);
}}

.aether-metric-label {{
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: {TEXT_SECONDARY};
    margin-bottom: 0.35rem;
}}

.aether-metric-value {{
    font-size: 1.85rem;
    font-weight: 800;
    color: {TEXT_PRIMARY};
    line-height: 1.2;
    letter-spacing: -0.03em;
}}

.aether-metric-subtext {{
    font-size: 0.8rem;
    color: {TEXT_SECONDARY};
    margin-top: 0.4rem;
}}

/* Streamlit Native Metric Overrides */
[data-testid="stMetric"] {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_COLOR};
    border-radius: 16px;
    padding: 1rem 1.25rem;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
}}

[data-testid="stMetricLabel"] {{
    color: {TEXT_SECONDARY} !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

[data-testid="stMetricValue"] {{
    color: {TEXT_PRIMARY} !important;
    font-weight: 800 !important;
    font-size: 1.75rem !important;
    letter-spacing: -0.02em;
}}

/* Primary & Action Buttons */
.stButton > button, button[kind="primary"] {{
    background: linear-gradient(135deg, {PRIMARY_ACCENT} 0%, {SECONDARY_ACCENT} 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.6rem 1.4rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    min-height: 44px !important;
    box-shadow: 0 4px 14px rgba(108, 99, 255, 0.28) !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}

.stButton > button:hover, button[kind="primary"]:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(108, 99, 255, 0.42) !important;
    opacity: 0.96;
}}

.stButton > button:active {{
    transform: translateY(0px) !important;
}}

/* Form Inputs, Selects, Sliders */
[data-baseweb="input"], [data-baseweb="select"], .stTextInput > div > div, .stNumberInput > div > div {{
    border-radius: 10px !important;
    border: 1px solid {BORDER_COLOR} !important;
    background-color: #FFFFFF !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}}

[data-baseweb="input"]:focus-within, [data-baseweb="select"]:focus-within {{
    border-color: {PRIMARY_ACCENT} !important;
    box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.15) !important;
}}

/* Modern Tabs */
.stTabs [data-baseweb="tab-list"] {{
    gap: 8px;
    background-color: transparent;
    border-bottom: 1px solid {BORDER_COLOR};
    padding-bottom: 4px;
}}

.stTabs [data-baseweb="tab"] {{
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 0.9rem;
    color: {TEXT_SECONDARY};
    border: none;
    background: transparent;
    transition: all 0.2s ease;
}}

.stTabs [data-baseweb="tab"]:hover {{
    color: {PRIMARY_ACCENT};
    background-color: {SOFT_PURPLE};
}}

.stTabs [aria-selected="true"] {{
    color: {PRIMARY_ACCENT} !important;
    background-color: {SOFT_PURPLE} !important;
    border-bottom: 2px solid {PRIMARY_ACCENT} !important;
}}

/* Expanders */
.streamlit-expanderHeader {{
    background-color: {BG_CARD} !important;
    border-radius: 12px !important;
    border: 1px solid {BORDER_COLOR} !important;
    font-weight: 600 !important;
    color: {TEXT_PRIMARY} !important;
}}

/* Badges */
.status-badge {{
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}}

.status-safe {{
    background-color: #E6F8F3;
    color: {COLOR_SUCCESS};
    border: 1px solid #A7F3D0;
}}

.status-watch {{
    background-color: #FFFBEB;
    color: #D97706;
    border: 1px solid #FDE68A;
}}

.status-at-risk {{
    background-color: #FEF2F2;
    color: {COLOR_DANGER};
    border: 1px solid #FECACA;
}}

.status-purple {{
    background-color: {SOFT_PURPLE};
    color: {PRIMARY_ACCENT};
    border: 1px solid #D6D2FF;
}}

/* Sidebar Refinements */
[data-testid="stSidebar"] {{
    background-color: #FFFFFF !important;
    border-right: 1px solid {BORDER_COLOR};
}}

[data-testid="stSidebarNav"] {{
    padding-top: 1rem;
}}

[data-testid="stSidebarNav"] a {{
    border-radius: 10px;
    margin: 3px 8px;
    padding: 8px 12px;
    transition: all 0.15s ease;
    font-weight: 500;
    color: {TEXT_PRIMARY} !important;
}}

[data-testid="stSidebarNav"] a:hover {{
    background-color: {BG_PRIMARY};
    color: {PRIMARY_ACCENT} !important;
}}

[data-testid="stSidebarNav"] a[aria-current="page"] {{
    background-color: {SOFT_PURPLE} !important;
    color: {PRIMARY_ACCENT} !important;
    font-weight: 700 !important;
}}

/* Sidebar Brand Header */
.sidebar-brand-box {{
    padding: 1.25rem 1rem 0.75rem 1rem;
    margin-bottom: 0.5rem;
    border-bottom: 1px solid {BORDER_COLOR};
}}

.sidebar-brand-title {{
    font-size: 1.25rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, {PRIMARY_ACCENT} 0%, {SECONDARY_ACCENT} 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}}

.sidebar-brand-subtitle {{
    font-size: 0.75rem;
    color: {TEXT_SECONDARY};
    margin: 2px 0 0 0;
    font-weight: 500;
    letter-spacing: 0.02em;
}}

.sidebar-user-card {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 12px;
    padding: 0.75rem 1rem;
    margin-top: 1rem;
    margin-bottom: 0.75rem;
}}

/* Tables / Dataframes */
[data-testid="stDataFrame"] {{
    border-radius: 12px;
    border: 1px solid {BORDER_COLOR};
    overflow: hidden;
}}

/* Footer */
.parivar-footer {{
    margin-top: 3.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid {BORDER_COLOR};
    text-align: center;
    font-size: 0.8rem;
    color: {TEXT_SECONDARY};
    line-height: 1.5;
}}
</style>
"""


def apply_theme():
    """Inject global Aether design tokens and CSS into the Streamlit session."""
    st.markdown(CSS_RULES, unsafe_allow_html=True)


def render_header(title: str, subtitle: str = "", tag: str = None):
    """
    Render a clean, modern Aether FinTech page header.
    """
    tag_html = f'<span class="status-badge status-purple" style="margin-left: 10px;">{tag}</span>' if tag else ""
    st.markdown(
        f"""
        <div style="margin-bottom: 1.5rem; padding-bottom: 0.75rem; border-bottom: 1px solid {BORDER_COLOR};">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center;">
                    <h1 style="margin: 0; font-size: 1.85rem; font-weight: 800; color: {TEXT_PRIMARY}; letter-spacing: -0.03em;">
                        {title}
                    </h1>
                    {tag_html}
                </div>
            </div>
            {f'<p style="margin: 6px 0 0 0; color: {TEXT_SECONDARY}; font-size: 0.95rem; font-weight: 400; line-height: 1.4;">{subtitle}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, subtext: str = "", badge_text: str = "", badge_type: str = "purple"):
    """
    Render a standalone Aether FinTech Metric Card with subtle shadow and border.
    """
    badge_html = ""
    if badge_text:
        badge_cls = {
            "safe": "status-safe",
            "watch": "status-watch",
            "risk": "status-at-risk",
            "purple": "status-purple"
        }.get(badge_type.lower(), "status-purple")
        badge_html = f'<span class="status-badge {badge_cls}">{badge_text}</span>'

    st.markdown(
        f"""
        <div class="aether-metric-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div class="aether-metric-label">{label}</div>
                {badge_html}
            </div>
            <div class="aether-metric-value">{value}</div>
            {f'<div class="aether-metric-subtext">{subtext}</div>' if subtext else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_badge(status: str) -> str:
    """Return HTML for an Aether status pill badge without emojis."""
    norm = status.strip().lower()
    if "safe" in norm or "on track" in norm or "healthy" in norm or "good" in norm:
        return f'<span class="status-badge status-safe">{status}</span>'
    elif "watch" in norm or "moderate" in norm or "caution" in norm or "warning" in norm:
        return f'<span class="status-badge status-watch">{status}</span>'
    elif "risk" in norm or "danger" in norm or "shortfall" in norm or "critical" in norm:
        return f'<span class="status-badge status-at-risk">{status}</span>'
    return f'<span class="status-badge status-purple">{status}</span>'


def render_sidebar_brand():
    """Render consistent modern brand block in Streamlit sidebar."""
    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand-box">
            <div class="sidebar-brand-title">Parivar Arth</div>
            <div class="sidebar-brand-subtitle">Family Financial Intelligence</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_sidebar_user(username: str, role: str = "Primary Account"):
    """Render a clean user profile card at the bottom of the sidebar."""
    st.sidebar.markdown(
        f"""
        <div class="sidebar-user-card">
            <div style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: {TEXT_SECONDARY}; font-weight: 600;">Signed in as</div>
            <div style="font-size: 0.92rem; font-weight: 700; color: {TEXT_PRIMARY};">{username}</div>
            <div style="font-size: 0.75rem; color: {PRIMARY_ACCENT}; font-weight: 500;">{role}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_footer():
    """Render the standard mandatory disclaimer footer."""
    st.markdown(
        f"""
        <div class="parivar-footer">
            <p><strong>Parivar Arth</strong> | {DISCLAIMER_FOOTER}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_aether_chart_layout(title: str = "", height: int = 380, show_legend: bool = True) -> dict:
    """
    Return a standardized Plotly layout dict matching the Aether FinTech aesthetic.
    """
    return dict(
        title=dict(
            text=f"<b>{title}</b>" if title else "",
            font=dict(family="Inter, sans-serif", size=15, color=TEXT_PRIMARY),
            x=0.02,
            y=0.96,
        ),
        font=dict(family="Inter, sans-serif", color=TEXT_PRIMARY),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        height=height,
        margin=dict(l=40, r=30, t=50 if title else 20, b=40),
        xaxis=dict(
            gridcolor=BORDER_COLOR,
            linecolor=BORDER_COLOR,
            zerolinecolor=BORDER_COLOR,
            tickfont=dict(size=11, color=TEXT_SECONDARY),
        ),
        yaxis=dict(
            gridcolor=BORDER_COLOR,
            linecolor=BORDER_COLOR,
            zerolinecolor=BORDER_COLOR,
            tickfont=dict(size=11, color=TEXT_SECONDARY),
        ),
        colorway=[PRIMARY_ACCENT, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, SECONDARY_ACCENT, "#38BDF8"],
        showlegend=show_legend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color=TEXT_SECONDARY),
        ),
    )


def apply_aether_chart_theme(fig, title: str = "", height: int = 380, show_legend: bool = True):
    """
    Apply Aether FinTech theme directly onto an existing Plotly figure.
    """
    layout_dict = get_aether_chart_layout(title=title, height=height, show_legend=show_legend)
    fig.update_layout(**layout_dict)
    return fig
