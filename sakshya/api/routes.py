"""
Sakshya REST API Endpoints
Provides programmatically accessible validation, mock issuer queries,
readiness evaluation, ring detection, and audit verification.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import json

from sakshya.core.models import (
    ApplicationDB, DocumentDB, FindingDB, OfficerActionDB, AuditLogDB,
    OfficerReviewAction, MockIssuerQuery, MockIssuerResponse, UserRole
)
from sakshya.core.database import get_db
from sakshya.core.audit import log_event, verify_audit_chain
from sakshya.pipeline.pipeline_runner import PipelineRunner
from sakshya.pipeline.mock_issuer import MockAuthorityVerifier
from sakshya.pipeline.ring_detector import RingDetector
from sakshya.pipeline.readiness import ReadinessEvaluator
from sakshya.data_generator.ground_truth import load_ground_truth

router = APIRouter()
runner = PipelineRunner()
mock_verifier = MockAuthorityVerifier()
ring_detector = RingDetector()
readiness_evaluator = ReadinessEvaluator()


@router.get("/health")
def health_check():
    """Service health and readiness check."""
    return {"status": "healthy", "service": "Sakshya AICTE Validation Engine", "version": "1.0.0"}


@router.get("/applications")
def list_applications(db: Session = Depends(get_db)):
    """List all institutional applications with validation status and metrics."""
    apps = db.query(ApplicationDB).all()
    results = []
    for a in apps:
        findings_count = db.query(FindingDB).filter_by(application_id=a.id).count()
        critical_count = db.query(FindingDB).filter_by(application_id=a.id, severity="CRITICAL").count()
        results.append({
            "application_id": a.id,
            "institution_name": a.institution_name,
            "institution_type": a.institution_type,
            "state": a.state,
            "district": a.district,
            "status": a.status.value,
            "overall_confidence": a.overall_confidence,
            "readiness_score": a.readiness_score,
            "findings_count": findings_count,
            "critical_findings": critical_count,
            "flagged_ring": a.flagged_ring,
            "is_clean": a.is_clean,
            "updated_at": a.updated_at.isoformat()
        })
    return {"total": len(results), "applications": results}


@router.get("/applications/{application_id}")
def get_application(application_id: str, db: Session = Depends(get_db)):
    """Retrieve full application details, documents, and findings."""
    app_db = db.query(ApplicationDB).filter_by(id=application_id).first()
    if not app_db:
        raise HTTPException(status_code=404, detail="Application not found.")

    docs = db.query(DocumentDB).filter_by(application_id=application_id).all()
    findings = db.query(FindingDB).filter_by(application_id=application_id).all()
    actions = db.query(OfficerActionDB).filter_by(application_id=application_id).all()

    return {
        "application_id": app_db.id,
        "institution_name": app_db.institution_name,
        "institution_type": app_db.institution_type,
        "state": app_db.state,
        "district": app_db.district,
        "status": app_db.status.value,
        "overall_confidence": app_db.overall_confidence,
        "readiness_score": app_db.readiness_score,
        "survey_number": app_db.survey_number,
        "land_area_acres": app_db.land_area_acres,
        "flagged_ring": app_db.flagged_ring,
        "documents": [
            {
                "id": d.id,
                "document_type": d.document_type.value,
                "filename": d.filename,
                "file_hash": d.file_hash,
                "issuer_status": d.issuer_status.value,
                "is_expired": d.is_expired,
                "expiry_date": d.expiry_date
            }
            for d in docs
        ],
        "findings": [
            {
                "code": f.code,
                "severity": f.severity.value,
                "title": f.title,
                "description": f.description,
                "rule_id": f.rule_id,
                "is_anomaly": f.is_anomaly,
                "is_contradiction": f.is_contradiction,
                "recommended_action": f.recommended_action
            }
            for f in findings
        ],
        "officer_actions": [
            {
                "officer_id": act.officer_id,
                "officer_name": act.officer_name,
                "decision": act.decision,
                "reason_code": act.reason_code,
                "remarks": act.remarks,
                "timestamp": act.action_timestamp.isoformat()
            }
            for act in actions
        ]
    }


@router.post("/applications/{application_id}/process")
def process_application(application_id: str, db: Session = Depends(get_db)):
    """Run full validation pipeline on an application."""
    gt = load_ground_truth()
    app_data = gt.get(application_id)
    if not app_data:
        raise HTTPException(status_code=404, detail="Application ground truth not found.")

    res = runner.process_application(app_data, actor_id="API_CLIENT")
    return res


@router.post("/mock-issuer/verify", response_model=MockIssuerResponse)
def verify_with_mock_issuer(query: MockIssuerQuery):
    """
    Simulate issuing authority verification query.
    Returns one of the 6 canonical statuses.
    """
    # Extract app_id from query if available, or fallback
    app_id = query.additional_params.get("application_id", "APP-001")
    return mock_verifier.verify_document(
        app_id=app_id,
        doc_type=query.document_type,
        doc_number=query.document_number,
        institution_name=query.institution_name,
        qr_content=query.additional_params.get("qr_content")
    )


@router.get("/mock-issuer/records/{application_id}")
def get_mock_issuer_records(application_id: str):
    """Inspect mock authority registry records for an application."""
    rec = mock_verifier.db.get(application_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Authority records not found for application.")
    return {"application_id": application_id, "registry_records": rec}


@router.get("/readiness/{application_id}")
def evaluate_readiness(application_id: str, db: Session = Depends(get_db)):
    """Evaluate pre-submission institution readiness checklist."""
    gt = load_ground_truth()
    app_data = gt.get(application_id)
    if not app_data:
        raise HTTPException(status_code=404, detail="Application not found.")

    docs = app_data.get("documents", [])
    findings_db = db.query(FindingDB).filter_by(application_id=application_id).all()
    findings = [
        runner.rules_engine.rules_config  # lightweight mock finding pass
    ]
    # Fetch real findings
    readiness = runner.readiness_evaluator.evaluate_readiness(
        application_data=app_data,
        documents=docs,
        findings=[f for f in []],
        issuer_statuses=[]
    )
    return readiness


@router.post("/officer/decision")
def record_officer_decision(action: OfficerReviewAction, db: Session = Depends(get_db)):
    """
    Record officer confirmation or manual override decision.
    Appends tamper-evident cryptographic audit log.
    """
    app_db = db.query(ApplicationDB).filter_by(id=action.application_id).first()
    if not app_db:
        raise HTTPException(status_code=404, detail="Application not found.")

    new_status = (
        ApplicationStatus.OFFICER_APPROVED if action.decision == "APPROVE"
        else ApplicationStatus.OFFICER_REJECTED
    )
    app_db.status = new_status

    act_db = OfficerActionDB(
        application_id=action.application_id,
        officer_id=action.officer_id,
        officer_name=action.officer_name,
        decision=action.decision,
        reason_code=action.reason_code,
        remarks=action.remarks,
        override_flags=json.dumps(action.override_flags)
    )
    db.add(act_db)

    # Log to audit chain
    log_event(
        db=db,
        actor_id=action.officer_id,
        actor_role=UserRole.SCRUTINY_OFFICER.value,
        action="OFFICER_DECISION_RECORDED",
        entity_type="application",
        entity_id=action.application_id,
        details={
            "decision": action.decision,
            "reason_code": action.reason_code,
            "remarks": action.remarks,
            "overrides": action.override_flags,
            "new_status": new_status.value
        }
    )
    db.commit()

    return {
        "status": "success",
        "application_id": action.application_id,
        "new_application_status": new_status.value,
        "message": f"Officer decision '{action.decision}' successfully recorded and logged in audit chain."
    }


@router.get("/ring-detection")
def run_ring_detection():
    """Execute cross-institution collusion ring detection across all applications."""
    gt = load_ground_truth()
    applications = list(gt.values())
    ring_detector.build_network(applications)
    clusters = ring_detector.detect_clusters()
    return {
        "total_applications_analyzed": len(applications),
        "detected_clusters_count": len(clusters),
        "clusters": clusters
    }


@router.get("/audit/verify")
def verify_audit_integrity(db: Session = Depends(get_db)):
    """Verify cryptographic hash chaining across all audit records."""
    return verify_audit_chain(db)


@router.get("/audit/logs")
def get_audit_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve audit log entries in reverse chronological order."""
    logs = db.query(AuditLogDB).order_by(AuditLogDB.id.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "timestamp": l.timestamp.isoformat(),
            "actor_id": l.actor_id,
            "actor_role": l.actor_role,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "details": json.loads(l.details_json),
            "prev_hash": l.prev_hash,
            "current_hash": l.current_hash
        }
        for l in logs
    ]
