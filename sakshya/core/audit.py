"""
Sakshya Cryptographic Hash-Chained Audit Log
Ensures tamper-evident immutability for all institutional uploads,
evaluations, mock verifications, and officer actions.
"""

import json
import hashlib
from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from sakshya.core.models import AuditLogDB, UserRole

GENESIS_PREV_HASH = "0" * 64


def calculate_entry_hash(
    prev_hash: str,
    timestamp_str: str,
    actor_id: str,
    actor_role: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details_json: str
) -> str:
    """Calculate SHA-256 hash chaining previous hash with current block contents."""
    payload = f"{prev_hash}|{timestamp_str}|{actor_id}|{actor_role}|{action}|{entity_type}|{entity_id}|{details_json}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def log_event(
    db: Session,
    actor_id: str,
    actor_role: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: Optional[dict[str, Any]] = None,
    timestamp: Optional[datetime] = None
) -> AuditLogDB:
    """Append a new tamper-evident audit record to the hash chain."""
    if details is None:
        details = {}
    
    # Canonical JSON string representation for stable hashing
    details_json = json.dumps(details, sort_keys=True)
    if timestamp is None:
        timestamp = datetime.utcnow()
    timestamp_str = timestamp.isoformat()

    # Retrieve last entry in audit log to link hashes
    last_entry = db.query(AuditLogDB).order_by(AuditLogDB.id.desc()).first()
    prev_hash = last_entry.current_hash if last_entry else GENESIS_PREV_HASH

    current_hash = calculate_entry_hash(
        prev_hash=prev_hash,
        timestamp_str=timestamp_str,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=details_json
    )

    entry = AuditLogDB(
        timestamp=timestamp,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=details_json,
        prev_hash=prev_hash,
        current_hash=current_hash
    )
    db.add(entry)
    db.flush()
    return entry


def verify_audit_chain(db: Session) -> dict[str, Any]:
    """
    Verify the cryptographic integrity of the entire audit chain.
    Detects any record alteration, deletion, or insertion.
    """
    records = db.query(AuditLogDB).order_by(AuditLogDB.id.asc()).all()
    if not records:
        return {
            "valid": True,
            "total_records": 0,
            "message": "Audit log is empty; genesis state valid."
        }

    expected_prev = GENESIS_PREV_HASH
    for idx, entry in enumerate(records):
        # 1. Check prev_hash pointer
        if entry.prev_hash != expected_prev:
            return {
                "valid": False,
                "total_records": len(records),
                "tampered_record_id": entry.id,
                "record_index": idx,
                "error": f"Broken chain pointer at ID {entry.id}: recorded prev_hash '{entry.prev_hash[:12]}...' does not match expected '{expected_prev[:12]}...'"
            }

        # 2. Recalculate hash from stored fields
        calculated = calculate_entry_hash(
            prev_hash=entry.prev_hash,
            timestamp_str=entry.timestamp.isoformat(),
            actor_id=entry.actor_id,
            actor_role=entry.actor_role,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            details_json=entry.details_json
        )

        if calculated != entry.current_hash:
            return {
                "valid": False,
                "total_records": len(records),
                "tampered_record_id": entry.id,
                "record_index": idx,
                "error": f"Content tampering detected at ID {entry.id}: recalculation failed."
            }

        expected_prev = entry.current_hash

    return {
        "valid": True,
        "total_records": len(records),
        "latest_block_hash": expected_prev,
        "message": f"Cryptographic integrity verified across all {len(records)} audit records."
    }
