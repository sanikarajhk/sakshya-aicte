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

st.set_page_config(page_title="Circular-to-Rule | Sakshya", page_icon="📜", layout="wide")
inject_responsive_css()

st.title("📜 AICTE Circular-to-Rule Translation & Replay Sandbox")
st.caption("Converts unstructured policy circulars into executable YAML rules with historical impact simulation.")

st.warning("""
**Regulatory Transparency Notice:**  
All circulars presented on this page are **purely illustrative test cases** developed for the Sakshya prototype.  
They **DO NOT represent official AICTE policy** or statutory amendments.
""")

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
with st.expander("📄 View Illustrative Circular Official Text", expanded=True):
    st.text(chosen_circ["content"])

# Propose YAML Rule Change
st.subheader("1. AI / Semantic Extraction of Rule Change")
proposal = engine.parse_circular_to_rule_proposal(chosen_circ["content"])

col_p1, col_p2 = st.columns([1, 1])
with col_p1:
    st.markdown(f"**Target Statutory Rule:** `{proposal['target_rule_id']}`")
    st.markdown(f"**Semantic Parser Note:** {proposal['llm_reasoning']}")
with col_p2:
    st.markdown("**Proposed YAML Rule Definition:**")
    st.code(yaml.dump(proposal["proposed_yaml"], sort_keys=False), language="yaml")

st.markdown("---")

# Replay against historical applications
st.subheader("2. Historical Batch Replay Simulation (30 Applications)")
st.markdown("""
*Before any regulatory rule is activated, Sakshya replays the amended thresholds across historical applications 
to evaluate systemic impact and identify newly qualifying or disqualified colleges.*
""")

if st.button("🚀 Execute Historical Batch Replay (30 Applications)", use_container_width=True):
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
    st.markdown("---")
    st.subheader("3. Administrative Approval & Activation")
    if not can_approve_rules(current_user):
        st.warning("🔒 RULE ACTIVATION LOCKED: Only AICTE Administrators can approve and activate new regulatory rules.")
    else:
        st.success(f"Administrator verified: **{current_user.full_name}** (`{current_user.user_id}`).")
        if st.button("✅ Approve & Activate Amended Rule into Active Production Engine", use_container_width=True):
            engine.activate_proposed_rule(proposal["proposed_yaml"], current_user.user_id)
            st.success("Rule successfully activated and committed to circular_rules.yaml!")
            st.balloons()
