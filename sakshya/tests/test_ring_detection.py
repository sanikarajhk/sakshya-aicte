"""
Sakshya Test Suite: Cross-Institution Ring Detection
Verifies the detection of the documented 6-institution cluster (APP-025 to APP-030)
and the correct disaggregation of high-risk collusion signals from harmless shared features.
"""

import pytest
from sakshya.pipeline.ring_detector import RingDetector
from sakshya.data_generator.ground_truth import load_ground_truth


def test_six_institution_cluster_detection():
    """Verify that exactly one 6-institution cluster is identified."""
    gt = load_ground_truth()
    applications = list(gt.values())

    detector = RingDetector()
    detector.build_network(applications)
    clusters = detector.detect_clusters()

    assert len(clusters) == 1, f"Expected exactly 1 high-risk cluster, found {len(clusters)}"
    cluster = clusters[0]
    assert cluster["institution_count"] == 6, f"Expected 6 institutions, found {cluster['institution_count']}"

    expected_members = {"APP-025", "APP-026", "APP-027", "APP-028", "APP-029", "APP-030"}
    actual_members = set(cluster["institutions"])
    assert actual_members == expected_members, f"Mismatched cluster members: {actual_members}"


def test_ring_disaggregation_high_risk_vs_benign():
    """Verify that high-risk signals and harmless shared attributes are properly segregated."""
    gt = load_ground_truth()
    detector = RingDetector()
    detector.build_network(list(gt.values()))
    clusters = detector.detect_clusters()
    cluster = clusters[0]

    # Check high-risk signals
    high_risk_str = " ".join(cluster["high_risk_signals"])
    assert "NOT/2021/DEL/8821" in high_risk_str or "Plot 44-B" in high_risk_str, "High-risk notary or survey signal missing"

    # Check benign attributes (e.g. Bank)
    benign_str = " ".join(cluster["benign_shared_attributes"])
    assert "Bank" in benign_str or "State Bank of India" in benign_str, "Benign banking attribute missing"

    # Verify that clean institutions sharing a bank branch do NOT get merged into the collusion ring
    for clean_id in ["APP-001", "APP-002", "APP-003"]:
        assert clean_id not in cluster["institutions"]
