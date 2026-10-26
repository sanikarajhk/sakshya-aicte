"""
Sakshya Test Suite: Mock Issuing Authority Verification
Verifies that all 6 statutory authority verification statuses and QR validation operate correctly.
"""

import pytest
from sakshya.pipeline.mock_issuer import MockAuthorityVerifier
from sakshya.core.models import VerificationStatus


@pytest.fixture
def verifier():
    return MockAuthorityVerifier()


def test_all_six_verification_statuses_supported(verifier):
    """Verify that all six canonical verification statuses can be queried and returned."""
    test_cases = [
        ("APP-001", "LAND_TITLE", VerificationStatus.VERIFIED),
        ("APP-016", "BUILDING_PLAN", VerificationStatus.MISMATCH_DETECTED),
        ("APP-013", "FIRE_NOC", VerificationStatus.EXPIRED),
        ("APP-011", "FIRE_NOC", VerificationStatus.VERIFICATION_PENDING),
        ("APP-023", "LAND_TITLE", VerificationStatus.SOURCE_UNAVAILABLE),
        ("APP-024", "LAND_TITLE", VerificationStatus.MANUAL_REVIEW_REQUIRED),
    ]

    for app_id, doc_type, expected_status in test_cases:
        resp = verifier.verify_document(
            app_id=app_id,
            doc_type=doc_type,
            doc_number="TEST-DOC-123",
            institution_name="Test College"
        )
        assert resp.status == expected_status, (
            f"Expected status '{expected_status.value}' for {app_id} {doc_type}, got '{resp.status.value}'"
        )
        assert len(resp.authority_name) > 0
        assert resp.latency_ms > 0


def test_qr_verification_flag(verifier):
    """Verify that presence of QR code content activates qr_verified flag."""
    resp_with_qr = verifier.verify_document(
        app_id="APP-001",
        doc_type="LAND_TITLE",
        doc_number="REG-DEED-2021-DL",
        institution_name="Vidyapeeth Institute of Technology",
        qr_content="STATE_REV_REG:APP-001:DEED-2021:LAND:5.5"
    )
    assert resp_with_qr.qr_verified is True

    resp_without_qr = verifier.verify_document(
        app_id="APP-001",
        doc_type="LAND_TITLE",
        doc_number="REG-DEED-2021-DL",
        institution_name="Vidyapeeth Institute of Technology",
        qr_content=None
    )
    assert resp_without_qr.qr_verified is False
