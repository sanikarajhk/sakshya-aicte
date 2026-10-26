"""
Sakshya Claim-Evidence Knowledge Graph
Constructs a NetworkX directed graph linking extracted claims, source documents,
regulatory rules, and issuing authority verification results.
Explicitly highlights cross-document contradictions and evidentiary provenance.
"""

from typing import Dict, Any, List
import networkx as nx
from sakshya.core.models import Finding, ExtractedField, MockIssuerResponse


class ClaimEvidenceGraphBuilder:
    """Builds and analyzes NetworkX claim-evidence provenance graphs."""

    def build_graph(
        self,
        app_id: str,
        application_data: Dict[str, Any],
        documents: List[Dict[str, Any]],
        extracted_fields_by_doc: Dict[str, List[ExtractedField]],
        findings: List[Finding],
        issuer_results: Dict[str, MockIssuerResponse]
    ) -> nx.DiGraph:
        """
        Construct DiGraph with typed nodes:
        - APPLICATION (Central entity)
        - DOCUMENT (Source files)
        - CLAIM (Extracted assertions: land area, survey, dates, names)
        - RULE (Regulatory rules evaluated)
        - FINDING (Discrepancies / Contradictions)
        - ISSUER (External authority validation)
        """
        G = nx.DiGraph()

        # 1. Central Application Node
        app_node = f"APP:{app_id}"
        G.add_node(
            app_node,
            label=f"Application {app_id}",
            category="APPLICATION",
            institution_name=application_data.get("institution_name", ""),
            color="#2B6CB0",
            size=28
        )

        # 2. Document Nodes
        for doc in documents:
            doc_id = f"DOC:{doc['filename']}"
            G.add_node(
                doc_id,
                label=doc["filename"],
                category="DOCUMENT",
                doc_type=doc.get("document_type"),
                color="#4A5568",
                size=20
            )
            G.add_edge(app_node, doc_id, relation="SUBMITTED_WITH")

            # Link Issuing Authority result to document
            doc_type = doc.get("document_type", "")
            for qry_id, resp in issuer_results.items():
                if doc_type[:4].upper() in qry_id.upper():
                    issuer_node = f"ISSUER:{resp.authority_name[:20]}"
                    G.add_node(
                        issuer_node,
                        label=f"Authority: {resp.status.value}",
                        category="ISSUER",
                        status=resp.status.value,
                        color="#38A169" if resp.matched else "#E53E3E",
                        size=18
                    )
                    G.add_edge(doc_id, issuer_node, relation="VERIFIED_BY", status=resp.status.value)

        # 3. Extracted Claim Nodes
        claim_nodes_by_type: Dict[str, List[str]] = {}

        for doc_name, fields in extracted_fields_by_doc.items():
            doc_node = f"DOC:{doc_name}"
            for f in fields:
                claim_id = f"CLAIM:{doc_name}:{f.field_name}"
                val_str = str(f.field_value)
                G.add_node(
                    claim_id,
                    label=f"{f.field_name}: {val_str}",
                    category="CLAIM",
                    field_name=f.field_name,
                    field_value=val_str,
                    confidence=f.confidence,
                    color="#3182CE",
                    size=16
                )
                G.add_edge(doc_node, claim_id, relation="ASSERTS")
                claim_nodes_by_type.setdefault(f.field_name, []).append(claim_id)

        # 4. Findings & Rule Nodes
        for idx, finding in enumerate(findings):
            finding_node = f"FINDING:{finding.code}:{idx}"
            color = "#E53E3E" if finding.severity.value in ["CRITICAL", "HIGH"] else "#DD6B20"
            G.add_node(
                finding_node,
                label=f"{finding.severity.value}: {finding.title[:30]}...",
                category="FINDING",
                severity=finding.severity.value,
                description=finding.description,
                is_contradiction=finding.is_contradiction,
                color=color,
                size=22
            )

            # Link to rule if specified
            if finding.rule_id:
                rule_node = f"RULE:{finding.rule_id}"
                if not G.has_node(rule_node):
                    G.add_node(
                        rule_node,
                        label=finding.rule_id,
                        category="RULE",
                        color="#805AD5",
                        size=18
                    )
                G.add_edge(rule_node, finding_node, relation="GENERATED")

            # Link finding to source document or claims
            if finding.source_document:
                doc_node = f"DOC:{finding.source_document}"
                if G.has_node(doc_node):
                    G.add_edge(finding_node, doc_node, relation="FLAGS_DOCUMENT")

            # Highlight Contradiction Edges between opposing claims
            if finding.is_contradiction:
                for claim_type in ["land_area_acres", "survey_number", "institution_name", "noc_number"]:
                    c_nodes = claim_nodes_by_type.get(claim_type, [])
                    if len(c_nodes) >= 2:
                        for i in range(len(c_nodes)):
                            for j in range(i + 1, len(c_nodes)):
                                # Add bidirectional CONFLICTS_WITH edge
                                G.add_edge(c_nodes[i], c_nodes[j], relation="CONTRADICTS", color="#E53E3E", width=3)
                                G.add_edge(finding_node, c_nodes[i], relation="FLAGS_CLAIM")
                                G.add_edge(finding_node, c_nodes[j], relation="FLAGS_CLAIM")

        return G

    def to_pyvis_network(self, G: nx.DiGraph, output_html_path: str) -> str:
        """Export NetworkX graph to an interactive HTML visualization using Pyvis."""
        from pyvis.network import Network
        net = Network(height="650px", width="100%", directed=True, bgcolor="#1A202C", font_color="#E2E8F0")
        
        # Configure physics for clear layout
        net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=95)

        for node, attrs in G.nodes(data=True):
            cat = attrs.get("category", "")
            color = attrs.get("color", "#718096")
            title = f"<b>{attrs.get('label')}</b><br/>Category: {cat}"
            if "description" in attrs:
                title += f"<br/>{attrs['description']}"
            net.add_node(
                node,
                label=attrs.get("label", node),
                title=title,
                color=color,
                size=attrs.get("size", 16)
            )

        for u, v, attrs in G.edges(data=True):
            rel = attrs.get("relation", "")
            color = attrs.get("color", "#A0AEC0")
            width = attrs.get("width", 1)
            net.add_edge(u, v, title=rel, label=rel, color=color, width=width)

        net.save_graph(output_html_path)
        return output_html_path
