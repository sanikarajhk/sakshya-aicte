"""
Sakshya Test Suite: NetworkX Claim-Evidence Graph
Verifies graph node topology, claim linkages, and cross-document contradiction edges.
"""

from pathlib import Path
import pytest
from sakshya.pipeline.pipeline_runner import PipelineRunner
from sakshya.data_generator.ground_truth import load_ground_truth


def test_claim_evidence_graph_structure():
    """Verify NetworkX DiGraph construction and node types."""
    runner = PipelineRunner()
    gt = load_ground_truth()
    app_data = gt["APP-001"]

    # Process and build graph
    res = runner.process_application(app_data)
    assert res["graph_nodes"] > 15, "Graph has too few nodes"
    assert res["graph_edges"] > 15, "Graph has too few edges"


def test_contradiction_edges_in_graph():
    """Verify that planted cross-document contradictions generate CONTRADICTS edges."""
    runner = PipelineRunner()
    gt = load_ground_truth()
    app_data = gt["APP-015"]  # Planted land area contradiction

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
        app_id="APP-015",
        application_data=app_data,
        documents=app_data.get("documents", []),
        extracted_fields_by_doc=fields_by_doc,
        findings=findings,
        issuer_results={}
    )

    contradiction_edges = [
        (u, v) for u, v, data in G.edges(data=True)
        if data.get("relation") == "CONTRADICTS"
    ]
    assert len(contradiction_edges) >= 1, "Graph failed to generate CONTRADICTS edge for APP-015"
