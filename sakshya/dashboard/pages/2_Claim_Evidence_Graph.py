"""
Sakshya Dashboard - Claim-Evidence Knowledge Graph
Interactive NetworkX and Pyvis visualization linking claims, documents, rules,
issuing authority verifications, and cross-document contradictions.
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
from sakshya.core.config import DATA_DIR
from sakshya.core.database import get_db_context
from sakshya.core.models import ApplicationDB, DocumentDB, FindingDB
from sakshya.pipeline.pipeline_runner import PipelineRunner
from sakshya.data_generator.ground_truth import load_ground_truth

st.set_page_config(page_title="Claim-Evidence Graph | Sakshya", page_icon="🕸️", layout="wide")

st.title("🕸️ Claim-Evidence Provenance & Contradiction Graph")
st.caption("Visualizes evidentiary linkages between extracted claims, source documents, regulatory rules, and authority checks.")

gt = load_ground_truth()

# Highlight applications with contradictions
contradiction_apps = ["APP-015", "APP-016", "APP-017", "APP-018", "APP-019"]

col_sel, col_info = st.columns([2, 3])
with col_sel:
    selected_app_id = st.selectbox(
        "Select Application for Graph Inspection",
        options=list(gt.keys()),
        index=list(gt.keys()).index("APP-015"),
        help="Applications APP-015 through APP-019 contain planted cross-document contradictions."
    )

with col_info:
    if selected_app_id in contradiction_apps:
        st.warning(f"⚠️ **Contradiction Case Detected ({selected_app_id}):** Cross-document claim discrepancy will appear as a highlighted red conflict edge in the graph below.")
    else:
        st.info("ℹ️ Standard evidentiary graph showing multi-document claim provenance and authority checks.")

# Build or retrieve graph
runner = PipelineRunner()
app_data = gt[selected_app_id]

# Generate interactive Pyvis HTML
graph_html_file = DATA_DIR / f"graph_{selected_app_id}.html"

# Run graph builder
from sakshya.core.models import DocumentType

fields_by_doc = {}
for d in app_data.get("documents", []):
    dt = DocumentType(d["document_type"])
    text = runner.reader.read_document(Path(d["file_path"]))["full_text"]
    fields_by_doc[d["filename"]] = runner.extractor.extract_document_fields(dt, text, d["filename"])

findings = runner.rules_engine.evaluate_application(
    application_data=app_data,
    documents=app_data.get("documents", []),
    extracted_fields_by_doc=fields_by_doc
)

G = runner.graph_builder.build_graph(
    app_id=selected_app_id,
    application_data=app_data,
    documents=app_data.get("documents", []),
    extracted_fields_by_doc=fields_by_doc,
    findings=findings,
    issuer_results={}
)

runner.graph_builder.to_pyvis_network(G, str(graph_html_file))

# Legend
st.markdown("""
<div style="display: flex; gap: 15px; background-color: #1E293B; padding: 10px 16px; border-radius: 8px; color: white; font-size: 13px; margin-bottom: 15px;">
    <span><span style="color: #2B6CB0;">●</span> Application Node</span>
    <span><span style="color: #4A5568;">●</span> Document Node</span>
    <span><span style="color: #3182CE;">●</span> Claim Node</span>
    <span><span style="color: #805AD5;">●</span> Regulatory Rule</span>
    <span><span style="color: #38A169;">●</span> Verified Authority</span>
    <span><span style="color: #E53E3E;">●</span> <b>Contradiction / Conflict</b></span>
</div>
""", unsafe_allow_html=True)

# Render Pyvis HTML inside Streamlit iframe
if graph_html_file.exists():
    with open(graph_html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    components.html(html_content, height=650, scrolling=False)
else:
    st.error("Graph visualization could not be generated.")

# Graph structural statistics
st.subheader("Graph Topology & Evidentiary Metrics")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Nodes", G.number_of_nodes())
c2.metric("Total Edges", G.number_of_edges())
c3.metric("Document Sources", sum(1 for _, d in G.nodes(data=True) if d.get("category") == "DOCUMENT"))
c4.metric("Contradiction Edges", sum(1 for _, _, d in G.edges(data=True) if d.get("relation") == "CONTRADICTS"))
