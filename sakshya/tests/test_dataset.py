"""
Sakshya Test Suite: Synthetic Dataset & Document Files Integrity
Verifies all 30 applications, file existence, byte validity, and reference consistency.
"""

import json
from pathlib import Path
import pytest
from pypdf import PdfReader
from PIL import Image

from sakshya.core.config import DATA_DIR, SYNTHETIC_DIR
from sakshya.data_generator.ground_truth import load_ground_truth


def test_ground_truth_exists():
    """Verify ground truth and summary metadata files exist."""
    gt_file = DATA_DIR / "ground_truth.json"
    csv_file = DATA_DIR / "applications_metadata.csv"
    mock_file = DATA_DIR / "mock_issuer_registry.json"

    assert gt_file.exists(), "ground_truth.json does not exist."
    assert csv_file.exists(), "applications_metadata.csv does not exist."
    assert mock_file.exists(), "mock_issuer_registry.json does not exist."


def test_30_applications_present():
    """Verify exactly 30 institutional applications exist with consistent IDs."""
    gt = load_ground_truth()
    assert len(gt) == 30, f"Expected 30 applications, found {len(gt)}"
    for i in range(1, 31):
        app_id = f"APP-{i:03d}"
        assert app_id in gt, f"Missing {app_id} in ground truth"
        app = gt[app_id]
        assert app["application_id"] == app_id
        assert len(app["institution_name"]) > 5
        assert len(app["documents"]) >= 3, f"{app_id} has fewer than 3 documents"


def test_all_document_files_openable():
    """Verify every document referenced in metadata physically exists and can be parsed."""
    gt = load_ground_truth()
    total_docs_checked = 0

    for app_id, app in gt.items():
        for doc in app["documents"]:
            file_path = Path(doc["file_path"])
            assert file_path.exists(), f"Document file missing: {file_path}"
            assert file_path.stat().st_size > 0, f"Document file empty (0 bytes): {file_path}"

            # Verify file can be opened and parsed
            if file_path.suffix.lower() == ".pdf":
                reader = PdfReader(str(file_path))
                assert len(reader.pages) >= 1, f"PDF has 0 pages: {file_path}"
            elif file_path.suffix.lower() in [".png", ".jpg"]:
                img = Image.open(str(file_path))
                assert img.size[0] > 10 and img.size[1] > 10, f"Image dimensions invalid: {file_path}"

            total_docs_checked += 1

    assert total_docs_checked >= 100, f"Expected at least 100 documents across 30 apps, found {total_docs_checked}"
