"""
Sakshya Dashboard - Institution Pre-Submission Readiness Check
Calculates regulatory completeness checklist score using an explicit formula.
Transparently displays missing documents, expiry warnings, and pre-submission checks.
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
from sakshya.core.database import get_db_context
from sakshya.core.models import ApplicationDB, DocumentDB, FindingDB
from sakshya.pipeline.readiness import ReadinessEvaluator
from sakshya.data_generator.ground_truth import load_ground_truth
from sakshya.dashboard.responsive import inject_responsive_css

st.set_page_config(page_title="Readiness Check | Sakshya", page_icon="⚖️", layout="wide")
inject_responsive_css()

# Government Masthead Banner
st.markdown("""
<div class="gov-masthead">
    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #FEF3C7; font-weight: 700; margin-bottom: 4px;">
        All India Council for Technical Education • Pre-Scrutiny Verification
    </div>
    <h1 class="gov-masthead-title">Institutional Pre-Submission Readiness Checklist</h1>
    <p class="gov-masthead-subtitle">
        Diagnostic self-audit portal for applicant institutions to evaluate document completeness, certificate validity, and statutory compliance prior to formal scrutiny
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="gov-notice">
    <b>Statutory Regulatory Notice:</b><br>
    The readiness score generated on this page is evaluated strictly through an explicit completeness formula measuring submitted document items. 
    <b>This diagnostic score DOES NOT constitute approval or prejudice the statutory discretion of AICTE Scrutiny Officers.</b>
</div>
""", unsafe_allow_html=True)

gt = load_ground_truth()
app_ids = list(gt.keys())

selected_app_id = st.selectbox("Select Registered Institutional Dossier to Inspect", app_ids, index=0)
app_data = gt[selected_app_id]

# Fetch findings and documents from DB
from sakshya.core.models import Finding, FindingSeverity

findings = []
with get_db_context() as db:
    findings_raw = db.query(FindingDB).filter_by(application_id=selected_app_id).all()
    for f in findings_raw:
        findings.append(Finding(
            code=f.code,
            severity=f.severity,
            title=f.title,
            description=f.description,
            source_document=f.document_id,
            rule_id=f.rule_id,
            is_anomaly=f.is_anomaly,
            is_contradiction=f.is_contradiction
        ))

# Run readiness evaluator
evaluator = ReadinessEvaluator()
readiness_res = evaluator.evaluate_readiness(
    application_data=app_data,
    documents=app_data.get("documents", []),
    findings=findings,
    issuer_statuses=[]
)

# Header KPI
col_score, col_status = st.columns([1, 2])
with col_score:
    st.metric(
        "Completeness Readiness Score",
        f"{readiness_res.readiness_score:.1f} / 100",
        help="Formula: Score = (Sum of Passed Checklist Weights / Total Weight 100) * 100"
    )

with col_status:
    if readiness_res.is_ready_for_submission:
        st.markdown(f"""
        <div class="gov-card" style="border-left: 5px solid #166534; margin: 0; padding: 12px 16px;">
            <span class="gov-badge gov-badge-verified">Dossier Compliant</span>
            <h3 style="margin: 4px 0 2px 0; color: #166534;">Dossier Satisfies Pre-Submission Checklist</h3>
            <p style="margin: 0; color: #334155; font-size: 13px;">{readiness_res.summary}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="gov-card" style="border-left: 5px solid #D97706; margin: 0; padding: 12px 16px;">
            <span class="gov-badge gov-badge-review">Deficiencies Identified</span>
            <h3 style="margin: 4px 0 2px 0; color: #92400E;">Deficiencies Detected — Revision Required</h3>
            <p style="margin: 0; color: #334155; font-size: 13px;">{readiness_res.summary}</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

# Formula Breakdown Card
st.subheader("Mathematical Checklist Evaluation Formula")
st.markdown('<div style="overflow-x: auto; max-width: 100%; padding: 6px 0;">', unsafe_allow_html=True)
st.latex(r"\text{Readiness Score} = \left( \frac{\sum_{i=1}^{N} (w_i \times \text{Pass}_i)}{\sum_{i=1}^{N} w_i} \right) \times 100")
st.markdown('</div>', unsafe_allow_html=True)

# Detailed Checklist Table
st.subheader("Statutory Checklist Evaluation Breakdown")
checklist_rows = []
for item in readiness_res.checklist:
    checklist_rows.append({
        "Checklist Item": item.check_name,
        "Category": item.category,
        "Status": "PASSED" if item.status else "DEFICIENCY",
        "Assigned Weight": f"{item.weight:.0f} pts",
        "Earned Score": f"{item.score:.0f} pts",
        "Audit Findings & Guidance": item.details
    })

df_checklist = pd.DataFrame(checklist_rows)
st.dataframe(
    df_checklist,
    use_container_width=True,
    column_config={
        "Status": st.column_config.TextColumn("Status", width="medium"),
        "Audit Findings & Guidance": st.column_config.TextColumn("Regulatory Guidance", width="large")
    }
)
