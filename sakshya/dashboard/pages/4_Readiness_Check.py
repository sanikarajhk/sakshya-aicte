"""
Sakshya Dashboard - Institution Pre-Submission Readiness Check
Calculates regulatory completeness checklist score using an explicit formula.
Transparently displays missing documents, expiry warnings, and pre-submission checks.
"""

import streamlit as st
import pandas as pd
from sakshya.core.database import get_db_context
from sakshya.core.models import ApplicationDB, DocumentDB, FindingDB
from sakshya.pipeline.readiness import ReadinessEvaluator
from sakshya.data_generator.ground_truth import load_ground_truth

st.set_page_config(page_title="Readiness Check | Sakshya", page_icon="📋", layout="wide")

st.title("📋 Institutional Pre-Submission Readiness Checklist")
st.caption("Self-audit tool for applicant institutions to diagnose missing documents, lapsed certificates, and data conflicts.")

st.info("""
**Important Regulatory Notice:**  
Any readiness score generated on this page uses an **explicit checklist formula** measuring document completeness.  
**This score DOES NOT represent the probability of statutory AICTE approval.**
""")

gt = load_ground_truth()
app_ids = list(gt.keys())

selected_app_id = st.selectbox("Select Institution Dossier to Inspect", app_ids, index=0)
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
        "Readiness Score",
        f"{readiness_res.readiness_score:.1f} / 100",
        help="Formula: Score = (Sum of Passed Checklist Weights / Total Weight 100) * 100"
    )

with col_status:
    if readiness_res.is_ready_for_submission:
        st.success(f"### ✅ READY FOR FORMAL SUBMISSION\n{readiness_res.summary}")
    else:
        st.warning(f"### ⚠️ DEFICIENCIES DETECTED — REVISION REQUIRED\n{readiness_res.summary}")

st.markdown("---")

# Formula Breakdown Card
st.subheader("📐 Explicit Mathematical Checklist Formula")
st.latex(r"\text{Readiness Score} = \left( \frac{\sum_{i=1}^{N} (w_i \times \text{Pass}_i)}{\sum_{i=1}^{N} w_i} \right) \times 100")

# Detailed Checklist Table
st.subheader("Audit Checklist Breakdown")
checklist_rows = []
for item in readiness_res.checklist:
    checklist_rows.append({
        "Checklist Item": item.check_name,
        "Category": item.category,
        "Status": "✅ PASS" if item.status else "❌ DEFICIENCY",
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
