"""
Sakshya Test Suite: Validation Pipeline & Rule Findings
Verifies that the pipeline processes documents dynamically, produces explainable findings,
and does not falsely flag clean applications.
"""

from pathlib import Path
import pytest
from sakshya.pipeline.pipeline_runner import PipelineRunner
from sakshya.data_generator.ground_truth import load_ground_truth
from sakshya.core.models import ApplicationStatus


@pytest.fixture(scope="module")
def runner():
    return PipelineRunner()


@pytest.fixture(scope="module")
def ground_truth():
    return load_ground_truth()


def test_clean_applications_not_flagged(runner, ground_truth):
    """Verify that clean applications (APP-001 to APP-010) pass with zero defect findings."""
    for i in range(1, 11):
        app_id = f"APP-{i:03d}"
        app_data = ground_truth[app_id]
        res = runner.process_application(app_data)

        assert res["status"] == ApplicationStatus.VERIFIED_AUTO.value, (
            f"Clean app {app_id} got status {res['status']} instead of VERIFIED_AUTO"
        )
        assert res["findings_count"] == 0, (
            f"Clean app {app_id} has unexpected findings: {res['findings']}"
        )
        assert res["confidence"] >= 0.85, (
            f"Clean app {app_id} has confidence {res['confidence']} < 0.85"
        )


def test_missing_document_detected(runner, ground_truth):
    """Verify missing mandatory documents are flagged with critical finding."""
    app_data = ground_truth["APP-011"]  # Missing Fire NOC
    res = runner.process_application(app_data)

    assert res["status"] == ApplicationStatus.NEEDS_OFFICER_REVIEW.value
    finding_codes = [f["code"] for f in res["findings"]]
    assert "ERR_MISSING_MANDATORY_DOC" in finding_codes


def test_expired_document_detected(runner, ground_truth):
    """Verify expired certificate produces explainable validity finding."""
    app_data = ground_truth["APP-013"]  # Expired Fire NOC
    res = runner.process_application(app_data)

    assert res["status"] == ApplicationStatus.NEEDS_OFFICER_REVIEW.value
    finding_codes = [f["code"] for f in res["findings"]]
    assert "ERR_EXPIRED_DOCUMENT" in finding_codes


def test_all_five_planted_contradictions(runner, ground_truth):
    """Verify all 5 planted cross-document contradictions are detected and flagged."""
    contradiction_mapping = {
        "APP-015": "ERR_CONTRADICTION_LAND_AREA",
        "APP-016": "ERR_CONTRADICTION_INSTITUTION_NAME",
        "APP-017": "ERR_CONTRADICTION_SURVEY_NUMBER",
        "APP-018": "ERR_CONTRADICTION_TEMPORAL_SEQUENCE",
        "APP-019": "ERR_CONTRADICTION_CERTIFICATE_NUMBER",
    }

    for app_id, expected_code in contradiction_mapping.items():
        app_data = ground_truth[app_id]
        res = runner.process_application(app_data)

        assert res["status"] == ApplicationStatus.FLAGGED_ANOMALY.value, (
            f"{app_id} was expected to be FLAGGED_ANOMALY, got {res['status']}"
        )
        finding_codes = [f["code"] for f in res["findings"]]
        assert expected_code in finding_codes, (
            f"Expected {expected_code} in {app_id}, found {finding_codes}"
        )


def test_suspicious_alterations_detected(runner, ground_truth):
    """Verify simulated suspicious metadata and visual font alterations are flagged."""
    res_meta = runner.process_application(ground_truth["APP-021"])
    meta_codes = [f["code"] for f in res_meta["findings"]]
    assert "ANOMALY_PDF_METADATA_DATE_MISMATCH" in meta_codes

    res_font = runner.process_application(ground_truth["APP-022"])
    font_codes = [f["code"] for f in res_font["findings"]]
    assert "ANOMALY_SUSPICIOUS_FONT_LAND_ALTERATION" in font_codes
