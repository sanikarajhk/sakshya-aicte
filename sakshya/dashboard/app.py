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

# Sidebar: User Role Selection & Portal Info
st.sidebar.image("https://upload.wikimedia.org/wikipedia/en/thumb/e/eb/All_India_Council_for_Technical_Education_logo.png/220px-All_India_Council_for_Technical_Education_logo.png", width=110)
st.sidebar.title("🛡️ Sakshya Portal")
st.sidebar.caption("AICTE SIH 2026 • PS SIH26261")

st.sidebar.markdown("---")
st.sidebar.subheader("👤 Active User Role")
selected_role = st.sidebar.selectbox(
    "Switch Portal Role",
    options=["scrutiny_officer", "institution", "admin"],
    format_func=lambda x: {
        "scrutiny_officer": "🔍 Scrutiny Officer (AICTE Bureau)",
        "institution": "🏛️ Institution Applicant (College)",
        "admin": "⚙️ System Administrator (Central AICTE)"
    }[x]
)

current_user = get_current_user(selected_role)
st.sidebar.info(f"**Logged in as:** {current_user.full_name}\n\n**Role:** `{current_user.role.value}`")

# Header Banner
st.markdown(f"""
<div class="main-header">
    <h1 style="margin: 0; font-size: 28px;">SAKSHYA: AI Document Authentication & Regulatory Scrutiny</h1>
    <p style="margin: 6px 0 0 0; opacity: 0.9; font-size: 14px;">
        All India Council for Technical Education (AICTE) • Automated Multi-Source Cross-Verification System
    </p>
    <div style="margin-top: 10px; font-size: 12px; color: #FCD34D;">
        ⚠️ SYNTHETIC DEMONSTRATION DATASET: 30 Fictional Institutional Dossiers for SIH26261 Evaluation
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# Prominent Document Upload & Targeted Validation Section
# =============================================================================
st.markdown("""
<div style="background: linear-gradient(135deg, #1E3A8A 0%, #1D4ED8 100%); color: white; padding: clamp(16px, 3vw, 22px); border-radius: 12px; margin: 18px 0 15px 0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
    <div class="responsive-flex">
        <div style="flex: 1 1 300px;">
            <h2 style="margin: 0; color: white; font-size: clamp(18px, 3.8vw, 22px);">📤 Upload & Validate Institutional Document</h2>
            <p style="margin: 6px 0 0 0; color: #E0E7FF; font-size: clamp(13px, 2.5vw, 14.5px); line-height: 1.45;">
                Upload an institutional document to check it against the college's existing records, identify compliance issues, and verify regulatory norms in real time.
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

col_cta_btn, col_cta_toggle = st.columns([1, 1])
with col_cta_btn:
    if st.button("🚀 Open Dedicated Upload & Scrutiny Page", type="primary", use_container_width=True, key="landing_upload_cta_btn"):
        st.switch_page("pages/1_Application_Review.py")
with col_cta_toggle:
    show_direct_upload = st.toggle("⚡ Direct Verification: Upload & Validate on this Landing Page", value=True, key="landing_upload_toggle")

if show_direct_upload:
    with st.container():
        render_upload_and_validation_ui(key_prefix="landing_", show_header=False)

st.markdown("---")

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
    st.subheader("📊 Application Status Distribution")
    status_df = pd.DataFrame([
        {"Status": "Auto-Verified (High Confidence)", "Count": clean_count, "Color": "#10B981"},
        {"Status": "Needs Officer Review", "Count": officer_count, "Color": "#F59E0B"},
        {"Status": "Flagged Anomaly / Collusion", "Count": anomaly_count, "Color": "#EF4444"},
    ])
    fig_donut = px.pie(
        status_df,
        values="Count",
        names="Status",
        color="Status",
        color_discrete_map={
            "Auto-Verified (High Confidence)": "#10B981",
            "Needs Officer Review": "#F59E0B",
            "Flagged Anomaly / Collusion": "#EF4444"
        },
        hole=0.45
    )
    fig_donut.update_layout(
        margin=dict(t=25, b=25, l=15, r=15),
        height=320,
        autosize=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with col_chart2:
    st.subheader("📈 State-wise Intake & Anomaly Rate")
    state_records = [
        {
            "State": a["state"],
            "Intake": a["applied_intake"],
            "Anomaly": 1 if a["status"] == "FLAGGED_ANOMALY" else 0
        }
        for a in apps_data
    ]
    state_df = pd.DataFrame(state_records).groupby("State").agg({"Intake": "sum", "Anomaly": "sum"}).reset_index()
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
        margin=dict(t=25, b=25, l=15, r=15),
        height=320,
        autosize=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# Overview Applications Table
st.subheader("📋 Institutional Applications Queue")
app_rows = [
    {
        "Application ID": a["id"],
        "Institution Name": a["institution_name"],
        "Category": a["institution_type"],
        "State / City": f"{a['state']} ({a['district']})",
        "Status": a["status"],
        "Calibrated Confidence": f"{a['overall_confidence']:.1%}",
        "Readiness Checklist": f"{a['readiness_score']:.1f}%",
        "Collusion Ring": "⚠️ Cluster Member" if a["flagged_ring"] else "Clear"
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

st.markdown("---")
st.info("""
**Regulatory Disclaimer & AI Safety:**  
Sakshya anomaly and ring-detection findings are preliminary indicators designed to assist regulatory scrutiny. 
They do not constitute automated proof of forgery or statutory rejection. 
Final regulatory approval or rejection remains strictly with authorized AICTE Scrutiny Officers.
""")
