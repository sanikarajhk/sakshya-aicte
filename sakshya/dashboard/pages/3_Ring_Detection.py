"""
Sakshya Dashboard - Cross-Institution Ring & Collusion Network
Visualizes interconnected institution networks, flags suspicious shared document
fingerprints, and explains high-risk collusion vs benign commonalities.
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
import streamlit.components.v1 as components
import pandas as pd

from sakshya.core.config import DATA_DIR
from sakshya.pipeline.ring_detector import RingDetector
from sakshya.data_generator.ground_truth import load_ground_truth

st.set_page_config(page_title="Ring Detection | Sakshya", page_icon="🔗", layout="wide")

st.title("🔗 Cross-Institution Collusion & Ring Detection")
st.caption("Graph analytics detecting multi-institution coordination via shared stamps, lease templates, and document fingerprints.")

gt = load_ground_truth()
applications = list(gt.values())

detector = RingDetector()
G = detector.build_network(applications)
clusters = detector.detect_clusters()

# Key metrics banner
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric("Total Institutions Evaluated", len(applications))
with col_m2:
    st.metric("Detected Collusion Clusters", len(clusters))
with col_m3:
    st.metric("Flagged Ring Institutions", sum(c["institution_count"] for c in clusters))
with col_m4:
    st.metric("Network Density", f"{detector.institution_graph.number_of_edges()} edges")

# Interactive Network Visualization
st.subheader("🌐 Institutional Shared Document Network")
network_html_file = DATA_DIR / "ring_network.html"
detector.to_pyvis_network(str(network_html_file))

# Legend
st.markdown("""
<div style="display: flex; gap: 15px; background-color: #0F172A; padding: 10px 16px; border-radius: 8px; color: white; font-size: 13px; margin-bottom: 15px;">
    <span><span style="color: #EF4444;">●</span> <b>Flagged Ring Institution</b></span>
    <span><span style="color: #3B82F6;">●</span> Independent Institution</span>
    <span><span style="color: #DC2626; font-weight: bold;">━</span> High-Risk Edge (Multi-Asset Overlap)</span>
    <span><span style="color: #F59E0B;">━</span> Moderate Shared Signal</span>
    <span><span style="color: #475569;">━</span> Benign Attribute (Bank / Region)</span>
</div>
""", unsafe_allow_html=True)

if network_html_file.exists():
    with open(network_html_file, "r", encoding="utf-8") as f:
        html_code = f.read()
    components.html(html_code, height=650, scrolling=False)

# Cluster Deep Dive Section
st.markdown("---")
st.subheader("🔍 Collusion Cluster Explanation & Signal Disaggregation")

if not clusters:
    st.info("No collusion clusters detected.")
else:
    for idx, cluster in enumerate(clusters):
        st.error(f"### ⚠️ Cluster Alert: {cluster['cluster_id']} ({cluster['institution_count']} Institutions Involved)")
        st.markdown(f"**Institutions:** `{', '.join(cluster['institutions'])}`")
        st.write(cluster["explanation"])

        # Disaggregation Table: High Risk vs Benign
        col_hr, col_be = st.columns(2)
        with col_hr:
            st.markdown("#### 🚨 High-Risk Collusion Signals (Actionable)")
            st.markdown("""
            *These documentary signals demonstrate physical asset duplication that should not occur across independent colleges:*
            """)
            for s in cluster["high_risk_signals"]:
                st.markdown(f"- 🔴 **{s}**")
        with col_be:
            st.markdown("#### ⚪ Benign Shared Attributes (Non-Incriminating)")
            st.markdown("""
            *These shared attributes are common commercial relationships and DO NOT alone imply wrongdoing:*
            """)
            for b in cluster["benign_shared_attributes"]:
                st.markdown(f"- 🟢 **{b}**")

        st.caption("""
        **Regulatory Safety Protocol:**  
        The presence of a shared bank branch or public notary in isolation does not warrant adverse inference. 
        However, the concurrent repetition of identical visual stamp image hashes, survey plot coordinates, 
        and architect empaneled credentials across 6 distant campuses constitutes a high-confidence signal for 
        physical inspection under AICTE regulations.
        """)
