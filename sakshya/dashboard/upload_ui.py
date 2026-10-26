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
        st.subheader("📤 Upload & Validate Institutional Document")
        st.markdown(
            "Upload an institutional document (PDF) to check it against the college's existing records, "
            "identify compliance issues, and verify regulatory norms in real time."
        )

    # 1. File Uploader Widget
    uploaded_file = st.file_uploader(
        "Choose an Institutional PDF Document to Authenticate",
        type=["pdf"],
        key=f"{key_prefix}pdf_uploader",
        help="Upload a digital or scanned regulatory PDF. Processing occurs securely in memory without modifying the synthetic dataset."
    )

    # 2. Quick sample document selector for instant testing
    with st.expander("💡 Or test instantly using a sample document from the synthetic repository"):
        sample_options = [
            "-- Select a pre-generated sample --",
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
    elif sample_choice != "-- Select a pre-generated sample --":
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
        st.info("👆 Please upload a PDF file from your computer or choose a sample document above to begin verification.")
        return

    st.markdown("---")
    # Step 1: Validate PDF Format and Read in Memory
    with st.spinner("Validating PDF integrity and parsing document content..."):
        is_valid, err_msg, metadata = validator.validate_pdf_bytes(file_bytes, filename)

    if not is_valid:
        st.error(f"❌ **Invalid Document:** {err_msg}")
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
        st.success(f"""
        🎯 **Target Institution Identified:** **{ident.identified_name}** (`{target_app_id}`)  
        • **Confidence:** `100% (Exact Match)`  
        • **Method:** {ident.method}  
        • **Detail:** {ident.explanation}
        """)
    elif ident.status == IdentificationStatus.HIGH_CONFIDENCE_FUZZY:
        target_app_id = ident.identified_app_id
        st.info(f"""
        🔍 **Target Institution Identified:** **{ident.identified_name}** (`{target_app_id}`)  
        • **Confidence:** `{ident.confidence:.1%}`  
        • **Method:** {ident.method}  
        • **Detail:** {ident.explanation}
        """)
    elif ident.status == IdentificationStatus.AMBIGUOUS_MATCH:
        is_identification_uncertain = True
        st.warning(f"""
        ⚠️ **Ambiguous Institutional Match Detected** (Confidence: {ident.confidence:.1%})  
        {ident.explanation}
        """)
        st.markdown("**Top Candidate Matches:**")
        cand_df = pd.DataFrame([c.dict() for c in ident.top_candidates])
        st.table(cand_df)

        target_app_id = st.selectbox(
            "👉 Select the intended college to validate this document against:",
            options=app_ids,
            index=app_ids.index(ident.top_candidates[0].application_id) if ident.top_candidates else 0,
            format_func=lambda x: f"{x} — {gt[x]['institution_name']} ({gt[x]['district']}, {gt[x]['state']})",
            key=f"{key_prefix}ambig_college_choice"
        )
    elif ident.status == IdentificationStatus.UNKNOWN_COLLEGE:
        is_identification_uncertain = True
        st.error(f"""
        🚫 **Unregistered Institution Detected**  
        {ident.explanation}
        """)
        st.caption("Sakshya adheres strictly to regulatory boundaries: unlisted colleges cannot be silently attributed to an arbitrary institution.")

        exp_compare = st.checkbox(
            "⚙️ Select an existing college to run targeted comparison for audit/experimental scrutiny",
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
        status_color = {
            "VERIFIED_AUTO": "#10B981",
            "NEEDS_OFFICER_REVIEW": "#F59E0B",
            "FLAGGED_ANOMALY": "#EF4444"
        }.get(res.overall_status, "#6B7280")

        st.markdown(f"""
        <div style="background-color: #F8FAFC; border-left: 6px solid {status_color}; padding: clamp(12px, 3vw, 18px); border-radius: 10px; margin: 15px 0 20px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div class="responsive-flex">
                <div style="flex: 1 1 280px;">
                    <h3 style="margin: 0; color: #1E293B; font-size: clamp(16px, 3.5vw, 20px);">{res.college_name} ({res.college_id})</h3>
                    <p style="margin: 6px 0 0 0; color: #64748B; font-size: clamp(12px, 2.5vw, 13.5px);">
                        Scrutiny Outcome: <b>{res.summary}</b>
                    </p>
                </div>
                <div style="flex: 0 0 auto; text-align: right;">
                    <span style="background-color: {status_color}; color: white; padding: 6px 14px; border-radius: 16px; font-weight: bold; font-size: clamp(12px, 2.5vw, 13.5px); display: inline-block;">
                        {res.overall_status}
                    </span>
                    <div style="margin-top: 6px; font-size: clamp(11.5px, 2.2vw, 13px); color: #475569;">
                        Calibrated Confidence: <b>{res.calibrated_confidence:.1%}</b>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Check breakdown metrics
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        with m_c1:
            st.metric("✅ Passed Checks", len(res.passed_checks))
        with m_c2:
            st.metric("⚠️ Mismatches", len(res.mismatches), delta=f"-{len(res.mismatches)}" if res.mismatches else None, delta_color="inverse")
        with m_c3:
            st.metric("❓ Missing Info", len(res.missing_info))
        with m_c4:
            st.metric("🔍 Unverified Checks", len(res.unverified))

        # Result Tabs: Mismatches, Passed, Missing, Extracted Fields, Authority Records
        res_tab_mismatch, res_tab_passed, res_tab_missing, res_tab_fields, res_tab_auth = st.tabs([
            f"⚠️ Mismatches & Findings ({len(res.mismatches)})",
            f"✅ Passed Statutory Checks ({len(res.passed_checks)})",
            f"❓ Missing / Unverified ({len(res.missing_info) + len(res.unverified)})",
            f"📑 Extracted Claims ({len(res.extracted_fields)})",
            "🏛️ Issuing Authority Verification"
        ])

        with res_tab_mismatch:
            st.subheader(f"Statutory Violations & Discrepancies ({len(res.mismatches)})")
            if not res.mismatches:
                st.success("✅ Zero mismatches detected. All extracted claims align with institutional reference records.")
            else:
                for m in res.mismatches:
                    sev_badge = {
                        "CRITICAL": "background-color: #FEE2E2; color: #991B1B; border: 1px solid #F87171;",
                        "HIGH": "background-color: #FEF3C7; color: #92400E; border: 1px solid #FCD34D;",
                        "MEDIUM": "background-color: #E0E7FF; color: #3730A3; border: 1px solid #A5B4FC;",
                        "INFO": "background-color: #F1F5F9; color: #475569; border: 1px solid #CBD5E1;"
                    }.get(m.severity.value, "")

                    claims_txt = " | ".join(m.evidence_claims) if m.evidence_claims else ""

                    st.markdown(f"""
                    <div style="background-color: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                        <div class="responsive-flex">
                            <b style="font-size: 15px; color: #0F172A;">{m.check_name}</b>
                            <span style="{sev_badge} padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                                {m.severity.value}
                            </span>
                        </div>
                        <p style="margin: 8px 0; color: #334155; font-size: 13.5px; line-height: 1.45;">{m.difference_details}</p>
                        <div style="font-size: 12px; color: #64748B; line-height: 1.5;">
                            <b>Expected Value:</b> <code>{m.expected_value}</code> • <b>Extracted Value:</b> <code>{m.extracted_value}</code>  
                            <br><b>Rule Ref:</b> <code>{m.rule_id}</code> • <b>Statutory Clause:</b> <i>{m.statutory_clause}</i>
                        </div>
                        {"<div style='margin-top: 6px; padding: 6px 10px; background-color: #F8FAFC; border-radius: 4px; font-size: 12px;'><b>Evidentiary Claims:</b> " + claims_txt + "</div>" if claims_txt else ""}
                        <div style="margin-top: 8px; font-size: 12.5px; color: #B91C1C;">
                            <b>Recommended Officer Action:</b> {m.recommended_action}
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
                    <div style="background-color: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;">
                        <div class="responsive-flex">
                            <b style="color: #166534; font-size: 14px;">✅ {p.check_name}</b>
                            <span style="color: #15803D; font-size: 11.5px; font-weight: bold;">PASSED</span>
                        </div>
                        <p style="margin: 5px 0 0 0; color: #1E293B; font-size: 13px;">{p.difference_details}</p>
                        <div style="margin-top: 4px; font-size: 11.5px; color: #475569;">
                            <b>Statutory Citation:</b> <i>{p.statutory_clause or 'AICTE Verification Framework'}</i>
                            {" • <b>Page:</b> " + str(p.page_number) if p.page_number else ""}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        with res_tab_missing:
            st.subheader("Missing Claims & Unverified Records")
            if not res.missing_info and not res.unverified:
                st.success("✅ All regulatory fields were extracted and verified against institutional records.")

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
                <div style="background-color: white; border: 1px solid #CBD5E1; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                    <h4 style="margin: 0; color: #1E293B;">{auth_data.get('authority_name')}</h4>
                    <p style="margin: 4px 0 12px 0; color: #64748B; font-size: 12px;">Query ID: <code>{auth_data.get('query_id')}</code> • Network Latency: <b>{auth_data.get('latency_ms')} ms</b></p>
                    <div style="display: flex; gap: 15px; margin-bottom: 10px;">
                        <div><b>Authority Verification Status:</b> <code>{auth_data.get('status')}</code></div>
                        <div><b>Matched:</b> {'✅ Yes' if auth_data.get('matched') else '❌ No'}</div>
                        <div><b>QR Code Verified:</b> {'✅ Validated' if auth_data.get('qr_verified') else '⚪ Not Present'}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if auth_data.get("mismatch_details"):
                    st.error("**Authority Mismatch Log:**\n- " + "\n- ".join(auth_data["mismatch_details"]))
            else:
                st.info("No external authority query executed.")

            st.caption("⚠️ Note: Issuing authority queries use Sakshya's realistic simulated registries as defined in the SIH26261 problem scope.")
