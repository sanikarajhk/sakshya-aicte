"""
Sakshya Streamlit Dashboard - Main Portal
AICTE AI-Powered Application Validation, Document Authentication & Compliance Verification
(SIH 2026 Problem Statement SIH26261)
"""

import sys
from pathlib import Path

# Automatically add repository root to sys.path for Streamlit Cloud
CURRENT_DIR = Path(__file__).resolve()
for parent in [CURRENT_DIR] + list(CURRENT_DIR.parents):
    if (parent / "sakshya").is_dir() and (parent / "sakshya" / "core").is_dir():
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))
        break

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from sakshya.core.config import settings
from sakshya.core.models import UserRole
from sakshya.core.database import get_db_context, init_db
from sakshya.core.models import ApplicationDB, FindingDB, AuditLogDB
from sakshya.core.security import DEMO_USERS, get_current_user
from sakshya.core.audit import verify_audit_chain
from sakshya.dashboard.responsive import inject_responsive_css
from sakshya.dashboard.upload_ui import render_upload_and_validation_ui

# Page setup - MUST be first Streamlit command
st.set_page_config(
    page_title="Sakshya | AICTE Verification Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Universal responsive UI styling
inject_responsive_css()

# Self-healing database check for cloud environments
with get_db_context() as db:
    init_db()
    if db.query(ApplicationDB).count() == 0:
        from sakshya.pipeline.pipeline_runner import PipelineRunner
        runner = PipelineRunner()
        runner.process_all_historical_applications()

# Sidebar: User Role Selection & Official System Identity
st.sidebar.markdown("""
<div style="padding: 4px 0 12px 0; border-bottom: 2px solid #CBD5E1; margin-bottom: 12px;">
    <div style="font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.8px; color: #64748B; font-weight: 700;">Regulatory Scrutiny System</div>
    <div style="font-size: 20px; font-weight: 800; color: #0B2545; letter-spacing: -0.2px; margin: 2px 0;">साक्ष्य • SAKSHYA</div>
    <div style="font-size: 11.5px; color: #334155; line-height: 1.35;">AICTE Institutional Scrutiny & Compliance Verification</div>
    <div style="display: inline-block; margin-top: 8px; padding: 2px 8px; background: #FFFBEB; color: #92400E; border: 1px solid #FCD34D; font-size: 10.5px; font-weight: 600; border-radius: 3px;">
        Demonstration Prototype • SIH26261
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<div style='font-size: 12px; font-weight: 700; color: #0B2545; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 4px;'>Portal Role Adjudication</div>", unsafe_allow_html=True)
selected_role = st.sidebar.selectbox(
    "Switch Portal Role",
    options=["scrutiny_officer", "institution", "admin"],
    format_func=lambda x: {
        "scrutiny_officer": "Scrutiny Officer (Bureau of Approval)",
        "institution": "Institutional Applicant (College)",
        "admin": "System Administrator (Central AICTE)"
    }[x],
    label_visibility="collapsed"
)

current_user = get_current_user(selected_role)
st.sidebar.markdown(f"""
<div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 3px; padding: 8px 10px; margin-top: 6px; font-size: 11.5px; color: #334155; line-height: 1.4;">
    <div><b>Active Officer:</b> {current_user.full_name}</div>
    <div><b>Role Designation:</b> <code>{current_user.role.value}</code></div>
</div>
""", unsafe_allow_html=True)

# Government Masthead Banner
st.markdown("""
<div class="gov-masthead">
    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #FEF3C7; font-weight: 700; margin-bottom: 4px;">
        All India Council for Technical Education • Regulatory Scrutiny Division
    </div>
    <h1 class="gov-masthead-title">साक्ष्य / SAKSHYA</h1>
    <p class="gov-masthead-subtitle">
        Institutional Application Scrutiny & Regulatory Compliance Verification Portal
    </p>
    <div class="gov-masthead-badge">
        Administrative Demonstration Staging • Synthetic Dataset of 30 Institutional Dossiers (SIH26261 Evaluation)
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# Document Upload & Targeted Regulatory Verification Section
# =============================================================================
st.markdown("""
<div class="gov-card" style="border-left: 4px solid #0B3C5D; margin-top: 6px; margin-bottom: 12px;">
    <div class="responsive-flex">
        <div style="flex: 1 1 300px;">
            <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #64748B; font-weight: 700;">Document Scrutiny Workflow</div>
            <h3 style="margin: 2px 0 6px 0; color: #0B2545;">Institutional Document Ingestion & Regulatory Scrutiny</h3>
            <p style="margin: 0; color: #475569; font-size: 13px; line-height: 1.45;">
                Upload an institutional document (PDF) to perform real-time automated verification against reference records, identify statutory defects, and scrutinize regulatory compliance.
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

col_cta_btn, col_cta_toggle = st.columns([1, 1])
with col_cta_btn:
    if st.button("Open Dedicated Application Review Page", type="primary", use_container_width=True, key="landing_upload_cta_btn"):
        st.switch_page("pages/1_Application_Review.py")
with col_cta_toggle:
    show_direct_upload = st.toggle("Direct Scrutiny: Ingest & Validate on this Landing Page", value=True, key="landing_upload_toggle")

if show_direct_upload:
    with st.container():
        render_upload_and_validation_ui(key_prefix="landing_", show_header=False)

st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

# Fetch stats from SQLite safely within active session
with get_db_context() as db:
    apps_raw = db.query(ApplicationDB).all()
    apps_data = [
        {
            "id": a.id,
            "institution_name": a.institution_name,
            "institution_type": a.institution_type,
            "state": a.state,
            "district": a.district,
            "applied_intake": a.applied_intake,
            "status": a.status.value,
            "overall_confidence": a.overall_confidence,
            "readiness_score": a.readiness_score,
            "flagged_ring": a.flagged_ring
        }
        for a in apps_raw
    ]
    total_apps = len(apps_data)
    clean_count = sum(1 for a in apps_data if a["status"] == "VERIFIED_AUTO")
    officer_count = sum(1 for a in apps_data if a["status"] == "NEEDS_OFFICER_REVIEW")
    anomaly_count = sum(1 for a in apps_data if a["status"] == "FLAGGED_ANOMALY")
    ring_count = sum(1 for a in apps_data if a["flagged_ring"])
    audit_res = verify_audit_chain(db)
    audit_valid = audit_res.get("valid", False)
    audit_records = audit_res.get("total_records", 0)

# Top KPI Metrics
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
with kpi1:
    st.metric("Total Applications", total_apps, help="Total synthetic institutional dossiers submitted")
with kpi2:
    st.metric("Auto-Verified (Clean)", clean_count, delta=f"{clean_count/total_apps*100:.0f}%", delta_color="normal")
with kpi3:
    st.metric("Needs Officer Review", officer_count, delta=f"{officer_count/total_apps*100:.0f}%", delta_color="off")
with kpi4:
    st.metric("Flagged Anomaly / Ring", anomaly_count, delta=f"{anomaly_count/total_apps*100:.0f}%", delta_color="inverse")
with kpi5:
    st.metric("Audit Chain Integrity", "VERIFIED ✅" if audit_valid else "CORRUPTED ❌", f"{audit_records} blocks")

st.markdown("---")

# Visual Analytics Row
col_chart1, col_chart2 = st.columns([1, 1])

with col_chart1:
    st.subheader("Application Status Distribution")
    status_df = pd.DataFrame([
        {"Status": "Auto-Verified (High Confidence)", "Count": clean_count},
        {"Status": "Needs Officer Review", "Count": officer_count},
        {"Status": "Flagged Anomaly / Collusion", "Count": anomaly_count},
    ])
    fig_donut = px.pie(
        status_df,
        values="Count",
        names="Status",
        color="Status",
        color_discrete_map={
            "Auto-Verified (High Confidence)": "#166534",
            "Needs Officer Review": "#D97706",
            "Flagged Anomaly / Collusion": "#B91C1C"
        },
        hole=0.45
    )
    fig_donut.update_layout(
        margin=dict(t=35, b=30, l=15, r=15),
        height=320,
        autosize=True,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Segoe UI, sans-serif", color="#1E293B", size=12),
        title=dict(text="Application Scrutiny Status Breakdown", font=dict(size=14, color="#0B2545"), x=0.02, y=0.96),
        legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5, font=dict(size=11))
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with col_chart2:
    st.subheader("State-wise Intake & Anomaly Concentration")
    state_records = [
        {
            "State": a["state"],
            "Intake": a["applied_intake"],
            "Anomaly": 1 if a["status"] == "FLAGGED_ANOMALY" else 0
        }
        for a in apps_data
    ]
    state_df = pd.DataFrame(state_records).groupby("State").agg({"Intake": "sum", "Anomaly": "sum"}).reset_index()

    # Desktop Chart (Screens > 768px): Vertical bars with horizontal bottom colorbar & clean top margin
    fig_bar = px.bar(
        state_df,
        x="State",
        y="Intake",
        color="Anomaly",
        color_continuous_scale="Reds",
        labels={"Intake": "Applied Student Seats", "Anomaly": "Flagged Dossiers"},
        title="Approved Intake vs Anomaly Concentration"
    )
    fig_bar.update_layout(
        margin=dict(t=50, b=65, l=35, r=20),
        height=340,
        autosize=True,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        xaxis_title=None,
        yaxis_title="Applied Seats",
        font=dict(family="Segoe UI, sans-serif", color="#1E293B"),
        title=dict(font=dict(size=14, color="#0B2545"), x=0.02, xanchor="left", y=0.96)
    )
    fig_bar.update_xaxes(showgrid=True, gridcolor="#F1F5F9")
    fig_bar.update_yaxes(showgrid=True, gridcolor="#F1F5F9")
    fig_bar.update_coloraxes(
        colorbar=dict(
            orientation="h",
            y=-0.28,
            yanchor="top",
            x=0.5,
            xanchor="center",
            len=0.75,
            thickness=12,
            title=dict(text="Flagged Dossiers", side="top", font=dict(size=11, color="#1E293B")),
            tickfont=dict(size=10, color="#1E293B")
        )
    )
    desktop_config = {
        "displayModeBar": "hover",
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d", "pan2d", "zoom2d", "autoScale2d"],
        "responsive": True,
    }

    # Mobile Chart (Screens <= 768px): Horizontal bar chart with horizontal state names and bottom colorbar
    state_df_sorted = state_df.sort_values("Intake", ascending=True)
    fig_bar_mobile = px.bar(
        state_df_sorted,
        y="State",
        x="Intake",
        orientation="h",
        color="Anomaly",
        color_continuous_scale="Reds",
        labels={"Intake": "Applied Student Seats", "Anomaly": "Flagged Dossiers", "State": "State"},
        title="Approved Intake vs Anomaly Concentration"
    )
    fig_bar_mobile.update_layout(
        margin=dict(t=48, b=65, l=95, r=20),
        height=390,
        autosize=True,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        yaxis_title=None,
        xaxis_title="Applied Student Seats",
        font=dict(family="Segoe UI, sans-serif", color="#1E293B"),
        title=dict(font=dict(size=13, color="#0B2545"), x=0.02, xanchor="left", y=0.97),
        yaxis=dict(tickfont=dict(size=11, color="#1E293B"), automargin=True),
        xaxis=dict(tickfont=dict(size=10, color="#1E293B"), showgrid=True, gridcolor="#F1F5F9")
    )
    fig_bar_mobile.update_coloraxes(
        colorbar=dict(
            orientation="h",
            y=-0.22,
            yanchor="top",
            x=0.5,
            xanchor="center",
            len=0.85,
            thickness=10,
            title=dict(text="Flagged Dossiers", side="top", font=dict(size=10, color="#1E293B")),
            tickfont=dict(size=9, color="#1E293B")
        )
    )
    mobile_config = {
        "displayModeBar": "hover",
        "displaylogo": False,
        "modeBarButtonsToRemove": [
            "lasso2d", "select2d", "zoom2d", "pan2d",
            "zoomIn2d", "zoomOut2d", "autoScale2d"
        ],
        "responsive": True,
    }

    with st.container(key="desktop_state_chart"):
        st.plotly_chart(fig_bar, use_container_width=True, key="fig_desktop_chart", config=desktop_config)

    with st.container(key="mobile_state_chart"):
        st.plotly_chart(fig_bar_mobile, use_container_width=True, key="fig_mobile_chart", config=mobile_config)

# Overview Applications Table
st.subheader("Institutional Applications Queue")
st.caption("Central regulatory scrutiny register for evaluating institutional applications, readiness checklists, and collusion indicators.")
app_rows = [
    {
        "Application ID": a["id"],
        "Institution Name": a["institution_name"],
        "Category": a["institution_type"],
        "State / City": f"{a['state']} ({a['district']})",
        "Status": a["status"],
        "Calibrated Confidence": f"{a['overall_confidence']:.1%}",
        "Readiness Checklist": f"{a['readiness_score']:.1f}%",
        "Collusion Ring": "Cluster Member" if a["flagged_ring"] else "Clear"
    }
    for a in apps_data
]
df_apps = pd.DataFrame(app_rows)

st.dataframe(
    df_apps,
    use_container_width=True,
    column_config={
        "Calibrated Confidence": st.column_config.ProgressColumn("Calibrated Confidence", min_value=0.0, max_value=1.0),
        "Readiness Checklist": st.column_config.ProgressColumn("Readiness Score", min_value=0.0, max_value=100.0),
    }
)

st.markdown("""
<div class="gov-notice">
    <b>Statutory Regulatory Notice & Administrative Disclaimer:</b><br>
    Sakshya anomaly indicators, ring detection clusters, and automated compliance findings are diagnostic aids intended to assist AICTE Scrutiny Officers during preliminary document examination. 
    Automated findings do not constitute conclusive statutory approval, rejection, or legal evidence of forgery. 
    Statutory authority and final adjudication remain strictly with authorized regulatory officers under AICTE Approval Process Regulations.
</div>
""", unsafe_allow_html=True)
