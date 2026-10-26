"""
Sakshya Dashboard - Circular-to-Rule Sandbox
Translates policy circulars into YAML compliance rules, simulates historical impact
via batch replay across 30 applications, and requires administrator approval.
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
import yaml
from sakshya.core.security import get_current_user, can_approve_rules
from sakshya.circular_to_rule.engine import CircularToRuleEngine
from sakshya.dashboard.responsive import inject_responsive_css

st.set_page_config(page_title="Circular-to-Rule | Sakshya", page_icon="⚖️", layout="wide")
inject_responsive_css()

# Government Masthead Banner
st.markdown("""
<div class="gov-masthead">
    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #FEF3C7; font-weight: 700; margin-bottom: 4px;">
        All India Council for Technical Education • Policy & Regulations Division
    </div>
    <h1 class="gov-masthead-title">Policy Circular Translation & Impact Simulation Sandbox</h1>
    <p class="gov-masthead-subtitle">
        Converts unstructured policy circulars into executable YAML regulatory compliance rules with retrospective impact evaluation
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="gov-notice">
    <b>Regulatory Transparency Notice:</b><br>
    All policy circulars presented on this page are illustrative test cases developed for the Sakshya regulatory prototype. 
    They demonstrate automated parsing and retrospective impact assessment capabilities.
</div>
""", unsafe_allow_html=True)

# Role Check
role_name = st.sidebar.selectbox("Active Role", ["admin", "scrutiny_officer", "institution"], index=0)
current_user = get_current_user(role_name)

engine = CircularToRuleEngine()
samples = engine.get_sample_circulars()

selected_circ_title = st.selectbox(
    "Select Illustrative Circular to Process",
    [f"{c['circular_id']} — {c['title']}" for c in samples]
)

chosen_circ = next(c for c in samples if c["circular_id"] in selected_circ_title)

# Display Circular Text
with st.expander("View Illustrative Circular Official Text", expanded=True):
    st.text(chosen_circ["content"])

# Propose YAML Rule Change
st.subheader("1. Semantic Extraction of Regulatory Rule Change")
proposal = engine.parse_circular_to_rule_proposal(chosen_circ["content"])

col_p1, col_p2 = st.columns([1, 1])
with col_p1:
    st.markdown(f"**Target Statutory Rule:** `{proposal['target_rule_id']}`")
    st.markdown(f"**Semantic Parser Note:** {proposal['llm_reasoning']}")
with col_p2:
    st.markdown("**Proposed YAML Rule Definition:**")
    st.code(yaml.dump(proposal["proposed_yaml"], sort_keys=False), language="yaml")

st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

# Replay against historical applications
st.subheader("2. Historical Batch Replay Simulation (30 Applications)")
st.markdown("""
*Prior to administrative rule promulgation, Sakshya evaluates the amended thresholds across historical dossiers 
to measure systemic impact and identify newly conforming or non-conforming institutions.*
""")

if st.button("Execute Historical Batch Replay (30 Applications)", use_container_width=True):
    with st.spinner("Replaying amended rule against all historical dossiers..."):
        replay_res = engine.replay_against_historical_applications(proposal["proposed_yaml"])

    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    col_r1.metric("Historical Dossiers", replay_res["total_historical_applications"])
    col_r2.metric("Previous Violations", replay_res["previous_violations_count"])
    col_r3.metric("New Violations", replay_res["new_violations_count"])
    col_r4.metric("Net Shift", f"{replay_res['net_impact']:+d}")

    st.subheader(f"Impacted Institutional Applications ({replay_res['impacted_applications_count']})")
    if replay_res["impacted_applications"]:
        import pandas as pd
        st.dataframe(pd.DataFrame(replay_res["impacted_applications"]), use_container_width=True)
    else:
        st.info("No applications changed compliance status under this threshold variation.")

    # Administrator Approval Block
    st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
    st.subheader("3. Administrative Approval & Promulgation")
    if not can_approve_rules(current_user):
        st.warning("RULE ACTIVATION RESTRICTED: Only AICTE Administrators can approve and commit new regulatory rules.")
    else:
        st.markdown(f"""
        <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; border-left: 4px solid #0B3C5D; padding: 10px 14px; border-radius: 4px; margin-bottom: 12px; font-size: 13px;">
            <b>Authorized Administrator:</b> {current_user.full_name} (ID: <code>{current_user.user_id}</code>)
        </div>
        """, unsafe_allow_html=True)
        if st.button("Approve & Commit Amended Rule into Active Production Engine", type="primary", use_container_width=True):
            engine.activate_proposed_rule(proposal["proposed_yaml"], current_user.user_id)
            st.success("Rule successfully activated and committed to circular_rules.yaml!")
