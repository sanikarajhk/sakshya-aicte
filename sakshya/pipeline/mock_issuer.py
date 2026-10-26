"""
Sakshya Mock Issuing Authority Verification Service
Simulates external statutory authority API queries and QR code validation.
Covers all 6 required verification statuses:
1. verified
2. mismatch_detected
3. expired
4. verification_pending
5. source_unavailable
6. manual_review_required
"""

import time
from typing import Dict, Any, Optional
from sakshya.core.models import VerificationStatus, MockIssuerQuery, MockIssuerResponse
from sakshya.data_generator.ground_truth import load_mock_issuer_db


class MockAuthorityVerifier:
    """Simulates REST integration with state revenue, municipal, and fire registries."""

    def __init__(self):
        self._db: Optional[Dict[str, Any]] = None

    @property
    def db(self) -> Dict[str, Any]:
        if self._db is None:
            self._db = load_mock_issuer_db()
        return self._db

    def verify_document(
        self,
        app_id: str,
        doc_type: str,
        doc_number: str,
        institution_name: str,
        qr_content: Optional[str] = None
    ) -> MockIssuerResponse:
        """
        Query mock authority database for a specific document and return
        one of the 6 canonical statuses with realistic metadata.
        """
        start_time = time.time()
        app_records = self.db.get(app_id, {})

        # Determine target authority record
        authority_key = "land_registry"
        authority_name = "State Department of Land Resources & Revenue"

        if "BUILDING" in doc_type.upper():
            authority_key = "municipal_bplan"
            authority_name = "Directorate of Town Planning & Municipal Sanctions"
        elif "FIRE" in doc_type.upper():
            authority_key = "fire_department"
            authority_name = "State Fire Prevention & Emergency Services Directorate"
        elif "MANDATORY" in doc_type.upper():
            authority_key = "aicte_central"
            authority_name = "AICTE National Institutional Portal Registry"

        rec = app_records.get(authority_key, {})
        status_str = rec.get("status", "verified")
        try:
            status = VerificationStatus(status_str)
        except ValueError:
            status = VerificationStatus.VERIFIED

        mismatch_details = []
        matched = False
        qr_verified = qr_content is not None and len(qr_content) > 0

        if status == VerificationStatus.VERIFIED:
            matched = True
        elif status == VerificationStatus.MISMATCH_DETECTED:
            matched = False
            mismatch_details.append(
                f"Authority database records institution as '{rec.get('institution_name', 'Different Entity')}' "
                f"whereas submitted document claims '{institution_name}'."
            )
        elif status == VerificationStatus.EXPIRED:
            matched = False
            mismatch_details.append(
                f"Authority record indicates certificate expired on {rec.get('expiry_date', '2022-01-01')}."
            )
        elif status == VerificationStatus.SOURCE_UNAVAILABLE:
            matched = False
            mismatch_details.append("External State Revenue Portal timed out after 3 retry attempts.")
        elif status == VerificationStatus.MANUAL_REVIEW_REQUIRED:
            matched = False
            mismatch_details.append("Active caveat/encumbrance dispute recorded against survey parcel in district court registry.")
        elif status == VerificationStatus.VERIFICATION_PENDING:
            matched = False
            mismatch_details.append("Application filed with issuing authority but departmental site inspection clearance pending.")

        latency_ms = (time.time() - start_time) * 1000.0 + 45.0  # simulate network latency

        return MockIssuerResponse(
            query_id=f"QRY-{app_id}-{doc_type[:4]}",
            status=status,
            matched=matched,
            authority_name=authority_name,
            authority_record=rec,
            mismatch_details=mismatch_details,
            latency_ms=round(latency_ms, 2),
            qr_verified=qr_verified
        )
