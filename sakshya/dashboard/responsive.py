"""
Sakshya Responsive UI System — Government Portal Design System
Provides official Indian e-governance styling (Ministry of Education / AICTE administrative style)
with full responsiveness across Mobile (320px–430px), Tablets (768px–1024px), Laptops (1366px),
and Large Desktops (1920px+).
"""

import streamlit as st

RESPONSIVE_CSS = """
<style>
/* ==========================================================================
   1. GOVERNMENT PORTAL FONT STACK, RESET & VIEWPORT
   ========================================================================== */
html, body {
    overflow-x: hidden !important;
    max-width: 100vw !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, 'Helvetica Neue', Arial, sans-serif !important;
    color: #1E293B !important;
    background-color: #FFFFFF !important;
    -webkit-text-size-adjust: 100%;
}

.stApp {
    overflow-x: hidden !important;
    max-width: 100vw !important;
    width: 100% !important;
    background-color: #FFFFFF !important;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, 'Helvetica Neue', Arial, sans-serif !important;
}

/* Fluid App Container Padding with restrained administrative width */
.block-container {
    padding-top: clamp(3.75rem, 5vw, 4.5rem) !important;
    padding-bottom: clamp(1.5rem, 3.5vw, 3rem) !important;
    padding-left: clamp(0.75rem, 2vw, 2.5rem) !important;
    padding-right: clamp(0.75rem, 2vw, 2.5rem) !important;
    max-width: 1600px !important;
    margin: 0 auto !important;
}

@media screen and (max-width: 768px) {
    .block-container {
        padding-top: 3.85rem !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-bottom: 1.5rem !important;
    }
}

/* ==========================================================================
   2. TYPOGRAPHY & ADMINISTRATIVE HEADINGS
   ========================================================================== */
h1 {
    font-size: clamp(20px, 4vw, 26px) !important;
    font-weight: 700 !important;
    color: #0B2545 !important;
    line-height: 1.3 !important;
    letter-spacing: -0.2px !important;
    margin-top: 0.5rem !important;
    margin-bottom: 0.5rem !important;
    word-break: break-word !important;
}

h2 {
    font-size: clamp(17px, 3.2vw, 21px) !important;
    font-weight: 700 !important;
    color: #0B2545 !important;
    line-height: 1.35 !important;
    margin-top: 0.75rem !important;
    margin-bottom: 0.5rem !important;
    word-break: break-word !important;
}

h3 {
    font-size: clamp(15px, 2.6vw, 18px) !important;
    font-weight: 600 !important;
    color: #0B2545 !important;
    line-height: 1.4 !important;
    margin-top: 0.6rem !important;
    margin-bottom: 0.4rem !important;
    word-break: break-word !important;
}

h4, h5, h6 {
    color: #1E293B !important;
    font-weight: 600 !important;
}

p, li, span {
    font-size: 13.5px;
    line-height: 1.5;
    color: #334155;
    word-break: break-word;
}

strong, b {
    color: #0F172A;
}

/* ==========================================================================
   3. GOVERNMENT MASTHEAD, SECTIONS & NOTICES
   ========================================================================== */
/* Official Portal Header Masthead */
.gov-masthead {
    background-color: #0B2545 !important;
    border-top: 4px solid #D97706 !important;
    border-bottom: 2px solid #081B33 !important;
    padding: clamp(12px, 2.2vw, 18px) clamp(14px, 2.8vw, 22px) !important;
    border-radius: 4px !important;
    color: #FFFFFF !important;
    margin-bottom: 12px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
    height: auto !important;
    min-height: 0 !important;
}

.gov-masthead,
.gov-masthead *,
.gov-masthead h1,
.gov-masthead h2,
.gov-masthead h3,
.gov-masthead a,
.gov-masthead div,
.gov-masthead span,
.gov-masthead p,
.gov-masthead .gov-masthead-title {
    color: #FFFFFF !important;
}

.gov-masthead a:hover {
    color: #FEF3C7 !important;
}

.gov-masthead-dept {
    font-size: clamp(10px, 2.2vw, 11px) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
    color: #FEF3C7 !important;
    font-weight: 700 !important;
    margin-bottom: 3px !important;
    line-height: 1.35 !important;
    word-break: break-word !important;
}

.gov-masthead-title {
    font-size: clamp(20px, 4.2vw, 26px) !important;
    font-weight: 800 !important;
    color: #FFFFFF !important;
    letter-spacing: -0.2px !important;
    margin: 2px 0 4px 0 !important;
    line-height: 1.25 !important;
    word-break: break-word !important;
}

.gov-masthead-subtitle {
    font-size: clamp(12px, 2.4vw, 13.5px) !important;
    color: #E2E8F0 !important;
    margin: 0 0 6px 0 !important;
    line-height: 1.4 !important;
    word-break: break-word !important;
}

.gov-masthead p {
    color: #E2E8F0 !important;
    margin: 3px 0 6px 0 !important;
    font-size: clamp(12px, 2.4vw, 13.5px) !important;
    line-height: 1.4 !important;
}

.gov-masthead-badge {
    display: inline-block !important;
    margin-top: 4px !important;
    font-size: clamp(10px, 2.2vw, 11px) !important;
    color: #FEF3C7 !important;
    background: rgba(217, 119, 6, 0.25) !important;
    border: 1px solid #D97706 !important;
    padding: 3px 9px !important;
    border-radius: 3px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    line-height: 1.35 !important;
    word-break: break-word !important;
}

@media screen and (max-width: 768px) {
    .gov-masthead {
        padding: 11px 13px !important;
        margin-bottom: 10px !important;
    }
    .gov-masthead-dept {
        font-size: 10px !important;
        letter-spacing: 0.6px !important;
        margin-bottom: 2px !important;
    }
    .gov-masthead-title {
        font-size: 20px !important;
        margin: 2px 0 3px 0 !important;
    }
    .gov-masthead-subtitle {
        font-size: 11.5px !important;
        margin: 0 0 5px 0 !important;
        line-height: 1.35 !important;
    }
    .gov-masthead-badge {
        font-size: 10px !important;
        padding: 2px 7px !important;
        margin-top: 2px !important;
    }
}

/* Administrative Box / Fieldset Container */
.gov-card {
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1;
    border-radius: 4px !important;
    padding: clamp(12px, 2vw, 16px) !important;
    margin-bottom: 12px !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
    box-sizing: border-box !important;
    height: auto !important;
    min-height: 0 !important;
    overflow: visible !important;
}

@media screen and (max-width: 768px) {
    .gov-card {
        padding: 10px 12px !important;
        margin-bottom: 10px !important;
        height: auto !important;
        min-height: 0 !important;
    }
}

.gov-card-header {
    font-size: 15px !important;
    font-weight: 700 !important;
    color: #0B2545 !important;
    border-bottom: 1px solid #E2E8F0 !important;
    padding-bottom: 8px !important;
    margin-bottom: 12px !important;
}

/* Administrative Notice & Disclaimers */
.gov-notice {
    background-color: #F8FAFC !important;
    border: 1px solid #CBD5E1 !important;
    border-left: 4px solid #0B3C5D !important;
    border-radius: 3px !important;
    padding: 12px 16px !important;
    margin: 12px 0 !important;
    color: #334155 !important;
    font-size: 13px !important;
    line-height: 1.45 !important;
}

.gov-notice-warning {
    background-color: #FFFBEB !important;
    border: 1px solid #FDE68A !important;
    border-left: 4px solid #D97706 !important;
    color: #92400E !important;
}

/* Legacy banner compatibility */
.main-header {
    background-color: #0B2545 !important;
    border-top: 4px solid #D97706 !important;
    border-bottom: 2px solid #081B33 !important;
    padding: clamp(14px, 2.5vw, 20px) clamp(16px, 3vw, 24px) !important;
    border-radius: 4px !important;
    color: #FFFFFF !important;
    margin-bottom: 18px !important;
    border-left: none !important;
}

.main-header h1 {
    color: #FFFFFF !important;
}

.main-header p {
    color: #CBD5E1 !important;
}

/* ==========================================================================
   4. GOVERNMENT REGULATORY STATUS BADGES
   ========================================================================== */
.gov-badge {
    display: inline-block !important;
    padding: 3px 9px !important;
    border-radius: 3px !important;
    font-size: 11.5px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.4px !important;
    line-height: 1.3 !important;
}

.gov-badge-verified {
    background-color: #DCFCE7 !important;
    color: #166534 !important;
    border: 1px solid #86EFAC !important;
}

.gov-badge-review {
    background-color: #FEF3C7 !important;
    color: #92400E !important;
    border: 1px solid #FCD34D !important;
}

.gov-badge-flagged {
    background-color: #FEE2E2 !important;
    color: #991B1B !important;
    border: 1px solid #FCA5A5 !important;
}

.gov-badge-info {
    background-color: #DBEAFE !important;
    color: #1E40AF !important;
    border: 1px solid #93C5FD !important;
}

.gov-badge-neutral {
    background-color: #F1F5F9 !important;
    color: #475569 !important;
    border: 1px solid #CBD5E1 !important;
}

/* ==========================================================================
   5. COMPACT ADMINISTRATIVE METRIC PANELS (MIS STYLE)
   ========================================================================== */
[data-testid="stMetric"] {
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-top: 3px solid #0B2545 !important;
    border-radius: 4px !important;
    padding: clamp(10px, 1.8vw, 14px) !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    width: 100% !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
}

[data-testid="stMetricLabel"] {
    font-size: clamp(10.5px, 2vw, 12px) !important;
    font-weight: 700 !important;
    color: #475569 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.4px !important;
    white-space: normal !important;
    word-break: break-word !important;
    line-height: 1.3 !important;
}

[data-testid="stMetricValue"] {
    font-size: clamp(18px, 3.5vw, 24px) !important;
    font-weight: 700 !important;
    color: #0B2545 !important;
    word-break: break-word !important;
    overflow-wrap: anywhere !important;
    line-height: 1.25 !important;
}

[data-testid="stMetricDelta"] {
    font-size: clamp(11px, 1.8vw, 12px) !important;
    font-weight: 600 !important;
}

/* ==========================================================================
   6. GOVERNMENT FORMS & ADMINISTRATIVE CONTROLS
   ========================================================================== */
/* Official Action Buttons */
.stButton > button, .stDownloadButton > button {
    min-height: 40px !important;
    padding: 7px 16px !important;
    font-size: clamp(12.5px, 2.4vw, 14px) !important;
    font-weight: 600 !important;
    border-radius: 4px !important;
    touch-action: manipulation !important;
    box-sizing: border-box !important;
    letter-spacing: 0.2px !important;
    transition: background-color 0.15s ease, border-color 0.15s ease !important;
}

.stButton > button[kind="primary"] {
    background-color: #0B3C5D !important;
    color: #FFFFFF !important;
    border: 1px solid #0B3C5D !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06) !important;
}

.stButton > button[kind="primary"]:hover {
    background-color: #133E87 !important;
    border-color: #133E87 !important;
    color: #FFFFFF !important;
}

.stButton > button[kind="secondary"] {
    background-color: #FFFFFF !important;
    color: #0B2545 !important;
    border: 1px solid #CBD5E1 !important;
}

.stButton > button[kind="secondary"]:hover {
    background-color: #F8FAFC !important;
    border-color: #94A3B8 !important;
}

/* Form Input Fields */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox [data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    border: 1px solid #94A3B8 !important;
    border-radius: 3px !important;
    color: #1E293B !important;
    font-size: 13.5px !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stSelectbox [data-baseweb="select"] > div:focus-within {
    border-color: #0B3C5D !important;
    box-shadow: 0 0 0 1px #0B3C5D !important;
}

.stTextInput label, .stSelectbox label, .stTextArea label, .stRadio label, .stCheckbox label {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #1E293B !important;
}

/* File Uploader styling */
[data-testid="stFileUploader"] {
    background-color: #F8FAFC !important;
    border: 1px dashed #94A3B8 !important;
    border-radius: 4px !important;
    padding: 12px !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: #0B3C5D !important;
}

/* Tabs: Official government underline tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    flex-wrap: nowrap !important;
    border-bottom: 2px solid #CBD5E1 !important;
    background: transparent !important;
    padding-bottom: 0 !important;
}

.stTabs [data-baseweb="tab"] {
    min-height: 42px !important;
    padding: 8px 16px !important;
    font-size: clamp(12.5px, 2.4vw, 13.5px) !important;
    font-weight: 600 !important;
    color: #475569 !important;
    white-space: nowrap !important;
    border-bottom: 3px solid transparent !important;
    border-radius: 0 !important;
    background: transparent !important;
}

.stTabs [aria-selected="true"] {
    color: #0B2545 !important;
    border-bottom: 3px solid #0B2545 !important;
    font-weight: 700 !important;
    background: transparent !important;
}

/* Expanders */
.streamlit-expanderHeader {
    background-color: #F8FAFC !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 4px !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    color: #0B2545 !important;
    padding: 10px 14px !important;
}

/* ==========================================================================
   7. GOVERNMENT TABLES & APPLICATION QUEUE
   ========================================================================== */
[data-testid="stDataFrame"], [data-testid="stTable"] {
    width: 100% !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 4px !important;
    background-color: #FFFFFF !important;
}

/* Table header styling */
[data-testid="stTable"] th {
    background-color: #F1F5F9 !important;
    color: #0B2545 !important;
    font-weight: 700 !important;
    font-size: 12px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.4px !important;
    border-bottom: 2px solid #CBD5E1 !important;
    padding: 10px 12px !important;
}

[data-testid="stTable"] td {
    font-size: 13px !important;
    padding: 9px 12px !important;
    border-bottom: 1px solid #E2E8F0 !important;
}

/* Zebra striping */
[data-testid="stTable"] tr:nth-child(even) td {
    background-color: #F8FAFC !important;
}

/* ==========================================================================
   8. SIDEBAR ERGONOMICS & GOVERNMENT IDENTITY
   ========================================================================== */
section[data-testid="stSidebar"] {
    width: min(300px, 85vw) !important;
    background-color: #F8FAFC !important;
    border-right: 1px solid #E2E8F0 !important;
}

section[data-testid="stSidebar"] .block-container {
    padding: 1.25rem 1rem !important;
}

/* Sidebar navigation links */
[data-testid="stSidebarNav"] a {
    color: #1E293B !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    border-radius: 4px !important;
    padding: 6px 10px !important;
}

[data-testid="stSidebarNav"] a[aria-current="page"] {
    background-color: #E2E8F0 !important;
    color: #0B2545 !important;
    font-weight: 700 !important;
    border-left: 3px solid #0B3C5D !important;
}

/* ==========================================================================
   9. STREAMLIT COLUMNS RESPONSIVENESS (Mobile Stacking & Tablet Grids)
   ========================================================================== */
/* Mobile Portrait & Small Screens (<= 768px): Stack columns vertically */
@media screen and (max-width: 768px) {
    div[data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
        flex-wrap: wrap !important;
        width: 100% !important;
        gap: 8px !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        width: 100% !important;
        min-width: 100% !important;
        flex: 1 1 100% !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        margin-bottom: 4px !important;
        min-height: 0 !important;
        height: auto !important;
    }
    .stButton > button, .stDownloadButton > button {
        width: 100% !important;
        min-height: 42px !important;
    }
}

/* Tablet Screens (769px to 1024px): Allow 2-column or 3-column wrapping */
@media screen and (min-width: 769px) and (max-width: 1024px) {
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(4)) {
        flex-wrap: wrap !important;
        gap: 12px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(4)) > div[data-testid="column"] {
        flex: 1 1 calc(50% - 12px) !important;
        min-width: calc(50% - 12px) !important;
    }
}

/* Flex helper */
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
        gap: 6px !important;
    }
    .responsive-flex > div {
        width: 100% !important;
        text-align: left !important;
        flex: none !important;
        min-height: 0 !important;
    }
}

/* ==========================================================================
   10. PLOTLY CHARTS & RESPONSIVE STATE CHART
   ========================================================================== */
.js-plotly-plot, .plot-container {
    width: 100% !important;
    max-width: 100% !important;
    background-color: #FFFFFF !important;
}

/* Desktop State Chart (> 768px): Show vertical bar chart, hide mobile horizontal chart */
@media screen and (min-width: 769px) {
    .st-key-mobile_state_chart,
    .st-key-fig_mobile_chart,
    div[data-testid="stVerticalBlock"]:has(> .st-key-mobile_state_chart),
    div[data-testid="stElementContainer"]:has(.st-key-fig_mobile_chart) {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }
    .st-key-desktop_state_chart,
    .st-key-fig_desktop_chart,
    div[data-testid="stVerticalBlock"]:has(> .st-key-desktop_state_chart),
    div[data-testid="stElementContainer"]:has(.st-key-fig_desktop_chart) {
        display: block !important;
        visibility: visible !important;
        height: auto !important;
    }
}

/* Mobile State Chart (<= 768px): Show horizontal bar chart, hide desktop vertical chart */
@media screen and (max-width: 768px) {
    .st-key-desktop_state_chart,
    .st-key-fig_desktop_chart,
    div[data-testid="stVerticalBlock"]:has(> .st-key-desktop_state_chart),
    div[data-testid="stElementContainer"]:has(.st-key-fig_desktop_chart) {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }
    .st-key-mobile_state_chart,
    .st-key-fig_mobile_chart,
    div[data-testid="stVerticalBlock"]:has(> .st-key-mobile_state_chart),
    div[data-testid="stElementContainer"]:has(.st-key-fig_mobile_chart) {
        display: block !important;
        visibility: visible !important;
        height: auto !important;
        width: 100% !important;
    }

    /* Prevent Plotly modebar from overlapping chart titles and labels on mobile */
    .st-key-mobile_state_chart .modebar-container,
    .st-key-fig_mobile_chart .modebar-container {
        top: -6px !important;
        right: 0 !important;
    }
    .st-key-mobile_state_chart .modebar-btn,
    .st-key-fig_mobile_chart .modebar-btn {
        font-size: 13px !important;
        padding: 2px 3px !important;
    }

    /* Ensure chart SVG and container occupy full width on mobile */
    .st-key-mobile_state_chart .main-svg,
    .st-key-mobile_state_chart .plot-container,
    .st-key-fig_mobile_chart .main-svg,
    .st-key-fig_mobile_chart .plot-container {
        width: 100% !important;
        max-width: 100% !important;
    }
}

/* ==========================================================================
   11. IFRAMES (Graph Visualizations)
   ========================================================================== */
iframe[title="streamlit.components.v1.html"], iframe {
    width: 100% !important;
    max-width: 100% !important;
    border-radius: 4px !important;
    border: 1px solid #CBD5E1 !important;
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
        height: 620px !important;
    }
}

.responsive-legend {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 8px 14px !important;
    background-color: #F8FAFC !important;
    border: 1px solid #CBD5E1 !important;
    padding: 10px 14px !important;
    border-radius: 4px !important;
    color: #1E293B !important;
    font-size: clamp(11.5px, 2.5vw, 13px) !important;
    margin-bottom: 12px !important;
    line-height: 1.4 !important;
}

.responsive-legend > span {
    display: inline-flex !important;
    align-items: center !important;
    white-space: nowrap !important;
}
</style>
"""


def inject_responsive_css():
    """Inject universal government regulatory portal styling across all pages."""
    st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)
