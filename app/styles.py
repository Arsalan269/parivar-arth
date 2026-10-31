"""
Styles and Design Tokens for Parivar Arth (Family Money Planner)
Concept: Calm, trustworthy money clarity with Indian warmth.
"""

import streamlit as st

# Color Palette Constants
PRIMARY_TEAL = "#0F766E"      # Growth, stability
ACCENT_SAFFRON = "#F59E0B"    # Warm saffron, inflation highlight
TEXT_NAVY = "#0B1F3A"         # High readability headers & body
BG_OFFWHITE = "#FAF7F2"       # Calm Indian off-white
CARD_BG = "#FFFFFF"           # Clean soft cards
CARD_BORDER = "#E5E0D8"       # Subtle warm border

# Status Indicators
STATUS_SAFE = "#16A34A"       # Green
STATUS_WATCH = "#F59E0B"      # Amber
STATUS_AT_RISK = "#DC2626"    # Red

DISCLAIMER_FOOTER = "Planning tool only, not financial or medical advice. Predictions are estimates."

CSS_RULES = f"""
<style>
/* Global resets and typography */
html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: {TEXT_NAVY};
}}

/* Main container constraints for mobile-first experience */
.block-container {{
    max-width: 720px;
    padding-top: 1.5rem;
    padding-bottom: 3.5rem;
    padding-left: 1rem;
    padding-right: 1rem;
}}

/* Headings with warm navy */
h1, h2, h3, h4 {{
    color: {TEXT_NAVY} !important;
    font-weight: 700;
    letter-spacing: -0.02em;
}}

/* Indian warmth soft cards */
.parivar-card {{
    background-color: {CARD_BG};
    border: 1px solid {CARD_BORDER};
    border-radius: 14px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(15, 118, 110, 0.05);
}}

/* Status badges with both icon and text */
.status-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 600;
}}

.status-safe {{
    background-color: #DCFCE7;
    color: #15803D;
    border: 1px solid #86EFAC;
}}

.status-watch {{
    background-color: #FEF3C7;
    color: #B45309;
    border: 1px solid #FDE68A;
}}

.status-at-risk {{
    background-color: #FEE2E2;
    color: #B91C1C;
    border: 1px solid #FCA5A5;
}}

/* Big tap-friendly buttons */
button[kind="primary"], .stButton > button {{
    min-height: 48px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 1rem;
    transition: all 0.15s ease-in-out;
}}

.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(15, 118, 110, 0.15);
}}

/* Prominent Rupee metric highlights */
.metric-large {{
    font-size: 1.85rem;
    font-weight: 800;
    color: {PRIMARY_TEAL};
    line-height: 1.2;
}}

.metric-label {{
    font-size: 0.825rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #5A6A80;
    font-weight: 600;
}}

/* Footer styling */
.parivar-footer {{
    margin-top: 3rem;
    padding-top: 1.25rem;
    border-top: 1px solid {CARD_BORDER};
    text-align: center;
    font-size: 0.8rem;
    color: #64748B;
    line-height: 1.4;
}}

/* Mobile responsive adjustments */
@media (max-width: 480px) {{
    .block-container {{
        padding-left: 0.75rem;
        padding-right: 0.75rem;
    }}
    .metric-large {{
        font-size: 1.5rem;
    }}
}}
</style>
"""


def apply_theme():
    """Inject the global CSS rules into the Streamlit session."""
    st.markdown(CSS_RULES, unsafe_allow_html=True)


def render_header(title: str, subtitle: str = "", icon: str = ""):
    """Render a consistent branded header without emojis."""
    st.markdown(
        f"""
        <div style="margin-bottom: 1.25rem; padding-bottom: 0.5rem; border-bottom: 2px solid #E2E8F0;">
            <h2 style="margin: 0; font-size: 1.7rem; color: {TEXT_NAVY}; font-weight: 700;">{title}</h2>
            {f'<p style="margin: 4px 0 0 0; color: #5A6A80; font-size: 0.95rem;">{subtitle}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_status_badge(status: str) -> str:
    """Return HTML for a status badge without emojis."""
    norm = status.strip().lower()
    if "safe" in norm:
        return '<span class="status-badge status-safe">[Safe]</span>'
    elif "watch" in norm:
        return '<span class="status-badge status-watch">[Watch]</span>'
    elif "risk" in norm or "danger" in norm:
        return '<span class="status-badge status-at-risk">[At Risk]</span>'
    return f'<span class="status-badge status-watch">[{status}]</span>'


def render_footer():
    """Render the standard mandatory disclaimer footer without Hindi text."""
    st.markdown(
        f"""
        <div class="parivar-footer">
            <p><strong>Parivar Arth</strong> - {DISCLAIMER_FOOTER}</p>
        </div>
        """,
        unsafe_allow_html=True
    )
