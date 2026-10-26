"""
Sakshya Core Models
Pydantic Schemas and SQLAlchemy Database Entities
"""

from datetime import datetime
from typing import Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ==========================================
# Enumerations
# ==========================================

class UserRole(str, Enum):
    INSTITUTION = "institution"
    SCRUTINY_OFFICER = "scrutiny_officer"
    ADMIN = "admin"


class ApplicationStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    VERIFIED_AUTO = "VERIFIED_AUTO"
    NEEDS_OFFICER_REVIEW = "NEEDS_OFFICER_REVIEW"
    OFFICER_APPROVED = "OFFICER_APPROVED"
    OFFICER_REJECTED = "OFFICER_REJECTED"
    FLAGGED_ANOMALY = "FLAGGED_ANOMALY"


class DocumentType(str, Enum):
    LAND_TITLE = "LAND_TITLE"
    BUILDING_PLAN = "BUILDING_PLAN"
    FIRE_NOC = "FIRE_NOC"
    MANDATORY_DISCLOSURE = "MANDATORY_DISCLOSURE"
    SOCIETY_REGISTRATION = "SOCIETY_REGISTRATION"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    MISMATCH_DETECTED = "mismatch_detected"
    EXPIRED = "expired"
    VERIFICATION_PENDING = "verification_pending"
    SOURCE_UNAVAILABLE = "source_unavailable"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class FindingSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ==========================================
# Pydantic Schemas
# ==========================================

class ExtractedField(BaseModel):
    field_name: str
    field_value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    source_document: str
    page_number: int = 1
    bounding_box: Optional[list[float]] = None  # [x0, y0, x1, y1]
    extraction_method: str = "regex"  # regex, layout, rapidfuzz, ocr


class Finding(BaseModel):
    code: str
    severity: FindingSeverity
    title: str
    description: str
    source_document: Optional[str] = None
    rule_id: Optional[str] = None
    evidence_claims: list[str] = []
    recommended_action: str = ""
    is_anomaly: bool = False
    is_contradiction: bool = False


class ReadinessItem(BaseModel):
    check_name: str
    category: str  # Mandatory Document, Expiry, Consistency, Verification
    status: bool   # Pass / Fail
    score: float
    weight: float
    details: str


class ReadinessResult(BaseModel):
    readiness_score: float = Field(ge=0.0, le=100.0)
    is_ready_for_submission: bool
    summary: str
    checklist: list[ReadinessItem]
    formula_note: str = "Score = (Weighted Sum of Passed Checks / Total Weight) * 100. Note: This represents regulatory completeness, not approval probability."


class MockIssuerQuery(BaseModel):
    document_type: str
    document_number: str
    institution_name: str
    issuing_authority: str
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    additional_params: dict[str, Any] = {}


class MockIssuerResponse(BaseModel):
    query_id: str
    status: VerificationStatus
    matched: bool
    authority_name: str
    authority_record: Optional[dict[str, Any]] = None
    mismatch_details: list[str] = []
    latency_ms: float = 0.0
    qr_verified: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ApplicationCreate(BaseModel):
    application_id: str
    institution_id: str
    institution_name: str
    institution_type: str  # Engineering, Management, Pharmacy, Polytechnic
    state: str
    district: str
    applied_intake: int
    land_area_acres: float
    survey_number: str
    society_trust_name: str
    architect_license: str
    notary_registration: str


class ApplicationSummary(BaseModel):
    application_id: str
    institution_name: str
    institution_type: str
    status: ApplicationStatus
    overall_confidence: float
    readiness_score: float
    total_findings: int
    critical_findings: int
    flagged_ring: bool
    submitted_at: datetime
    updated_at: datetime


class OfficerReviewAction(BaseModel):
    application_id: str
    officer_id: str
    officer_name: str
    decision: str  # APPROVE, REJECT, REQUEST_CLARIFICATION
    reason_code: str
    remarks: str
    override_flags: list[str] = []


class AuditLogEntry(BaseModel):
    id: Optional[int] = None
    timestamp: datetime
    actor_id: str
    actor_role: UserRole
    action: str
    entity_type: str
    entity_id: str
    details: dict[str, Any]
    prev_hash: str
    hash: str


# ==========================================
# SQLAlchemy ORM Models
# ==========================================

class ApplicationDB(Base):
    __tablename__ = "applications"

    id = Column(String(64), primary_key=True)
    institution_id = Column(String(64), nullable=False, index=True)
    institution_name = Column(String(255), nullable=False)
    institution_type = Column(String(64), nullable=False)
    state = Column(String(64), nullable=False)
    district = Column(String(64), nullable=False)
    applied_intake = Column(Integer, default=0)
    land_area_acres = Column(Float, default=0.0)
    survey_number = Column(String(128), default="")
    society_trust_name = Column(String(255), default="")
    architect_license = Column(String(128), default="")
    notary_registration = Column(String(128), default="")
    
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.SUBMITTED, index=True)
    overall_confidence = Column(Float, default=1.0)
    readiness_score = Column(Float, default=0.0)
    
    is_clean = Column(Boolean, default=True)
    injected_defects = Column(Text, default="[]")  # JSON list of defect codes
    flagged_ring = Column(Boolean, default=False)
    ring_cluster_id = Column(String(64), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = relationship("DocumentDB", back_populates="application", cascade="all, delete-orphan")
    findings = relationship("FindingDB", back_populates="application", cascade="all, delete-orphan")
    officer_actions = relationship("OfficerActionDB", back_populates="application", cascade="all, delete-orphan")


class DocumentDB(Base):
    __tablename__ = "documents"

    id = Column(String(64), primary_key=True)
    application_id = Column(String(64), ForeignKey("applications.id"), nullable=False, index=True)
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_hash = Column(String(64), nullable=False)
    perceptual_hash = Column(String(64), default="")
    file_size_bytes = Column(Integer, default=0)
    page_count = Column(Integer, default=1)
    
    ocr_applied = Column(Boolean, default=False)
    extracted_text_snippet = Column(Text, default="")
    qr_content = Column(Text, default="")
    
    issuer_status = Column(SQLEnum(VerificationStatus), default=VerificationStatus.VERIFICATION_PENDING)
    is_expired = Column(Boolean, default=False)
    expiry_date = Column(String(32), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("ApplicationDB", back_populates="documents")
    fields = relationship("ExtractedFieldDB", back_populates="document", cascade="all, delete-orphan")


class ExtractedFieldDB(Base):
    __tablename__ = "extracted_fields"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), ForeignKey("documents.id"), nullable=False, index=True)
    field_name = Column(String(128), nullable=False, index=True)
    field_value = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0)
    page_number = Column(Integer, default=1)
    extraction_method = Column(String(64), default="regex")

    document = relationship("DocumentDB", back_populates="fields")


class FindingDB(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(String(64), ForeignKey("applications.id"), nullable=False, index=True)
    document_id = Column(String(64), nullable=True)
    code = Column(String(64), nullable=False, index=True)
    severity = Column(SQLEnum(FindingSeverity), default=FindingSeverity.INFO)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    rule_id = Column(String(64), nullable=True)
    evidence_claims = Column(Text, default="[]")  # JSON list
    recommended_action = Column(Text, default="")
    is_anomaly = Column(Boolean, default=False)
    is_contradiction = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("ApplicationDB", back_populates="findings")


class OfficerActionDB(Base):
    __tablename__ = "officer_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(String(64), ForeignKey("applications.id"), nullable=False, index=True)
    officer_id = Column(String(64), nullable=False)
    officer_name = Column(String(128), nullable=False)
    decision = Column(String(64), nullable=False)  # APPROVE, REJECT, OVERRIDE
    reason_code = Column(String(64), nullable=False)
    remarks = Column(Text, default="")
    override_flags = Column(Text, default="[]")  # JSON list
    action_timestamp = Column(DateTime, default=datetime.utcnow)

    application = relationship("ApplicationDB", back_populates="officer_actions")


class AuditLogDB(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    actor_id = Column(String(64), nullable=False)
    actor_role = Column(String(32), nullable=False)
    action = Column(String(128), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False, index=True)
    details_json = Column(Text, default="{}")
    prev_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False, unique=True)
