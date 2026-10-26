"""
Sakshya Cross-Institution Ring & Collusion Detector
Detects institutional clusters linked through shared document fingerprints,
identical notary stamps, duplicate lease templates, and shared architects.
Distinguishes high-risk collusion signals from benign shared attributes.
"""

from typing import Dict, Any, List, Set, Tuple
import networkx as nx
from pathlib import Path
from PIL import Image
import imagehash

from sakshya.core.models import Finding, FindingSeverity


class RingDetector:
    """Network analysis engine for detecting inter-institution collusion rings."""

    def __init__(self):
        self.bipartite_graph = nx.Graph()
        self.institution_graph = nx.Graph()

    def build_network(self, applications: List[Dict[str, Any]]) -> nx.Graph:
        """
        Build full network connecting institutions via shared documentary attributes.
        Classifies attributes into HIGH_RISK vs BENIGN.
        """
        self.bipartite_graph.clear()
        self.institution_graph.clear()

        # Attribute buckets: attr_key -> list of (app_id, risk_level, attr_label)
        attributes_map: Dict[str, List[Tuple[str, str, str]]] = {}

        for app in applications:
            app_id = app.get("application_id", "")
            inst_name = app.get("institution_name", "")
            self.institution_graph.add_node(
                app_id,
                label=f"{app_id}\n{inst_name[:18]}...",
                full_name=inst_name,
                state=app.get("state", ""),
                category="INSTITUTION"
            )

            # 1. Notary Registration (High Risk if shared across different institutes)
            notary_reg = app.get("notary_registration")
            if notary_reg:
                key = f"NOTARY:{notary_reg}"
                attributes_map.setdefault(key, []).append((app_id, "HIGH_RISK", f"Notary: {notary_reg}"))

            # 2. Architect License (High Risk if identical across distant cities)
            arch = app.get("architect_license")
            if arch:
                key = f"ARCHITECT:{arch}"
                attributes_map.setdefault(key, []).append((app_id, "HIGH_RISK", f"Architect: {arch}"))

            # 3. Leased Survey Plot Number (High Risk if identical)
            survey = app.get("survey_number")
            if survey:
                key = f"SURVEY:{survey}"
                attributes_map.setdefault(key, []).append((app_id, "HIGH_RISK", f"Survey: {survey}"))

            # 4. Bank Branch (Benign / Harmless shared attribute)
            bank = app.get("bank_name")
            if bank:
                key = f"BANK:{bank}"
                attributes_map.setdefault(key, []).append((app_id, "BENIGN", f"Bank: {bank}"))

            # 5. Shared Notary Stamp Perceptual Image Hash (High Risk)
            for doc in app.get("documents", []):
                p_hash = doc.get("perceptual_hash")
                if p_hash and "notary" in doc.get("filename", "").lower():
                    key = f"STAMP_HASH:{p_hash}"
                    attributes_map.setdefault(key, []).append((app_id, "HIGH_RISK", f"Stamp Hash: {p_hash[:8]}"))

        # Build projected institution-to-institution graph
        for attr_key, occurrences in attributes_map.items():
            if len(occurrences) > 1:
                # Connected by shared attribute
                risk_level = occurrences[0][1]
                attr_label = occurrences[0][2]

                for i in range(len(occurrences)):
                    for j in range(i + 1, len(occurrences)):
                        u = occurrences[i][0]
                        v = occurrences[j][0]

                        if self.institution_graph.has_edge(u, v):
                            # Append to existing edge
                            edge_data = self.institution_graph[u][v]
                            edge_data["shared_attributes"].append(attr_label)
                            if risk_level == "HIGH_RISK":
                                edge_data["high_risk_signals"] += 1
                                edge_data["risk_level"] = "HIGH_RISK"
                        else:
                            self.institution_graph.add_edge(
                                u, v,
                                risk_level=risk_level,
                                high_risk_signals=1 if risk_level == "HIGH_RISK" else 0,
                                shared_attributes=[attr_label]
                            )

        return self.institution_graph

    def detect_clusters(self) -> List[Dict[str, Any]]:
        """
        Identify high-risk collusion clusters by extracting connected components
        filtered strictly on HIGH_RISK edges.
        """
        # Create subgraph containing only edges with high_risk_signals >= 2
        high_risk_subgraph = nx.Graph()
        for u, v, data in self.institution_graph.edges(data=True):
            if data.get("high_risk_signals", 0) >= 2:
                high_risk_subgraph.add_edge(u, v, **data)

        clusters = []
        for idx, comp in enumerate(nx.connected_components(high_risk_subgraph)):
            comp_nodes = sorted(list(comp))
            if len(comp_nodes) >= 3:
                # Gather all shared signals in this cluster
                cluster_signals = set()
                benign_signals = set()
                edges_summary = []

                for i in range(len(comp_nodes)):
                    for j in range(i + 1, len(comp_nodes)):
                        u, v = comp_nodes[i], comp_nodes[j]
                        if self.institution_graph.has_edge(u, v):
                            data = self.institution_graph[u][v]
                            for s in data["shared_attributes"]:
                                if "Bank:" in s:
                                    benign_signals.add(s)
                                else:
                                    cluster_signals.add(s)
                            edges_summary.append({
                                "source": u,
                                "target": v,
                                "signals": data["shared_attributes"]
                            })

                explanation = (
                    f"Identified collusion cluster of {len(comp_nodes)} institutions "
                    f"({', '.join(comp_nodes)}) linked by {len(cluster_signals)} overlapping high-risk documentary assets. "
                    f"Shared signals: {'; '.join(cluster_signals)}. "
                    f"Note: These institutions also share benign banking attributes ({'; '.join(benign_signals)}), "
                    "which alone do not indicate collusion. The multi-asset concurrence warrants field inspection."
                )

                clusters.append({
                    "cluster_id": f"COLLUSION_RING_{idx + 1:02d}",
                    "institution_count": len(comp_nodes),
                    "institutions": comp_nodes,
                    "high_risk_signals": list(cluster_signals),
                    "benign_shared_attributes": list(benign_signals),
                    "explanation": explanation,
                    "edges": edges_summary
                })

        return clusters

    def to_pyvis_network(self, output_html_path: str) -> str:
        """Render the cross-institution network with interactive color coding."""
        from pyvis.network import Network
        net = Network(height="650px", width="100%", bgcolor="#0F172A", font_color="#F8FAFC")
        net.barnes_hut(gravity=-2500, central_gravity=0.25, spring_length=120)

        # Highlight cluster nodes
        clusters = self.detect_clusters()
        ring_members = set()
        for c in clusters:
            ring_members.update(c["institutions"])

        for node, data in self.institution_graph.nodes(data=True):
            is_ring = node in ring_members
            color = "#EF4444" if is_ring else "#3B82F6"
            size = 24 if is_ring else 16
            title = f"<b>{node}</b><br/>{data.get('full_name')}<br/>State: {data.get('state')}"
            if is_ring:
                title += "<br/><b style='color:red;'>⚠️ FLAGGED IN COLLUSION CLUSTER</b>"

            net.add_node(
                node,
                label=node,
                title=title,
                color=color,
                size=size
            )

        for u, v, data in self.institution_graph.edges(data=True):
            risk = data.get("risk_level", "BENIGN")
            high_signals = data.get("high_risk_signals", 0)
            if high_signals >= 2:
                edge_color = "#DC2626"
                width = 3
            elif risk == "HIGH_RISK":
                edge_color = "#F59E0B"
                width = 2
            else:
                edge_color = "#475569"
                width = 1

            title = "<br/>".join(data.get("shared_attributes", []))
            net.add_edge(u, v, title=title, color=edge_color, width=width)

        net.save_graph(output_html_path)
        return output_html_path
