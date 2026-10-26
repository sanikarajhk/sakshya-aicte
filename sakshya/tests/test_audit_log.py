"""
Sakshya Test Suite: Cryptographic Hash-Chained Audit Log
Verifies immutable SHA-256 hash chaining, verification, and tamper detection.
"""

from datetime import datetime
import pytest
from sakshya.core.database import get_db_context
from sakshya.core.models import AuditLogDB, UserRole
from sakshya.core.audit import log_event, verify_audit_chain


def test_audit_chain_validity():
    """Verify that the un-tampered audit log passes cryptographic verification."""
    with get_db_context() as db:
        res = verify_audit_chain(db)
        assert res["valid"] is True, f"Audit chain verification failed: {res.get('error')}"
        assert res["total_records"] > 0


def test_tamper_detection():
    """Verify that unauthorized alteration of an audit entry breaks hash chaining."""
    with get_db_context() as db:
        # Append a test event
        entry = log_event(
            db=db,
            actor_id="TEST_ACTOR",
            actor_role=UserRole.SCRUTINY_OFFICER.value,
            action="TEST_ACTION_BEFORE_TAMPER",
            entity_type="application",
            entity_id="APP-999",
            details={"original": "legitimate_data"}
        )
        db.commit()
        entry_id = entry.id
        original_details = entry.details_json

        # Verification must pass initially
        assert verify_audit_chain(db)["valid"] is True

        # Maliciously tamper with the stored JSON payload
        entry.details_json = '{"original": "MALICIOUSLY_ALTERED_DATA"}'
        db.commit()

        # Verification MUST now fail and pinpoint the exact record
        tamper_res = verify_audit_chain(db)
        assert tamper_res["valid"] is False, "Audit chain failed to detect payload tampering!"
        assert tamper_res.get("tampered_record_id") == entry_id

        # Revert change to preserve integrity for subsequent tests
        entry.details_json = original_details
        db.commit()

        # Chain is valid again
        assert verify_audit_chain(db)["valid"] is True
