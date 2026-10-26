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
from sakshya.dashboard.responsive import inject_responsive_css

st.set_page_config(page_title="Ring Detection | Sakshya", page_icon="⚖️", layout="wide")
inject_responsive_css()

# Government Masthead Banner
st.markdown("""
<div class="gov-masthead">
    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #FEF3C7; font-weight: 700; margin-bottom: 4px;">
        All India Council for Technical Education • Regulatory Intelligence Unit
    </div>
    <h1 class="gov-masthead-title">Cross-Institution Collusion & Ring Detection</h1>
    <p class="gov-masthead-subtitle">
        Graph analytics identifying coordinated multi-institution applicant rings via shared document fingerprints, identical visual stamps, and duplicated land assets
    </p>
</div>
""", unsafe_allow_html=True)

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
    st.metric("Network Edge Density", f"{detector.institution_graph.number_of_edges()} edges")

# Interactive Network Visualization
st.subheader("Institutional Shared Document Network")
network_html_file = DATA_DIR / "ring_network.html"
detector.to_pyvis_network(str(network_html_file))

# Legend
st.markdown("""
<div class="responsive-legend">
    <span><span style="color: #991B1B; font-weight: bold; margin-right: 5px;">●</span> Flagged Ring Institution</span>
    <span><span style="color: #0B3C5D; font-weight: bold; margin-right: 5px;">●</span> Independent Institution</span>
    <span><span style="color: #B91C1C; font-weight: bold; margin-right: 5px;">━</span> High-Risk Edge</span>
    <span><span style="color: #D97706; font-weight: bold; margin-right: 5px;">━</span> Moderate Shared Signal</span>
    <span><span style="color: #64748B; font-weight: bold; margin-right: 5px;">━</span> Benign Attribute</span>
</div>
""", unsafe_allow_html=True)

st.caption("Touch tip: On mobile devices, swipe using two fingers or touch outside the graph box to scroll the page.")

if network_html_file.exists():
    with open(network_html_file, "r", encoding="utf-8") as f:
        html_code = f.read()
    components.html(html_code, height=600, scrolling=True)

# Cluster Deep Dive Section
st.markdown("<hr style='margin: 18px 0; border: none; border-top: 1px solid #CBD5E1;'>", unsafe_allow_html=True)
st.subheader("Collusion Cluster Adjudication & Signal Disaggregation")

if not clusters:
    st.info("No collusion clusters detected.")
else:
    for idx, cluster in enumerate(clusters):
        st.markdown(f"""
        <div class="gov-card" style="border-left: 5px solid #B91C1C; margin-bottom: 16px;">
            <div class="responsive-flex">
                <div>
                    <span class="gov-badge gov-badge-flagged">Statutory Alert</span>
                    <h3 style="margin: 6px 0 2px 0; color: #0B2545;">Cluster Identifier: {cluster['cluster_id']} ({cluster['institution_count']} Institutions Coordinated)</h3>
                    <div style="font-size: 12.5px; color: #475569;">
                        <b>Coordinated Institutions:</b> <code>{', '.join(cluster['institutions'])}</code>
                    </div>
                </div>
            </div>
            <p style="margin: 8px 0; font-size: 13.5px; color: #334155; line-height: 1.45;">
                {cluster["explanation"]}
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Disaggregation Table: High Risk vs Benign
        col_hr, col_be = st.columns(2)
        with col_hr:
            st.markdown("""
            <div style="background-color: #FEF2F2; border: 1px solid #FECACA; border-radius: 4px; padding: 12px 14px; margin-bottom: 10px;">
                <b style="color: #991B1B; font-size: 13.5px;">High-Risk Collusion Signals (Actionable Deficiencies)</b>
                <div style="font-size: 12px; color: #7F1D1D; margin: 4px 0 8px 0;">Demonstrates physical asset duplication that cannot legitimately recur across independent institutions:</div>
            """, unsafe_allow_html=True)
            for s in cluster["high_risk_signals"]:
                st.markdown(f"- <b>{s}</b>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_be:
            st.markdown("""
            <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 4px; padding: 12px 14px; margin-bottom: 10px;">
                <b style="color: #334155; font-size: 13.5px;">Benign Shared Attributes (Non-Incriminating)</b>
                <div style="font-size: 12px; color: #64748B; margin: 4px 0 8px 0;">Standard commercial overlap that does not alone constitute regulatory non-compliance:</div>
            """, unsafe_allow_html=True)
            for b in cluster["benign_shared_attributes"]:
                st.markdown(f"- {b}")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
        <div class="gov-notice">
            <b>Regulatory Safety Protocol:</b><br>
            The presence of a shared bank branch or public notary in isolation does not warrant adverse regulatory inference. 
            However, concurrent repetition of identical perceptual stamp image hashes, survey plot coordinates, 
            and architect credentials across campuses constitutes a high-confidence basis for physical surprise inspection under AICTE regulations.
        </div>
        """, unsafe_allow_html=True)
