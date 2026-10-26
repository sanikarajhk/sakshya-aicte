"""
Sakshya Dashboard - Application Review & Document Verification Portal
Provides dual functionality:
1. Live Document Ingestion & Targeted Regulatory Validation against the 30-College Dataset.
2. Complete Historical Dossier Review of all 30 Registered Institutions.
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
import json
import pandas as pd
from sakshya.core.database import get_db_context
from sakshya.core.models import ApplicationDB, DocumentDB, FindingDB, ExtractedFieldDB, DocumentType
from sakshya.data_generator.ground_truth import load_ground_truth
from sakshya.dashboard.responsive import inject_responsive_css
from sakshya.dashboard.upload_ui import render_upload_and_validation_ui

st.set_page_config(page_title="Application Review | Sakshya", page_icon="📄", layout="wide")
inject_responsive_css()

st.title("📄 AICTE Institutional Application & Document Verification")
st.caption("AI-powered statutory compliance validation, claim-evidence cross-verification, and dossier scrutiny.")

gt = load_ground_truth()
app_ids = list(gt.keys())

# Top-level tabs: Upload & Validate vs Browse Dossiers
tab_upload, tab_dossier = st.tabs([
    "📤 Upload & Validate Institutional Document",
    "📋 Inspect Registered 30-College Dossiers"
])

# =============================================================================
# TAB 1: Live Document Upload & Targeted College Verification
# =============================================================================
with tab_upload:
    render_upload_and_validation_ui(key_prefix="review_", show_header=True)


# =============================================================================
# TAB 2: Historical Dossier Review of all 30 Registered Institutions
# =============================================================================
with tab_dossier:
    st.subheader("📋 Inspect Registered 30-College Dossiers")
    st.caption("Review existing applications, documentary evidence claims, planted ground-truth defects, and authority records.")

    # Select application
    selected_app_id = st.selectbox("Select Application to Inspect", app_ids, index=0, key="dossier_app_select")

    with get_db_context() as db:
        app_raw = db.query(ApplicationDB).filter_by(id=selected_app_id).first()
        if not app_raw:
            st.error("Application record not found in database.")
            st.stop()

        app_db = {
            "id": app_raw.id,
            "institution_name": app_raw.institution_name,
            "institution_type": app_raw.institution_type,
            "state": app_raw.state,
            "district": app_raw.district,
            "applied_intake": app_raw.applied_intake,
            "status": app_raw.status.value,
            "overall_confidence": app_raw.overall_confidence,
            "readiness_score": app_raw.readiness_score,
            "survey_number": app_raw.survey_number,
            "land_area_acres": app_raw.land_area_acres,
            "society_trust_name": app_raw.society_trust_name,
            "architect_license": app_raw.architect_license,
            "notary_registration": app_raw.notary_registration
        }

        docs_db = [
            {
                "id": d.id,
                "document_type": d.document_type.value,
                "filename": d.filename,
                "file_path": d.file_path,
                "file_hash": d.file_hash,
                "perceptual_hash": d.perceptual_hash,
                "issuer_status": d.issuer_status.value,
                "expiry_date": d.expiry_date
            }
            for d in db.query(DocumentDB).filter_by(application_id=selected_app_id).all()
        ]

        findings_db = [
            {
                "id": f.id,
                "title": f.title,
                "description": f.description,
                "severity": f.severity.value,
                "code": f.code,
                "rule_id": f.rule_id,
                "document_id": f.document_id,
                "evidence_claims": json.loads(f.evidence_claims) if f.evidence_claims else [],
                "recommended_action": f.recommended_action
            }
            for f in db.query(FindingDB).filter_by(application_id=selected_app_id).all()
        ]

    # Header status row
    status_color = {
        "VERIFIED_AUTO": "#10B981",
        "NEEDS_OFFICER_REVIEW": "#F59E0B",
        "FLAGGED_ANOMALY": "#EF4444",
        "OFFICER_APPROVED": "#3B82F6",
        "OFFICER_REJECTED": "#6B7280"
    }.get(app_db["status"], "#6B7280")

    st.markdown(f"""
    <div style="background-color: #F8FAFC; border-left: 6px solid {status_color}; padding: clamp(12px, 3vw, 18px); border-radius: 10px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div class="responsive-flex">
            <div style="flex: 1 1 280px;">
                <h2 style="margin: 0; color: #1E293B; font-size: clamp(17px, 3.8vw, 22px);">{app_db['institution_name']} ({app_db['id']})</h2>
                <p style="margin: 6px 0 0 0; color: #64748B; font-size: clamp(12px, 2.5vw, 13.5px); line-height: 1.4;">Category: <b>{app_db['institution_type']}</b> • Location: <b>{app_db['district']}, {app_db['state']}</b> • Applied Intake: <b>{app_db['applied_intake']} Seats</b></p>
            </div>
            <div style="flex: 0 0 auto; text-align: right;">
                <span style="background-color: {status_color}; color: white; padding: 6px 14px; border-radius: 16px; font-weight: bold; font-size: clamp(12px, 2.5vw, 13.5px); display: inline-block;">
                    {app_db['status']}
                </span>
                <div style="margin-top: 6px; font-size: clamp(11.5px, 2.2vw, 13px); color: #475569;">Calibrated Confidence: <b>{app_db['overall_confidence']:.1%}</b></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs: Findings, Documents & Claims, Pre-Submission Readiness
    tab_findings, tab_docs, tab_claims, tab_mock = st.tabs([
        "⚠️ Evidence-Linked Findings",
        "📁 Submitted Documents & Hashes",
        "📑 Extracted Claims & Ground Truth",
        "🏛️ Authority Verification Records"
    ])

    with tab_findings:
        st.subheader(f"Statutory Findings & Rule Violations ({len(findings_db)})")
        if not findings_db:
            st.success("✅ No statutory non-compliance or document contradictions detected. Dossier is clean.")
        else:
            for f in findings_db:
                sev_badge = {
                    "CRITICAL": "background-color: #FEE2E2; color: #991B1B; border: 1px solid #F87171;",
                    "HIGH": "background-color: #FEF3C7; color: #92400E; border: 1px solid #FCD34D;",
                    "MEDIUM": "background-color: #E0E7FF; color: #3730A3; border: 1px solid #A5B4FC;",
                    "INFO": "background-color: #F1F5F9; color: #475569; border: 1px solid #CBD5E1;"
                }.get(f["severity"], "")

                claims_list = f["evidence_claims"]

                st.markdown(f"""
                <div style="background-color: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: clamp(10px, 2.5vw, 16px); margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); word-break: break-word;">
                    <div class="responsive-flex">
                        <b style="font-size: clamp(14px, 3vw, 16px); color: #0F172A; flex: 1 1 200px;">{f['title']}</b>
                        <span style="{sev_badge} padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; white-space: nowrap;">
                            {f['severity']}
                        </span>
                    </div>
                    <p style="margin: 8px 0; color: #334155; font-size: clamp(12.5px, 2.5vw, 14px); line-height: 1.45;">{f['description']}</p>
                    <div style="font-size: 12px; color: #64748B; line-height: 1.5; word-break: break-word;">
                        <b>Rule Ref:</b> <code>{f['rule_id'] or 'SYSTEM_CHECK'}</code> • <b>Document:</b> <code>{f['document_id'] or 'Application Master'}</code>
                    </div>
                    {"<div style='margin-top: 6px; padding: 6px 10px; background-color: #F8FAFC; border-radius: 4px; font-size: 12px; line-height: 1.4; word-break: break-word;'><b>Evidentiary Claims:</b> " + " | ".join(claims_list) + "</div>" if claims_list else ""}
                    <div style="margin-top: 8px; font-size: 12.5px; color: #0369A1; line-height: 1.4;">
                        <b>Recommended Action:</b> {f['recommended_action']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with tab_docs:
        st.subheader(f"Submitted Institutional Documents ({len(docs_db)})")
        for d in docs_db:
            col_d1, col_d2, col_d3 = st.columns([3, 2, 2])
            with col_d1:
                st.markdown(f"**{d['document_type']}**  \n`{d['filename']}`")
            with col_d2:
                st.caption(f"SHA-256 Hash: `{d['file_hash'][:16]}...`  \nPerceptual Hash: `{d['perceptual_hash']}`")
            with col_d3:
                st.markdown(f"Authority Status: `{d['issuer_status']}`  \nExpiry: `{d['expiry_date'] or 'N/A'}`")
            
            # Download / View button
            doc_path = Path(d["file_path"])
            if not doc_path.exists():
                from sakshya.core.config import DATA_DIR
                doc_path = DATA_DIR / "synthetic_applications" / selected_app_id / d["filename"]
            if doc_path.exists():
                with open(doc_path, "rb") as f_bytes:
                    st.download_button(
                        label=f"⬇️ Download {d['filename']}",
                        data=f_bytes.read(),
                        file_name=d["filename"],
                        mime="application/pdf" if d["filename"].endswith(".pdf") else "image/png",
                        key=f"dl_{d['id']}",
                        use_container_width=True
                    )
            st.markdown("---")

    with tab_claims:
        st.subheader("Extracted Entity Claims vs Ground Truth")
        gt_app = gt.get(selected_app_id, {})
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("**Core Application Data:**")
            st.json({
                "Institution": app_db["institution_name"],
                "Sponsoring Society": app_db["society_trust_name"],
                "Survey Plot": app_db["survey_number"],
                "Campus Land (Acres)": app_db["land_area_acres"],
                "Architect License": app_db["architect_license"],
                "Notary Registration": app_db["notary_registration"]
            })
        with col_c2:
            st.markdown("**Ground-Truth Planted Attributes:**")
            st.json({
                "Clean Baseline": gt_app.get("is_clean"),
                "Injected Defects": gt_app.get("injected_defects"),
                "Collusion Ring Member": gt_app.get("flagged_ring"),
                "Expected Routing Status": gt_app.get("expected_status")
            })

    with tab_mock:
        st.subheader("External Statutory Authority Verification Registry")
        mock_registry = load_ground_truth()
        app_mock = gt_app.get("documents", [])
        st.markdown("Simulated live verification responses across State Land, Municipal, and Fire registries:")
        for d in app_mock:
            st.info(f"**{d['document_type']}** (`{d['filename']}`) → Issuer Status: **`{d['issuer_status']}`**")
