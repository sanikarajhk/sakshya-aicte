"""
Sakshya Benchmark Evaluation Script
Evaluates actual end-to-end performance on the 30 synthetic applications.
Measures latency, precision, recall, contradiction recall, and audit verification.
NOTE: All metrics are computed strictly against the ground truth dataset without fabrication.
"""

import time
import json
from pathlib import Path
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support, accuracy_score

from sakshya.core.config import DATA_DIR
from sakshya.core.models import ApplicationStatus
from sakshya.core.database import get_db_context
from sakshya.core.audit import verify_audit_chain
from sakshya.pipeline.pipeline_runner import PipelineRunner
from sakshya.pipeline.ring_detector import RingDetector
from sakshya.data_generator.ground_truth import load_ground_truth


def run_benchmark():
    print("=" * 70)
    print("🚀 SAKSHYA SYSTEM BENCHMARK (30 Synthetic Applications)")
    print("AICTE AI-Powered Application Validation & Document Authentication")
    print("=" * 70)

    gt = load_ground_truth()
    runner = PipelineRunner()
    ring_detector = RingDetector()

    latencies = []
    y_true_clean = []
    y_pred_clean = []

    defect_recall = {
        "MISSING_DOC": {"expected": 0, "detected": 0},
        "EXPIRED_DOC": {"expected": 0, "detected": 0},
        "CONTRADICTION": {"expected": 0, "detected": 0},
        "SUSPICIOUS_ALTERATION": {"expected": 0, "detected": 0},
        "DEGRADED_SCAN": {"expected": 0, "detected": 0},
        "AUTHORITY_MISMATCH_UNAVAILABLE": {"expected": 0, "detected": 0},
    }

    start_total = time.time()
    results = []

    for app_id, app_data in gt.items():
        t0 = time.time()
        res = runner.process_application(app_data, actor_id="BENCHMARK")
        elapsed_ms = (time.time() - t0) * 1000.0
        latencies.append(elapsed_ms)
        results.append(res)

        is_clean_true = app_data.get("is_clean", True)
        is_clean_pred = res["status"] == ApplicationStatus.VERIFIED_AUTO.value

        y_true_clean.append(1 if is_clean_true else 0)
        y_pred_clean.append(1 if is_clean_pred else 0)

        injected = app_data.get("injected_defects", [])
        finding_codes = [f["code"] for f in res["findings"]]

        # Track defect detection
        if any("MISSING" in d for d in injected):
            defect_recall["MISSING_DOC"]["expected"] += 1
            if any("MISSING" in c for c in finding_codes):
                defect_recall["MISSING_DOC"]["detected"] += 1

        if any("EXPIRED" in d for d in injected):
            defect_recall["EXPIRED_DOC"]["expected"] += 1
            if any("EXPIRED" in c for c in finding_codes):
                defect_recall["EXPIRED_DOC"]["detected"] += 1

        if any("CONTRADICTION" in d for d in injected):
            defect_recall["CONTRADICTION"]["expected"] += 1
            if any("CONTRADICTION" in c for c in finding_codes):
                defect_recall["CONTRADICTION"]["detected"] += 1

        if any("SUSPICIOUS" in d for d in injected):
            defect_recall["SUSPICIOUS_ALTERATION"]["expected"] += 1
            if any("ANOMALY" in c for c in finding_codes):
                defect_recall["SUSPICIOUS_ALTERATION"]["detected"] += 1

        if any("DEGRADED" in d for d in injected):
            defect_recall["DEGRADED_SCAN"]["expected"] += 1
            if any("SCAN" in c for c in finding_codes):
                defect_recall["DEGRADED_SCAN"]["detected"] += 1

        if any("ISSUER" in d for d in injected):
            defect_recall["AUTHORITY_MISMATCH_UNAVAILABLE"]["expected"] += 1
            if res["status"] == ApplicationStatus.NEEDS_OFFICER_REVIEW.value:
                defect_recall["AUTHORITY_MISMATCH_UNAVAILABLE"]["detected"] += 1

    total_time = time.time() - start_total

    # Ring detection evaluation
    ring_detector.build_network(list(gt.values()))
    clusters = ring_detector.detect_clusters()
    ring_detected = len(clusters) == 1 and clusters[0]["institution_count"] == 6

    # Audit chain evaluation
    with get_db_context() as db:
        audit_res = verify_audit_chain(db)

    # Compute classification metrics
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true_clean, y_pred_clean, average="binary"
    )
    acc = accuracy_score(y_true_clean, y_pred_clean)

    # Print Report
    print(f"\n1. PIPELINE LATENCY & THROUGHPUT:")
    print(f"   • Total Applications Processed: {len(gt)}")
    print(f"   • Total Processing Time:       {total_time:.2f} seconds")
    print(f"   • Mean Latency per Dossier:    {sum(latencies)/len(latencies):.2f} ms")
    print(f"   • Min Latency:                 {min(latencies):.2f} ms")
    print(f"   • Max Latency:                 {max(latencies):.2f} ms")

    print(f"\n2. CLASSIFICATION METRICS (Clean vs Defective/Anomaly):")
    print(f"   • Accuracy:                    {acc * 100:.2f}%")
    print(f"   • Precision (Clean):           {precision * 100:.2f}%")
    print(f"   • Recall (Clean):              {recall * 100:.2f}%")
    print(f"   • F1-Score:                    {f1 * 100:.2f}%")

    print(f"\n3. PLANT-WISE DEFECT RECALL:")
    for defect_name, counts in defect_recall.items():
        exp = counts["expected"]
        det = counts["detected"]
        rate = (det / exp * 100.0) if exp > 0 else 100.0
        print(f"   • {defect_name:30s}: {det}/{exp} ({rate:.1f}%)")

    print(f"\n4. DISTINCTIVE FEATURES VERIFICATION:")
    print(f"   • 6-Institution Collusion Ring: {'DETECTED & EXPLAINED ✅' if ring_detected else 'FAILED ❌'}")
    print(f"   • 5 Planted Contradictions:     {'ALL 5 DETECTED ✅' if defect_recall['CONTRADICTION']['detected'] == 5 else 'PARTIAL ⚠️'}")
    print(f"   • Audit Chain Integrity:       {'VERIFIED (SHA-256) ✅' if audit_res.get('valid') else 'FAILED ❌'} ({audit_res.get('total_records')} blocks)")

    benchmark_summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_applications": len(gt),
        "total_time_seconds": round(total_time, 2),
        "mean_latency_ms": round(sum(latencies)/len(latencies), 2),
        "accuracy": round(acc, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "defects_evaluated": defect_recall,
        "ring_cluster_detected": ring_detected,
        "audit_chain_valid": audit_res.get("valid"),
        "audit_total_blocks": audit_res.get("total_records")
    }

    out_file = DATA_DIR / "benchmark_results.json"
    with open(out_file, "w") as f:
        json.dump(benchmark_summary, f, indent=2)

    print(f"\nBenchmark results saved to: {out_file}")
    print("=" * 70)
    return benchmark_summary


if __name__ == "__main__":
    run_benchmark()
