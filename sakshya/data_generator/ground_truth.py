"""
Sakshya Ground Truth Loader & Evaluator
Provides programmatic access to ground truth records and expected findings.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from sakshya.core.config import DATA_DIR


def load_ground_truth() -> Dict[str, Any]:
    """Load the ground-truth dictionary for all 30 synthetic applications."""
    gt_path = DATA_DIR / "ground_truth.json"
    if not gt_path.exists():
        raise FileNotFoundError(f"Ground truth not found at {gt_path}. Run generator first.")
    with open(gt_path, "r") as f:
        return json.load(f)


def load_mock_issuer_db() -> Dict[str, Any]:
    """Load mock issuer authority records."""
    mock_path = DATA_DIR / "mock_issuer_registry.json"
    if not mock_path.exists():
        raise FileNotFoundError(f"Mock issuer registry not found at {mock_path}.")
    with open(mock_path, "r") as f:
        return json.load(f)


def get_expected_defects(application_id: str) -> List[str]:
    """Return list of planted defect codes for an application."""
    gt = load_ground_truth()
    record = gt.get(application_id, {})
    return record.get("injected_defects", [])


def is_ground_truth_clean(application_id: str) -> bool:
    """Check if application was designated clean in ground truth."""
    gt = load_ground_truth()
    record = gt.get(application_id, {})
    return record.get("is_clean", True)
