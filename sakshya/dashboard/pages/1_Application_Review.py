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

st.set_page_config(page_title="Application Review | Sakshya", page_icon="⚖️", layout="wide")
inject_responsive_css()

# Government Masthead Banner
st.markdown("""
<div class="gov-masthead">
    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #FEF3C7; font-weight: 700; margin-bottom: 4px;">
        All India Council for Technical Education • Approval Bureau
    </div>
    <h1 class="gov-masthead-title">Institutional Application Review & Scrutiny</h1>
    <p class="gov-masthead-subtitle">
        Automated regulatory compliance validation, claim-evidence cross-verification, and institutional dossier examination
    </p>
</div>
""", unsafe_allow_html=True)

gt = load_ground_truth()
app_ids = list(gt.keys())

# Top-level tabs: Upload & Validate vs Browse Dossiers
tab_upload, tab_dossier = st.tabs([
    "Upload & Validate Institutional Document",
    "Inspect Registered 30-College Dossiers"
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
    st.subheader("Registered Institution Dossier Scrutiny")
    st.caption("Inspect submitted dossiers, evidentiary claim linkages, compliance audit logs, and external authority records.")

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
    status_badge_class = {
        "VERIFIED_AUTO": "gov-badge-verified",
        "NEEDS_OFFICER_REVIEW": "gov-badge-review",
        "FLAGGED_ANOMALY": "gov-badge-flagged",
        "OFFICER_APPROVED": "gov-badge-info",
        "OFFICER_REJECTED": "gov-badge-neutral"
    }.get(app_db["status"], "gov-badge-neutral")

    status_border_color = {
        "VERIFIED_AUTO": "#166534",
        "NEEDS_OFFICER_REVIEW": "#D97706",
        "FLAGGED_ANOMALY": "#B91C1C",
        "OFFICER_APPROVED": "#1E40AF",
        "OFFICER_REJECTED": "#64748B"
    }.get(app_db["status"], "#64748B")

    st.markdown(f"""
    <div class="gov-card" style="border-left: 5px solid {status_border_color}; margin-bottom: 16px;">
        <div class="responsive-flex">
            <div style="flex: 1 1 280px;">
                <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #64748B; font-weight: 700;">Institutional Profile</div>
                <h2 style="margin: 2px 0 4px 0; color: #0B2545; font-size: clamp(17px, 3.5vw, 21px);">{app_db['institution_name']} ({app_db['id']})</h2>
                <p style="margin: 0; color: #334155; font-size: 13px; line-height: 1.45;">Category: <b>{app_db['institution_type']}</b> • Location: <b>{app_db['district']}, {app_db['state']}</b> • Applied Intake: <b>{app_db['applied_intake']} Seats</b></p>
            </div>
            <div style="flex: 0 0 auto; text-align: right;">
                <span class="gov-badge {status_badge_class}" style="font-size: 12px; padding: 4px 12px;">
                    {app_db['status']}
                </span>
                <div style="margin-top: 5px; font-size: 12px; color: #475569;">Calibrated Confidence: <b>{app_db['overall_confidence']:.1%}</b></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs: Findings, Documents & Claims, Pre-Submission Readiness
    tab_findings, tab_docs, tab_claims, tab_mock = st.tabs([
        "Statutory Findings & Violations",
        "Submitted Documents & Cryptographic Hashes",
        "Extracted Claims & Baseline Data",
        "Issuing Authority Records"
    ])

    with tab_findings:
        st.subheader(f"Statutory Findings & Rule Violations ({len(findings_db)})")
        if not findings_db:
            st.success("No statutory non-compliance or document discrepancies detected. Institutional dossier is clean.")
        else:
            for f in findings_db:
                sev_badge = {
                    "CRITICAL": "background-color: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5;",
                    "HIGH": "background-color: #FEF3C7; color: #92400E; border: 1px solid #FCD34D;",
                    "MEDIUM": "background-color: #E0E7FF; color: #1E40AF; border: 1px solid #93C5FD;",
                    "INFO": "background-color: #F1F5F9; color: #475569; border: 1px solid #CBD5E1;"
                }.get(f["severity"], "")

                claims_list = f["evidence_claims"]

                st.markdown(f"""
                <div class="gov-card" style="border-left: 4px solid #B91C1C; margin-bottom: 12px;">
                    <div class="responsive-flex">
                        <b style="font-size: 14.5px; color: #0B2545; flex: 1 1 200px;">{f['title']}</b>
                        <span style="{sev_badge} padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 700; white-space: nowrap;">
                            {f['severity']}
                        </span>
                    </div>
                    <p style="margin: 8px 0; color: #334155; font-size: 13.5px; line-height: 1.45;">{f['description']}</p>
                    <div style="font-size: 12px; color: #475569; line-height: 1.5; background: #F8FAFC; padding: 6px 10px; border-radius: 3px; border: 1px solid #E2E8F0;">
                        <b>Rule Identifier:</b> <code>{f['rule_id'] or 'SYSTEM_CHECK'}</code> • <b>Document Scope:</b> <code>{f['document_id'] or 'Application Master'}</code>
                    </div>
                    {"<div style='margin-top: 6px; padding: 6px 10px; background-color: #F8FAFC; border-radius: 3px; font-size: 12px; border: 1px solid #E2E8F0;'><b>Evidentiary Claims:</b> " + " | ".join(claims_list) + "</div>" if claims_list else ""}
                    <div style="margin-top: 8px; font-size: 12.5px; color: #0B3C5D;">
                        <b>Recommended Scrutiny Action:</b> {f['recommended_action']}
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
