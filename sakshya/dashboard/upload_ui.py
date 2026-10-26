"""
Sakshya Reusable Document Upload & Targeted Validation UI Component
Shared across the Main Landing Page (app.py) and Application Review (1_Application_Review.py).
Ensures zero code duplication and 100% consistent regulatory validation behavior.
"""

from pathlib import Path
from typing import Optional
import streamlit as st
import pandas as pd

from sakshya.data_generator.ground_truth import load_ground_truth
from sakshya.core.models import DocumentType
from sakshya.pipeline.single_doc_validator import (
    SingleDocValidator, IdentificationStatus, CheckStatus
)


def render_upload_and_validation_ui(key_prefix: str = "", show_header: bool = True):
    """
    Renders the complete document upload, college identification,
    targeted regulatory compliance validation, and evidentiary findings UI.
    """
    gt = load_ground_truth()
    app_ids = list(gt.keys())
    validator = SingleDocValidator(ground_truth=gt)

    if show_header:
        st.subheader("Upload & Validate Institutional Document")
        st.markdown(
            "Upload an institutional regulatory document (PDF) to scrutinize compliance against reference college records, "
            "statutory requirements, and AICTE approval norms."
        )

    # 1. File Uploader Widget
    uploaded_file = st.file_uploader(
        "Select Institutional PDF Document for Scrutiny",
        type=["pdf"],
        key=f"{key_prefix}pdf_uploader",
        help="Upload a digital or scanned regulatory PDF. Processing occurs securely in memory without modifying the synthetic dataset."
    )

    # 2. Quick sample document selector for instant testing
    with st.expander("Administrative Test Repository — Pre-generated Institutional Samples"):
        sample_options = [
            "-- Select an institutional sample document --",
            "APP-001: Land Title Deed (Clean / Valid)",
            "APP-001: Building Plan Approval Order",
            "APP-001: Fire Safety Certificate",
            "APP-001: Mandatory Disclosure",
            "APP-002: Land Title Deed (Saraswati College)",
            "APP-003: Land Title Deed (Kaveri Academy)",
            "APP-007: Land Title Deed (Collusion Ring Member)",
            "APP-021: Land Title Deed (Planted Contradiction)"
        ]
        sample_choice = st.selectbox(
            "Pre-generated test document:",
            sample_options,
            index=0,
            key=f"{key_prefix}sample_doc_choice"
        )

    # Determine file bytes source
    file_bytes = None
    filename = ""

    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        filename = uploaded_file.name
    elif sample_choice != "-- Select an institutional sample document --":
        sample_app_id = sample_choice.split(":")[0].strip()
        doc_keyword = sample_choice.split(":")[1].lower()
        if sample_app_id in gt:
            for d in gt[sample_app_id].get("documents", []):
                fn = d.get("filename", "")
                if ("land" in doc_keyword and "land" in fn.lower()) or \
                   ("building" in doc_keyword and "building" in fn.lower()) or \
                   ("fire" in doc_keyword and "fire" in fn.lower()) or \
                   ("mandatory" in doc_keyword and "mandatory" in fn.lower()):
                    sample_path = Path(d.get("file_path", ""))
                    if not sample_path.exists():
                        from sakshya.core.config import DATA_DIR
                        sample_path = DATA_DIR / "synthetic_applications" / sample_app_id / fn
                    if sample_path.exists():
                        with open(sample_path, "rb") as sf:
                            file_bytes = sf.read()
                        filename = fn
                        break

    if file_bytes is None:
        st.info("Select or upload an institutional PDF document above to initiate regulatory verification.")
        return

    st.markdown("<hr style='margin: 14px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
    # Step 1: Validate PDF Format and Read in Memory
    with st.spinner("Validating PDF integrity and parsing document content..."):
        is_valid, err_msg, metadata = validator.validate_pdf_bytes(file_bytes, filename)

    if not is_valid:
        st.error(f"Invalid Document: {err_msg}")
        return

    # Display File Metadata Bar
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        st.metric("Document Filename", filename)
    with col_f2:
        st.metric("File Size", f"{metadata['file_size'] / 1024:.1f} KB")
    with col_f3:
        st.metric("Page Count", f"{metadata['page_count']} Page(s)")
    with col_f4:
        st.metric("SHA-256 Hash", f"{metadata['sha256'][:16]}...")

    # Step 2: College Identification
    with st.spinner("Extracting regulatory claims and matching against 30 registered institutions..."):
        ident = validator.identify_college(metadata["full_text"], metadata["filename"], metadata.get("qr_content"))

    target_app_id = None
    is_identification_uncertain = False

    if ident.status == IdentificationStatus.EXACT_MATCH:
        target_app_id = ident.identified_app_id
        st.markdown(f"""
        <div style="background-color: #F0FDF4; border: 1px solid #BBF7D0; border-left: 4px solid #166534; padding: 12px 16px; border-radius: 4px; margin: 10px 0;">
            <div class="responsive-flex">
                <div style="font-weight: 700; color: #166534; font-size: 14px;">Target Institution Identified: {ident.identified_name} ({target_app_id})</div>
                <span class="gov-badge gov-badge-verified">Exact Match (100%)</span>
            </div>
            <div style="font-size: 12.5px; color: #334155; margin-top: 5px;">
                <b>Method:</b> {ident.method} • <b>Details:</b> {ident.explanation}
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif ident.status == IdentificationStatus.HIGH_CONFIDENCE_FUZZY:
        target_app_id = ident.identified_app_id
        st.markdown(f"""
        <div style="background-color: #EFF6FF; border: 1px solid #BFDBFE; border-left: 4px solid #1D4ED8; padding: 12px 16px; border-radius: 4px; margin: 10px 0;">
            <div class="responsive-flex">
                <div style="font-weight: 700; color: #1E40AF; font-size: 14px;">Target Institution Identified: {ident.identified_name} ({target_app_id})</div>
                <span class="gov-badge gov-badge-info">Fuzzy Match ({ident.confidence:.1%})</span>
            </div>
            <div style="font-size: 12.5px; color: #334155; margin-top: 5px;">
                <b>Method:</b> {ident.method} • <b>Details:</b> {ident.explanation}
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif ident.status == IdentificationStatus.AMBIGUOUS_MATCH:
        is_identification_uncertain = True
        st.markdown(f"""
        <div style="background-color: #FFFBEB; border: 1px solid #FDE68A; border-left: 4px solid #D97706; padding: 12px 16px; border-radius: 4px; margin: 10px 0;">
            <div class="responsive-flex">
                <div style="font-weight: 700; color: #92400E; font-size: 14px;">Ambiguous Institutional Match (Confidence: {ident.confidence:.1%})</div>
                <span class="gov-badge gov-badge-review">Officer Discretion Required</span>
            </div>
            <div style="font-size: 12.5px; color: #334155; margin-top: 5px;">{ident.explanation}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("**Candidate Matches:**")
        cand_df = pd.DataFrame([c.dict() for c in ident.top_candidates])
        st.table(cand_df)

        target_app_id = st.selectbox(
            "Select the intended registered institution to validate this document against:",
            options=app_ids,
            index=app_ids.index(ident.top_candidates[0].application_id) if ident.top_candidates else 0,
            format_func=lambda x: f"{x} — {gt[x]['institution_name']} ({gt[x]['district']}, {gt[x]['state']})",
            key=f"{key_prefix}ambig_college_choice"
        )
    elif ident.status == IdentificationStatus.UNKNOWN_COLLEGE:
        is_identification_uncertain = True
        st.markdown(f"""
        <div style="background-color: #FEF2F2; border: 1px solid #FECACA; border-left: 4px solid #B91C1C; padding: 12px 16px; border-radius: 4px; margin: 10px 0;">
            <div class="responsive-flex">
                <div style="font-weight: 700; color: #991B1B; font-size: 14px;">Unregistered Institution Detected</div>
                <span class="gov-badge gov-badge-flagged">Unlisted Entity</span>
            </div>
            <div style="font-size: 12.5px; color: #334155; margin-top: 5px;">{ident.explanation}</div>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Regulatory Boundary: Unlisted colleges cannot be attributed to an arbitrary registered institution without official declaration.")

        exp_compare = st.checkbox(
            "Select an existing college to run targeted comparison for audit/experimental scrutiny",
            key=f"{key_prefix}exp_compare_chk"
        )
        if exp_compare:
            target_app_id = st.selectbox(
                "Select Registered Institutional Profile to Validate Against:",
                options=app_ids,
                index=0,
                format_func=lambda x: f"{x} — {gt[x]['institution_name']}",
                key=f"{key_prefix}unknown_manual_choice"
            )
        else:
            target_app_id = None

    # Option to override identified college if user wishes
    if target_app_id and not is_identification_uncertain:
        with st.expander("⚙️ Need to validate against a different college? (Manual Override)"):
            override_app = st.selectbox(
                "Change Target College for Scrutiny:",
                options=app_ids,
                index=app_ids.index(target_app_id),
                format_func=lambda x: f"{x} — {gt[x]['institution_name']}",
                key=f"{key_prefix}manual_override_select"
            )
            if override_app != target_app_id:
                target_app_id = override_app
                st.info(f"Target changed to: **{gt[target_app_id]['institution_name']}** (`{target_app_id}`)")

    # Step 3: Run Targeted Validation
    if target_app_id:
        doc_type = validator.infer_document_type(metadata["full_text"], metadata["filename"])

        col_dt1, col_dt2 = st.columns([3, 2])
        with col_dt1:
            st.caption(f"Target College Profile: **{gt[target_app_id]['institution_name']}** (`{target_app_id}`)")
        with col_dt2:
            st.caption(f"Inferred Document Category: **`{doc_type.value}`**")

        with st.spinner(f"Executing targeted compliance checks strictly against {target_app_id}..."):
            res = validator.validate_document_against_college(
                college_id=target_app_id,
                doc_type=doc_type,
                filename=filename,
                metadata=metadata
            )

        # Overall Result Banner
        status_badge_class = {
            "VERIFIED_AUTO": "gov-badge-verified",
            "NEEDS_OFFICER_REVIEW": "gov-badge-review",
            "FLAGGED_ANOMALY": "gov-badge-flagged"
        }.get(res.overall_status, "gov-badge-neutral")

        status_border_color = {
            "VERIFIED_AUTO": "#166534",
            "NEEDS_OFFICER_REVIEW": "#D97706",
            "FLAGGED_ANOMALY": "#B91C1C"
        }.get(res.overall_status, "#64748B")

        st.markdown(f"""
        <div class="gov-card" style="border-left: 5px solid {status_border_color}; margin: 12px 0 16px 0;">
            <div class="responsive-flex">
                <div style="flex: 1 1 280px;">
                    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #64748B; font-weight: 700;">Regulatory Scrutiny Outcome</div>
                    <h3 style="margin: 2px 0 4px 0; color: #0B2545;">{res.college_name} ({res.college_id})</h3>
                    <p style="margin: 0; color: #334155; font-size: 13px;">
                        Scrutiny Finding: <b>{res.summary}</b>
                    </p>
                </div>
                <div style="flex: 0 0 auto; text-align: right;">
                    <span class="gov-badge {status_badge_class}" style="font-size: 12px; padding: 4px 12px;">
                        {res.overall_status}
                    </span>
                    <div style="margin-top: 5px; font-size: 12px; color: #475569;">
                        Calibrated Confidence: <b>{res.calibrated_confidence:.1%}</b>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Check breakdown metrics
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        with m_c1:
            st.metric("Passed Statutory Checks", len(res.passed_checks))
        with m_c2:
            st.metric("Discrepancies & Violations", len(res.mismatches), delta=f"-{len(res.mismatches)}" if res.mismatches else None, delta_color="inverse")
        with m_c3:
            st.metric("Missing Regulatory Fields", len(res.missing_info))
        with m_c4:
            st.metric("Unverified Claims", len(res.unverified))

        # Result Tabs: Mismatches, Passed, Missing, Extracted Fields, Authority Records
        res_tab_mismatch, res_tab_passed, res_tab_missing, res_tab_fields, res_tab_auth = st.tabs([
            f"Discrepancies & Findings ({len(res.mismatches)})",
            f"Passed Statutory Checks ({len(res.passed_checks)})",
            f"Missing & Unverified ({len(res.missing_info) + len(res.unverified)})",
            f"Extracted Regulatory Claims ({len(res.extracted_fields)})",
            "Issuing Authority Verification"
        ])

        with res_tab_mismatch:
            st.subheader(f"Statutory Violations & Discrepancies ({len(res.mismatches)})")
            if not res.mismatches:
                st.success("Zero statutory discrepancies detected. All extracted claims align with reference records.")
            else:
                for m in res.mismatches:
                    sev_badge = {
                        "CRITICAL": "background-color: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5;",
                        "HIGH": "background-color: #FEF3C7; color: #92400E; border: 1px solid #FCD34D;",
                        "MEDIUM": "background-color: #E0E7FF; color: #1E40AF; border: 1px solid #93C5FD;",
                        "INFO": "background-color: #F1F5F9; color: #475569; border: 1px solid #CBD5E1;"
                    }.get(m.severity.value, "")

                    claims_txt = " | ".join(m.evidence_claims) if m.evidence_claims else ""

                    st.markdown(f"""
                    <div class="gov-card" style="border-left: 4px solid #B91C1C; margin-bottom: 12px;">
                        <div class="responsive-flex">
                            <b style="font-size: 14.5px; color: #0B2545;">{m.check_name}</b>
                            <span style="{sev_badge} padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 700;">
                                {m.severity.value}
                            </span>
                        </div>
                        <p style="margin: 8px 0; color: #334155; font-size: 13.5px; line-height: 1.45;">{m.difference_details}</p>
                        <div style="font-size: 12px; color: #475569; line-height: 1.5; background: #F8FAFC; padding: 6px 10px; border-radius: 3px; border: 1px solid #E2E8F0;">
                            <b>Expected Reference:</b> <code>{m.expected_value}</code> • <b>Extracted In Document:</b> <code>{m.extracted_value}</code>  
                            <br><b>Rule Identifier:</b> <code>{m.rule_id}</code> • <b>Statutory Clause:</b> <i>{m.statutory_clause}</i>
                        </div>
                        {"<div style='margin-top: 6px; padding: 6px 10px; background-color: #F8FAFC; border-radius: 3px; font-size: 12px; border: 1px solid #E2E8F0;'><b>Evidentiary Provenance:</b> " + claims_txt + "</div>" if claims_txt else ""}
                        <div style="margin-top: 8px; font-size: 12.5px; color: #991B1B;">
                            <b>Recommended Scrutiny Action:</b> {m.recommended_action}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        with res_tab_passed:
            st.subheader(f"Passed Statutory Checks ({len(res.passed_checks)})")
            if not res.passed_checks:
                st.warning("No checks passed.")
            else:
                for p in res.passed_checks:
                    st.markdown(f"""
                    <div style="background-color: #FFFFFF; border: 1px solid #CBD5E1; border-left: 4px solid #166534; border-radius: 4px; padding: 10px 14px; margin-bottom: 8px;">
                        <div class="responsive-flex">
                            <b style="color: #166534; font-size: 13.5px;">{p.check_name}</b>
                            <span class="gov-badge gov-badge-verified">PASSED</span>
                        </div>
                        <p style="margin: 4px 0 0 0; color: #334155; font-size: 13px;">{p.difference_details}</p>
                        <div style="margin-top: 4px; font-size: 11.5px; color: #64748B;">
                            <b>Statutory Clause:</b> <i>{p.statutory_clause or 'AICTE Approval Process Handbook Regulations'}</i>
                            {" • <b>Page:</b> " + str(p.page_number) if p.page_number else ""}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        with res_tab_missing:
            st.subheader("Missing Regulatory Claims & Unverified Checks")
            if not res.missing_info and not res.unverified:
                st.success("All statutory requirements extracted and verified against institutional records.")

            if res.missing_info:
                st.markdown("**Required Regulatory Fields Missing from Document:**")
                for mi in res.missing_info:
                    st.warning(f"**{mi.check_name}**: {mi.difference_details} (Statutory Ref: *{mi.statutory_clause}*)")

            if res.unverified:
                st.markdown("**Checks Requiring Officer Manual Investigation:**")
                for uv in res.unverified:
                    st.info(f"**{uv.check_name}**: {uv.difference_details} (Statutory Ref: *{uv.statutory_clause}*)")

        with res_tab_fields:
            st.subheader(f"Extracted Regulatory Claims ({len(res.extracted_fields)})")
            if not res.extracted_fields:
                st.info("No structured fields were extracted.")
            else:
                fields_df = pd.DataFrame(res.extracted_fields)
                fields_df["field_value"] = fields_df["field_value"].astype(str)
                fields_df["confidence"] = fields_df["confidence"].apply(lambda x: f"{x:.1%}")
                st.dataframe(fields_df, use_container_width=True)

        with res_tab_auth:
            st.subheader("External Issuing Authority Query")
            if res.authority_verification:
                auth_data = res.authority_verification
                st.markdown(f"""
                <div class="gov-card" style="border-left: 4px solid #0B3C5D; margin-bottom: 12px;">
                    <div style="font-size: 11px; text-transform: uppercase; color: #64748B; font-weight: 700;">Issuing Authority Record</div>
                    <h4 style="margin: 2px 0 6px 0; color: #0B2545;">{auth_data.get('authority_name')}</h4>
                    <p style="margin: 0 0 10px 0; color: #64748B; font-size: 12px;">Query ID: <code>{auth_data.get('query_id')}</code> • Network Latency: <b>{auth_data.get('latency_ms')} ms</b></p>
                    <div class="responsive-flex" style="gap: 16px;">
                        <div><b>Authority Status:</b> <code>{auth_data.get('status')}</code></div>
                        <div><b>Record Match:</b> {'Yes (Verified)' if auth_data.get('matched') else 'Discrepancy Detected'}</div>
                        <div><b>Cryptographic / QR Token:</b> {'Validated' if auth_data.get('qr_verified') else 'Not Present'}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if auth_data.get("mismatch_details"):
                    st.error("**Authority Mismatch Log:**\n- " + "\n- ".join(auth_data["mismatch_details"]))
            else:
                st.info("No external authority query executed.")

            st.caption("Administrative Note: Issuing authority queries use Sakshya's realistic simulated registries as defined in the SIH26261 problem scope.")

