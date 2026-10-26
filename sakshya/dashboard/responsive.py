"""
Sakshya Responsive UI System
Provides universal device responsiveness across Mobile (320px, 375px, 390px, 430px),
Tablets (768px, 1024px), Laptops (1366px), and Desktops/Large Screens (1920px+).
"""

import streamlit as st

RESPONSIVE_CSS = """
<style>
/* ==========================================================================
   1. GLOBAL VIEWPORT & RESET FIXES (Prevents unintended horizontal scroll)
   ========================================================================== */
html, body {
    overflow-x: hidden !important;
    max-width: 100vw !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    -webkit-text-size-adjust: 100%;
}

.stApp {
    overflow-x: hidden !important;
    max-width: 100vw !important;
    width: 100% !important;
}

/* Fluid App Container Padding */
.block-container {
    padding-top: clamp(1.2rem, 3vw, 2.5rem) !important;
    padding-bottom: clamp(1.5rem, 4vw, 3.5rem) !important;
    padding-left: clamp(0.75rem, 2.5vw, 2.5rem) !important;
    padding-right: clamp(0.75rem, 2.5vw, 2.5rem) !important;
    max-width: 1680px !important;
    margin: 0 auto !important;
}

/* ==========================================================================
   2. STREAMLIT COLUMNS RESPONSIVENESS (Mobile Stacking & Tablet Grids)
   ========================================================================== */
/* Mobile Portrait & Small Screens (<= 768px): Stack columns vertically */
@media screen and (max-width: 768px) {
    div[data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
        flex-wrap: wrap !important;
        width: 100% !important;
        gap: 12px !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        width: 100% !important;
        min-width: 100% !important;
        flex: 1 1 100% !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        margin-bottom: 6px !important;
    }
}

/* Tablet Screens (769px to 1024px): Allow 2-column or 3-column wrapping */
@media screen and (min-width: 769px) and (max-width: 1024px) {
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(4)) {
        flex-wrap: wrap !important;
        gap: 14px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(4)) > div[data-testid="column"] {
        flex: 1 1 calc(50% - 14px) !important;
        min-width: calc(50% - 14px) !important;
    }
}

/* ==========================================================================
   3. METRIC CARDS & KPIS (Fluid Typography & Word Wrapping)
   ========================================================================== */
[data-testid="stMetric"] {
    background-color: #F8FAFC !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    padding: clamp(10px, 2vw, 16px) !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    width: 100% !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

[data-testid="stMetric"]:hover {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08) !important;
}

[data-testid="stMetricLabel"] {
    font-size: clamp(11.5px, 2.2vw, 13.5px) !important;
    font-weight: 600 !important;
    color: #475569 !important;
    white-space: normal !important;
    word-break: break-word !important;
    line-height: 1.3 !important;
}

[data-testid="stMetricValue"] {
    font-size: clamp(18px, 4vw, 26px) !important;
    font-weight: 700 !important;
    color: #0F172A !important;
    word-break: break-word !important;
    overflow-wrap: anywhere !important;
    line-height: 1.25 !important;
}

[data-testid="stMetricDelta"] {
    font-size: clamp(11px, 2vw, 13px) !important;
    word-break: break-word !important;
}

/* ==========================================================================
   4. FLUID TYPOGRAPHY & TEXT BREAKING
   ========================================================================== */
h1 {
    font-size: clamp(20px, 5vw, 32px) !important;
    line-height: 1.25 !important;
    word-break: break-word !important;
    overflow-wrap: break-word !important;
}

h2 {
    font-size: clamp(18px, 4vw, 24px) !important;
    line-height: 1.3 !important;
    word-break: break-word !important;
    overflow-wrap: break-word !important;
}

h3 {
    font-size: clamp(15.5px, 3.2vw, 20px) !important;
    line-height: 1.35 !important;
    word-break: break-word !important;
    overflow-wrap: break-word !important;
}

p, li, span {
    word-break: break-word;
    overflow-wrap: break-word;
}

code, pre {
    word-break: break-all !important;
    overflow-wrap: anywhere !important;
    white-space: pre-wrap !important;
}

/* ==========================================================================
   5. BANNER & RESPONSIVE CARDS
   ========================================================================== */
.main-header {
    background: linear-gradient(135deg, #1E3A8A 0%, #0F172A 100%) !important;
    padding: clamp(14px, 3vw, 24px) !important;
    border-radius: 12px !important;
    color: white !important;
    margin-bottom: 20px !important;
    border-left: 6px solid #F59E0B !important;
    word-break: break-word !important;
    overflow-wrap: break-word !important;
}

.main-header h1 {
    margin: 0 !important;
    font-size: clamp(17px, 4.2vw, 28px) !important;
    color: #FFFFFF !important;
    line-height: 1.25 !important;
}

.main-header p {
    margin: 6px 0 0 0 !important;
    opacity: 0.9 !important;
    font-size: clamp(11.5px, 2.6vw, 14px) !important;
    line-height: 1.4 !important;
}

.responsive-card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: clamp(10px, 2vw, 16px);
    margin-bottom: 12px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    word-break: break-word;
    overflow-wrap: break-word;
}

.responsive-flex {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: space-between;
    align-items: center;
}

@media screen and (max-width: 768px) {
    .responsive-flex {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 8px !important;
    }
    .responsive-flex > div {
        width: 100% !important;
        text-align: left !important;
    }
}

/* ==========================================================================
   6. RESPONSIVE LEGENDS (Knowledge Graphs & Ring Networks)
   ========================================================================== */
.responsive-legend {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 8px 14px !important;
    background-color: #0F172A !important;
    padding: 10px 14px !important;
    border-radius: 8px !important;
    color: #F8FAFC !important;
    font-size: clamp(11px, 2.5vw, 13px) !important;
    margin-bottom: 12px !important;
    line-height: 1.4 !important;
}

.responsive-legend > span {
    display: inline-flex !important;
    align-items: center !important;
    white-space: nowrap !important;
}

/* ==========================================================================
   7. IFRAME & KNOWLEDGE GRAPH RESPONSIVENESS
   ========================================================================== */
iframe[title="streamlit.components.v1.html"], iframe {
    width: 100% !important;
    max-width: 100% !important;
    border-radius: 8px !important;
    border: 1px solid #334155 !important;
    box-sizing: border-box !important;
}

@media screen and (max-width: 768px) {
    iframe[title="streamlit.components.v1.html"], iframe {
        height: 440px !important;
    }
}

@media screen and (min-width: 769px) and (max-width: 1024px) {
    iframe[title="streamlit.components.v1.html"], iframe {
        height: 520px !important;
    }
}

@media screen and (min-width: 1025px) {
    iframe[title="streamlit.components.v1.html"], iframe {
        height: 650px !important;
    }
}

.graph-touch-hint {
    font-size: 11.5px;
    color: #94A3B8;
    margin-top: 4px;
    margin-bottom: 10px;
    font-style: italic;
}

/* ==========================================================================
   8. TOUCH TARGETS (Buttons, Dropdowns, Tabs >= 44px on Touch Devices)
   ========================================================================== */
.stButton > button, .stDownloadButton > button {
    min-height: 44px !important;
    padding: 8px 16px !important;
    font-size: clamp(13px, 2.6vw, 15px) !important;
    border-radius: 8px !important;
    touch-action: manipulation !important;
    box-sizing: border-box !important;
}

@media screen and (max-width: 768px) {
    .stButton > button, .stDownloadButton > button {
        width: 100% !important;
    }
}

/* Tabs touch target & horizontal scroll */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    flex-wrap: nowrap !important;
    padding-bottom: 4px !important;
}

.stTabs [data-baseweb="tab"] {
    min-height: 44px !important;
    padding: 8px 14px !important;
    font-size: clamp(12px, 2.5vw, 14px) !important;
    white-space: nowrap !important;
}

/* Form inputs touch ergonomics */
.stSelectbox > div, .stTextInput > div, .stTextArea > div {
    min-height: 44px !important;
}

/* ==========================================================================
   9. DATAFRAMES & TABLES SCROLLABILITY
   ========================================================================== */
[data-testid="stDataFrame"], [data-testid="stTable"] {
    width: 100% !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    border-radius: 8px !important;
}

/* ==========================================================================
   10. PLOTLY CHARTS CONTAINER
   ========================================================================== */
.js-plotly-plot, .plot-container {
    width: 100% !important;
    max-width: 100% !important;
}

/* ==========================================================================
   11. SIDEBAR ERGONOMICS
   ========================================================================== */
section[data-testid="stSidebar"] {
    width: min(300px, 85vw) !important;
}
section[data-testid="stSidebar"] .block-container {
    padding: 1.5rem 1rem !important;
}
</style>
"""


def inject_responsive_css():
    """Inject universal responsive styling across all pages."""
    st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
