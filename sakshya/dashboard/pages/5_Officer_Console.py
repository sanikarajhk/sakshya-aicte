"""
Sakshya Dashboard - Scrutiny Officer Adjudication Console
Enables authorized AICTE Scrutiny Officers to review evidence, confirm or override
automated system findings, record regulatory justifications, and commit to the audit trail.
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
from sakshya.core.models import UserRole, ApplicationStatus
from sakshya.core.database import get_db_context
from sakshya.core.models import ApplicationDB, FindingDB, OfficerActionDB
from sakshya.core.security import get_current_user, can_override_decision
from sakshya.core.audit import log_event
from sakshya.data_generator.ground_truth import load_ground_truth
from sakshya.dashboard.responsive import inject_responsive_css

st.set_page_config(page_title="Officer Console | Sakshya", page_icon="⚖️", layout="wide")
inject_responsive_css()

st.title("⚖️ AICTE Scrutiny Officer Adjudication Console")
st.caption("Official regulatory decision portal for reviewing dossiers, confirming findings, or recording justified overrides.")

# Role Check
role_name = st.sidebar.selectbox(
    "Active Role (Override Simulation)",
    ["scrutiny_officer", "admin", "institution"],
    index=0
)
current_user = get_current_user(role_name)

if not can_override_decision(current_user):
    st.error("⛔ ACCESS DENIED: Only authorized AICTE Scrutiny Officers and Administrators may access the Adjudication Console.")
    st.info("Please switch your role to 'Scrutiny Officer' or 'Admin' in the sidebar.")
    st.stop()

st.success(f"**Authenticated Officer:** {current_user.full_name} (`{current_user.user_id}`) • Bureau: Approval Bureau (Headquarters)")

# Select Application
gt = load_ground_truth()
review_needed_apps = []
with get_db_context() as db:
    apps = db.query(ApplicationDB).all()
    for a in apps:
        review_needed_apps.append(a.id)

selected_app_id = st.selectbox("Select Application for Official Action", review_needed_apps)

with get_db_context() as db:
    app_raw = db.query(ApplicationDB).filter_by(id=selected_app_id).first()
    app_info = {
        "id": app_raw.id,
        "institution_name": app_raw.institution_name,
        "status": app_raw.status.value,
        "overall_confidence": app_raw.overall_confidence,
        "readiness_score": app_raw.readiness_score,
        "flagged_ring": app_raw.flagged_ring
    }
    findings_list = [
        {
            "severity": f.severity.value,
            "title": f.title,
            "description": f.description
        }
        for f in db.query(FindingDB).filter_by(application_id=selected_app_id).all()
    ]
    past_actions_list = [
        {
            "decision": act.decision,
            "officer_name": act.officer_name,
            "officer_id": act.officer_id,
            "action_timestamp": act.action_timestamp.isoformat(),
            "reason_code": act.reason_code,
            "remarks": act.remarks
        }
        for act in db.query(OfficerActionDB).filter_by(application_id=selected_app_id).all()
    ]

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Dossier Summary & System Recommendation")
    st.markdown(f"""
    - **Institution:** {app_info['institution_name']}
    - **Current Automated Status:** `{app_info['status']}`
    - **Calibrated AI Confidence:** `{app_info['overall_confidence']:.1%}`
    - **Readiness Score:** `{app_info['readiness_score']:.1f}%`
    - **Collusion Ring Flag:** `{'YES ⚠️' if app_info['flagged_ring'] else 'NO'}`
    """)

    st.markdown("#### System Findings:")
    if not findings_list:
        st.write("No findings flagged by automated rules.")
    else:
        for f in findings_list:
            st.markdown(f"- **[{f['severity']}]** {f['title']}: *{f['description']}*")

with col_right:
    st.subheader("Official Regulatory Determination")
    with st.form("officer_decision_form"):
        decision = st.selectbox(
            "Regulatory Determination",
            options=["APPROVE", "REJECT", "REQUEST_CLARIFICATION"],
            help="Select official determination for this application dossier."
        )

        reason_code = st.selectbox(
            "Statutory Reason Code",
            options=[
                "AI_VALIDATION_CONFIRMED",
                "PHYSICAL_INSPECTION_SATISFACTORY",
                "OFFICIAL_EXEMPTION_GRANTED",
                "UNRESOLVED_CONTRADICTION",
                "LAPSED_STATUTORY_SAFETY_CLEARANCE",
                "MISREPRESENTATION_OF_LAND_TITLE",
                "CROSS_INSTITUTION_COLLUSION_FLAGGED"
            ]
        )

        remarks = st.text_area(
            "Official Scrutiny Remarks (Recorded into Permanent Hash-Chained Audit Trail)",
            placeholder="Provide explicit factual justification for approval, rejection, or override...",
            height=120
        )

        override_confirm = st.checkbox(
            "I hereby certify that this regulatory action is exercised pursuant to AICTE Approval Process norms.",
            value=False
        )

        submitted = st.form_submit_button("⚖️ Commit Regulatory Decision to Audit Chain", use_container_width=True)

        if submitted:
            if not override_confirm:
                st.error("Please confirm certification checkbox before committing regulatory action.")
            elif not remarks.strip():
                st.error("Official scrutiny remarks are strictly mandatory for compliance auditability.")
            else:
                with get_db_context() as db:
                    # Update application status
                    app_to_update = db.query(ApplicationDB).filter_by(id=selected_app_id).first()
                    new_status = (
                        ApplicationStatus.OFFICER_APPROVED if decision == "APPROVE"
                        else ApplicationStatus.OFFICER_REJECTED
                    )
                    app_to_update.status = new_status

                    # Record officer action
                    action_record = OfficerActionDB(
                        application_id=selected_app_id,
                        officer_id=current_user.user_id,
                        officer_name=current_user.full_name,
                        decision=decision,
                        reason_code=reason_code,
                        remarks=remarks,
                        override_flags=json.dumps([f"OVERRODE_FROM_{app_info['status']}"])
                    )
                    db.add(action_record)

                    # Append to tamper-evident audit log
                    log_event(
                        db=db,
                        actor_id=current_user.user_id,
                        actor_role=current_user.role.value,
                        action=f"OFFICER_DETERMINATION_{decision}",
                        entity_type="application",
                        entity_id=selected_app_id,
                        details={
                            "previous_status": app_info["status"],
                            "new_status": new_status.value,
                            "reason_code": reason_code,
                            "remarks": remarks,
                            "officer_name": current_user.full_name
                        }
                    )

                st.success(f"Regulatory decision committed! Application '{selected_app_id}' is now '{new_status.value}'.")
                st.rerun()

# Past Adjudication History
if past_actions_list:
    st.markdown("---")
    st.subheader("📜 Historical Officer Adjudications for this Dossier")
    for act in past_actions_list:
        st.info(f"**{act['decision']}** by **{act['officer_name']}** (`{act['officer_id']}`) on `{act['action_timestamp']}`  \nReason: `{act['reason_code']}`  \n*\"{act['remarks']}\"*")
