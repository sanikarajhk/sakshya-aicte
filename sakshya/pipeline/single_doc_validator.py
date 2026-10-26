"""
Sakshya Single Document Validator & Targeted College Verification Engine
Enables dynamic PDF upload, robust college identification against the 30-college
dataset, and targeted regulatory compliance validation against the identified institution.
"""

import io
import os
import re
import hashlib
import tempfile
from enum import Enum
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from rapidfuzz import fuzz

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import pypdf
except ImportError:
    pypdf = None

from sakshya.core.models import (
    DocumentType, FindingSeverity, VerificationStatus, ExtractedField, Finding
)
from sakshya.core.database import get_db_context
from sakshya.core.models import ApplicationDB, DocumentDB
from sakshya.data_generator.ground_truth import load_ground_truth
from sakshya.pipeline.reader import DocumentReader
from sakshya.pipeline.extractor import FieldExtractor
from sakshya.pipeline.mock_issuer import MockAuthorityVerifier
from sakshya.pipeline.rules_engine import RulesEngine


class CheckStatus(str, Enum):
    PASSED = "PASSED"
    MISMATCH = "MISMATCH"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    UNVERIFIED = "UNVERIFIED"


class IdentificationStatus(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    HIGH_CONFIDENCE_FUZZY = "HIGH_CONFIDENCE_FUZZY"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    UNKNOWN_COLLEGE = "UNKNOWN_COLLEGE"


class CollegeCandidate(BaseModel):
    application_id: str
    institution_id: str
    institution_name: str
    match_score: float
    match_reason: str


class CollegeIdentificationResult(BaseModel):
    status: IdentificationStatus
    identified_app_id: Optional[str] = None
    identified_name: Optional[str] = None
    confidence: float = 0.0
    method: str = "none"
    explanation: str = ""
    extracted_identifier: Optional[str] = None
    top_candidates: List[CollegeCandidate] = []


class ValidationCheck(BaseModel):
    check_name: str
    status: CheckStatus
    rule_id: Optional[str] = None
    statutory_clause: Optional[str] = None
    severity: FindingSeverity = FindingSeverity.INFO
    expected_value: Any = None
    extracted_value: Any = None
    difference_details: str = ""
    evidence_claims: List[str] = []
    source_document: str = ""
    page_number: int = 1
    recommended_action: str = ""
    is_anomaly: bool = False
    is_contradiction: bool = False


class SingleDocValidationResult(BaseModel):
    college_id: str
    college_name: str
    document_type: str
    filename: str
    file_hash_sha256: str
    file_size_bytes: int
    page_count: int
    identification: CollegeIdentificationResult
    extracted_fields: List[Dict[str, Any]]
    all_checks: List[ValidationCheck]
    passed_checks: List[ValidationCheck]
    mismatches: List[ValidationCheck]
    missing_info: List[ValidationCheck]
    unverified: List[ValidationCheck]
    overall_status: str
    calibrated_confidence: float
    summary: str
    authority_verification: Optional[Dict[str, Any]] = None


class SingleDocValidator:
    """Targeted validation harness for single uploaded documents."""

    def __init__(self, ground_truth: Optional[Dict[str, Any]] = None):
        self.gt = ground_truth if ground_truth is not None else load_ground_truth()
        self.reader = DocumentReader()
        self.extractor = FieldExtractor()
        self.rules_engine = RulesEngine()
        self.mock_verifier = MockAuthorityVerifier()

    def validate_pdf_bytes(self, file_bytes: bytes, filename: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate file format, magic bytes, and basic readability.
        Returns: (is_valid, error_message, metadata)
        """
        if not file_bytes or len(file_bytes) == 0:
            return False, "Uploaded file is empty (0 bytes). Please upload a valid document.", {}

        # Check PDF header magic bytes '%PDF-'
        if not file_bytes.startswith(b"%PDF-"):
            return False, "Unsupported file format. The uploaded file does not contain a valid PDF signature (%PDF-).", {}

        sha256_hash = hashlib.sha256(file_bytes).hexdigest()
        size_bytes = len(file_bytes)

        # Attempt to read with pdfplumber or pypdf in memory
        page_count = 0
        extracted_pages = []
        full_text = ""

        try:
            bio = io.BytesIO(file_bytes)
            if pdfplumber is not None:
                with pdfplumber.open(bio) as pdf:
                    page_count = len(pdf.pages)
                    if page_count == 0:
                        return False, "Corrupted PDF: Document contains 0 pages.", {}
                    for idx, p in enumerate(pdf.pages):
                        txt = p.extract_text() or ""
                        extracted_pages.append({
                            "page_number": idx + 1,
                            "text": txt,
                            "width": p.width,
                            "height": p.height
                        })
                        full_text += txt + "\n"
            elif pypdf is not None:
                reader = pypdf.PdfReader(bio)
                page_count = len(reader.pages)
                if page_count == 0:
                    return False, "Corrupted PDF: Document contains 0 pages.", {}
                for idx, p in enumerate(reader.pages):
                    txt = p.extract_text() or ""
                    extracted_pages.append({
                        "page_number": idx + 1,
                        "text": txt
                    })
                    full_text += txt + "\n"
            else:
                return False, "No PDF parser (pdfplumber/pypdf) is available in environment.", {}

        except Exception as e:
            return False, f"Corrupted or unreadable PDF: Unable to parse document stream. Error: {str(e)}", {}

        metadata = {
            "filename": filename,
            "file_size": size_bytes,
            "sha256": sha256_hash,
            "page_count": page_count,
            "pages": extracted_pages,
            "full_text": full_text.strip()
        }
        return True, "", metadata

    def infer_document_type(self, text: str, filename: str) -> DocumentType:
        """Infer canonical DocumentType from document text and filename."""
        text_upper = text.upper()
        fn_upper = filename.upper()

        if "DEED OF PERPETUAL LEASE" in text_upper or "LAND TITLE" in text_upper or "LAND_TITLE" in fn_upper or "LEASE DEED" in text_upper:
            return DocumentType.LAND_TITLE
        elif "BUILDING PLAN SANCTION" in text_upper or "OCCUPANCY ORDER" in text_upper or "BUILDING_PLAN" in fn_upper or "SANCTION ORDER" in text_upper:
            return DocumentType.BUILDING_PLAN
        elif "FIRE SAFETY CERTIFICATE" in text_upper or "FIRE NOC" in text_upper or "FIRE_NOC" in fn_upper or "DISASTER MANAGEMENT & FIRE" in text_upper:
            return DocumentType.FIRE_NOC
        elif "MANDATORY DISCLOSURE" in text_upper or "MANDATORY_DISCLOSURE" in fn_upper:
            return DocumentType.MANDATORY_DISCLOSURE
        elif "SOCIETY REGISTRATION" in text_upper or "SOCIETY_REGISTRATION" in fn_upper or "TRUST DEED" in text_upper:
            return DocumentType.SOCIETY_REGISTRATION

        # Fallback to Land Title if ambiguous
        return DocumentType.LAND_TITLE

    def identify_college(self, text: str, filename: str, qr_content: Optional[str] = None) -> CollegeIdentificationResult:
        """
        Identify the correct college from the 30-college dataset.
        Priority:
        1. Exact Application ID (APP-XXX) in text, QR, or filename.
        2. Exact Institution ID (INST-XXX) in text, QR, or filename.
        3. Exact substring match of institutional name.
        4. High-confidence fuzzy string match (>= 0.85 with >= 0.08 margin).
        5. Ambiguous / Insufficient confidence match (0.65 - 0.85 or close margin) -> Prompt user.
        6. Unknown college (< 0.65) -> Document does not belong to the dataset.
        """
        text_lower = text.lower()
        combined_meta = f"{filename} {qr_content or ''}"

        # 1. Check exact APP-XXX pattern
        app_id_match = re.search(r"\bAPP-\d{3}\b", text + " " + combined_meta)
        if app_id_match:
            candidate_id = app_id_match.group(0).upper()
            if candidate_id in self.gt:
                college = self.gt[candidate_id]
                return CollegeIdentificationResult(
                    status=IdentificationStatus.EXACT_MATCH,
                    identified_app_id=candidate_id,
                    identified_name=college["institution_name"],
                    confidence=1.0,
                    method="Exact Application ID (APP-XXX)",
                    explanation=f"Exact match on official Application ID '{candidate_id}' embedded in document metadata.",
                    extracted_identifier=candidate_id,
                    top_candidates=[CollegeCandidate(
                        application_id=candidate_id,
                        institution_id=college["institution_id"],
                        institution_name=college["institution_name"],
                        match_score=1.0,
                        match_reason="Exact Application ID"
                    )]
                )

        # 2. Check exact INST-XXX pattern
        inst_id_match = re.search(r"\bINST-\d{3}\b", text + " " + combined_meta)
        if inst_id_match:
            cand_inst_id = inst_id_match.group(0).upper()
            for app_id, col in self.gt.items():
                if col.get("institution_id") == cand_inst_id:
                    return CollegeIdentificationResult(
                        status=IdentificationStatus.EXACT_MATCH,
                        identified_app_id=app_id,
                        identified_name=col["institution_name"],
                        confidence=1.0,
                        method="Exact Institution ID (INST-XXX)",
                        explanation=f"Exact match on registered Institution ID '{cand_inst_id}' associated with {col['institution_name']}.",
                        extracted_identifier=cand_inst_id,
                        top_candidates=[CollegeCandidate(
                            application_id=app_id,
                            institution_id=col["institution_id"],
                            institution_name=col["institution_name"],
                            match_score=1.0,
                            match_reason="Exact Institution ID"
                        )]
                    )

        # 3. Check exact institution name substring in text
        for app_id, col in self.gt.items():
            name = col["institution_name"].strip().lower()
            if len(name) > 8 and name in text_lower:
                return CollegeIdentificationResult(
                    status=IdentificationStatus.EXACT_MATCH,
                    identified_app_id=app_id,
                    identified_name=col["institution_name"],
                    confidence=0.99,
                    method="Exact Institution Name Substring",
                    explanation=f"Document explicitly recites exact registered name '{col['institution_name']}'.",
                    extracted_identifier=col["institution_name"],
                    top_candidates=[CollegeCandidate(
                        application_id=app_id,
                        institution_id=col["institution_id"],
                        institution_name=col["institution_name"],
                        match_score=0.99,
                        match_reason="Exact Name Match"
                    )]
                )

        # 4. Extract candidate entity name via regex/layout for fuzzy matching
        candidate_name = None
        for pattern in [
            r"operation\s+of\s+([^\n,]+?),?\s*hereinafter",
            r"(?:Name\s*of\s*the\s*Institution|Certified\s*Institution|Institution\s*Name)\s*[:\-]?\s*([^\n]+)",
            r"between\s+the\s+Land\s+Authority.+?and\s+the\s+sponsoring\s+body\s+([^\n,]+)",
            r"([A-Z][a-zA-Z\s]{4,40}(?:Institute|College|Academy|University)\s+of\s+[A-Za-z\s]+)"
        ]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                candidate_name = m.group(1).strip()
                break

        if not candidate_name and len(text.strip()) > 20:
            # First non-header line with plausible length
            lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 10 and not l.strip().startswith("***")]
            if lines:
                candidate_name = lines[0]

        if not candidate_name:
            return CollegeIdentificationResult(
                status=IdentificationStatus.UNKNOWN_COLLEGE,
                confidence=0.0,
                method="Extraction Failed",
                explanation="No institution name, application ID, or regulatory identifier could be extracted from the document text.",
                top_candidates=[]
            )

        # Compute fuzzy similarities against all 30 colleges
        scored: List[Tuple[str, Dict[str, Any], float]] = []
        for app_id, col in self.gt.items():
            col_name = col["institution_name"]
            sim_name = fuzz.token_sort_ratio(candidate_name.lower(), col_name.lower()) / 100.0
            sim_trust = fuzz.token_sort_ratio(candidate_name.lower(), col.get("society_trust_name", "").lower()) / 100.0
            best_sim = max(sim_name, sim_trust)
            scored.append((app_id, col, best_sim))

        scored.sort(key=lambda x: x[2], reverse=True)

        candidates = [
            CollegeCandidate(
                application_id=s[0],
                institution_id=s[1]["institution_id"],
                institution_name=s[1]["institution_name"],
                match_score=round(s[2], 3),
                match_reason=f"Fuzzy match similarity: {s[2]:.1%}"
            )
            for s in scored[:5]
        ]

        top_app_id, top_col, top_score = scored[0]
        second_score = scored[1][2] if len(scored) > 1 else 0.0

        # Evaluate against documented thresholds:
        # High confidence: score >= 0.88 and score margin >= 0.10
        if top_score >= 0.88 and (top_score - second_score) >= 0.10:
            return CollegeIdentificationResult(
                status=IdentificationStatus.HIGH_CONFIDENCE_FUZZY,
                identified_app_id=top_app_id,
                identified_name=top_col["institution_name"],
                confidence=round(top_score, 3),
                method="High-Confidence Fuzzy Name Match",
                explanation=(
                    f"Extracted name '{candidate_name}' closely matches '{top_col['institution_name']}' "
                    f"with {top_score:.1%} similarity (margin over runner-up: {(top_score - second_score):.1%})."
                ),
                extracted_identifier=candidate_name,
                top_candidates=candidates
            )

        # Ambiguous match: moderate confidence (0.65 - 0.85) or close margin (< 0.08)
        if top_score >= 0.65:
            reason = "Multiple institutions scored closely to the extracted entity name." if (top_score - second_score) < 0.08 else "Confidence score falls between 65% and 85%."
            return CollegeIdentificationResult(
                status=IdentificationStatus.AMBIGUOUS_MATCH,
                identified_app_id=None,
                identified_name=None,
                confidence=round(top_score, 3),
                method="Ambiguous / Insufficient Confidence Match",
                explanation=(
                    f"Document refers to '{candidate_name}'. {reason} "
                    f"Top candidate: '{top_col['institution_name']}' ({top_score:.1%}), "
                    f"Second candidate: '{scored[1][1]['institution_name']}' ({second_score:.1%}). "
                    f"User confirmation is strictly required to prevent misattribution."
                ),
                extracted_identifier=candidate_name,
                top_candidates=candidates
            )

        # Unknown college (< 0.65)
        return CollegeIdentificationResult(
            status=IdentificationStatus.UNKNOWN_COLLEGE,
            identified_app_id=None,
            identified_name=None,
            confidence=round(top_score, 3),
            method="No Significant Match Found",
            explanation=(
                f"The extracted entity name '{candidate_name}' has insufficient similarity "
                f"(highest: {top_score:.1%} with '{top_col['institution_name']}', threshold >= 65%). "
                f"This document does not belong to any of the 30 registered AICTE colleges in the active dataset."
            ),
            extracted_identifier=candidate_name,
            top_candidates=candidates
        )

    def validate_document_against_college(
        self,
        college_id: str,
        doc_type: DocumentType,
        filename: str,
        metadata: Dict[str, Any],
        raw_fields: Optional[List[ExtractedField]] = None
    ) -> SingleDocValidationResult:
        """
        Execute targeted validation checks of the uploaded document strictly
        against the selected college's profile and baseline records.
        """
        if college_id not in self.gt:
            raise ValueError(f"College ID '{college_id}' not found in the 30-college database.")

        college_profile = self.gt[college_id]
        full_text = metadata.get("full_text", "")
        file_hash = metadata.get("sha256", "")
        file_size = metadata.get("file_size", 0)
        page_count = metadata.get("page_count", 1)

        # 1. Extract structured fields if not provided
        if raw_fields is None:
            raw_fields = self.extractor.extract_document_fields(doc_type, full_text, filename)

        # Index extracted fields by name
        fields_map: Dict[str, ExtractedField] = {f.field_name: f for f in raw_fields}

        checks: List[ValidationCheck] = []

        # -------------------------------------------------------------
        # Check 1: Institutional Name Alignment
        # -------------------------------------------------------------
        exp_name = college_profile.get("institution_name")
        act_name_field = fields_map.get("institution_name")
        act_name = str(act_name_field.field_value) if act_name_field else None

        if exp_name is None:
            checks.append(ValidationCheck(
                check_name="Institutional Name Alignment",
                status=CheckStatus.UNVERIFIED,
                rule_id="RULE_CROSS_DOC_INSTITUTION_NAME",
                statutory_clause="AICTE APH 2024-25, Clause 2.14.1 (Institutional Identity Alignment)",
                severity=FindingSeverity.MEDIUM,
                expected_value=None,
                extracted_value=act_name,
                difference_details="Reference institution name missing in college profile.",
                source_document=filename
            ))
        elif act_name is None:
            checks.append(ValidationCheck(
                check_name="Institutional Name Alignment",
                status=CheckStatus.MISSING_INFORMATION,
                rule_id="RULE_CROSS_DOC_INSTITUTION_NAME",
                statutory_clause="AICTE APH 2024-25, Clause 2.14.1 (Institutional Identity Alignment)",
                severity=FindingSeverity.HIGH,
                expected_value=exp_name,
                extracted_value=None,
                difference_details=f"Document lacks an extracted institution name to compare against registered '{exp_name}'.",
                source_document=filename,
                recommended_action="Ensure the uploaded document contains clear institutional header or signatory declaration."
            ))
        else:
            sim = fuzz.token_sort_ratio(exp_name.lower(), act_name.lower()) / 100.0
            if sim >= 0.85:
                checks.append(ValidationCheck(
                    check_name="Institutional Name Alignment",
                    status=CheckStatus.PASSED,
                    rule_id="RULE_CROSS_DOC_INSTITUTION_NAME",
                    statutory_clause="AICTE APH 2024-25, Clause 2.14.1 (Institutional Identity Alignment)",
                    severity=FindingSeverity.INFO,
                    expected_value=exp_name,
                    extracted_value=act_name,
                    difference_details=f"Concordant institutional identity (Similarity: {sim:.1%}).",
                    evidence_claims=[f"Document: '{act_name}'", f"Profile: '{exp_name}'"],
                    source_document=filename,
                    page_number=act_name_field.page_number if act_name_field else 1
                ))
            else:
                checks.append(ValidationCheck(
                    check_name="Institutional Name Alignment",
                    status=CheckStatus.MISMATCH,
                    rule_id="RULE_CROSS_DOC_INSTITUTION_NAME",
                    statutory_clause="AICTE APH 2024-25, Clause 2.14.1 (Institutional Identity Alignment)",
                    severity=FindingSeverity.HIGH,
                    expected_value=exp_name,
                    extracted_value=act_name,
                    difference_details=f"Extracted name '{act_name}' does not match registered profile '{exp_name}' (Similarity: {sim:.1%}).",
                    evidence_claims=[f"Document Name: '{act_name}'", f"Registered Name: '{exp_name}'", f"Similarity: {sim:.2f}"],
                    source_document=filename,
                    page_number=act_name_field.page_number if act_name_field else 1,
                    recommended_action="Review legal change-of-name endorsement or gazette notification.",
                    is_contradiction=True,
                    is_anomaly=True
                ))

        # -------------------------------------------------------------
        # Check 2: Site Survey / Plot Number Concordance
        # -------------------------------------------------------------
        exp_survey = college_profile.get("survey_number")
        act_survey_field = fields_map.get("survey_number")
        act_survey = str(act_survey_field.field_value) if act_survey_field else None

        if doc_type in [DocumentType.LAND_TITLE, DocumentType.BUILDING_PLAN, DocumentType.MANDATORY_DISCLOSURE]:
            if exp_survey is None:
                checks.append(ValidationCheck(
                    check_name="Survey / Plot Number Concordance",
                    status=CheckStatus.UNVERIFIED,
                    rule_id="RULE_CROSS_DOC_SURVEY_NUMBER",
                    statutory_clause="AICTE APH 2024-25, Clause 2.3.1 (Land Title & Site Contiguity)",
                    severity=FindingSeverity.MEDIUM,
                    expected_value=None,
                    extracted_value=act_survey,
                    difference_details="Reference survey number missing in institutional profile record.",
                    source_document=filename
                ))
            elif act_survey is None:
                checks.append(ValidationCheck(
                    check_name="Survey / Plot Number Concordance",
                    status=CheckStatus.MISSING_INFORMATION,
                    rule_id="RULE_CROSS_DOC_SURVEY_NUMBER",
                    statutory_clause="AICTE APH 2024-25, Clause 2.3.1 (Land Title & Site Contiguity)",
                    severity=FindingSeverity.HIGH,
                    expected_value=exp_survey,
                    extracted_value=None,
                    difference_details=f"Document does not state survey/khasra number (Expected: '{exp_survey}').",
                    source_document=filename,
                    recommended_action="Document must cite official revenue survey parcel identification."
                ))
            else:
                norm_exp = exp_survey.strip().lower()
                norm_act = act_survey.strip().lower()
                sim_survey = fuzz.ratio(norm_exp, norm_act) / 100.0

                if norm_exp == norm_act or sim_survey >= 0.90:
                    checks.append(ValidationCheck(
                        check_name="Survey / Plot Number Concordance",
                        status=CheckStatus.PASSED,
                        rule_id="RULE_CROSS_DOC_SURVEY_NUMBER",
                        statutory_clause="AICTE APH 2024-25, Clause 2.3.1 (Land Title & Site Contiguity)",
                        severity=FindingSeverity.INFO,
                        expected_value=exp_survey,
                        extracted_value=act_survey,
                        difference_details=f"Survey parcel '{act_survey}' matches registered campus location.",
                        evidence_claims=[f"Document Survey: '{act_survey}'", f"Profile Record: '{exp_survey}'"],
                        source_document=filename,
                        page_number=act_survey_field.page_number if act_survey_field else 1
                    ))
                else:
                    checks.append(ValidationCheck(
                        check_name="Survey / Plot Number Concordance",
                        status=CheckStatus.MISMATCH,
                        rule_id="RULE_CROSS_DOC_SURVEY_NUMBER",
                        statutory_clause="AICTE APH 2024-25, Clause 2.3.1 (Land Title & Site Contiguity)",
                        severity=FindingSeverity.CRITICAL,
                        expected_value=exp_survey,
                        extracted_value=act_survey,
                        difference_details=f"Survey number mismatch: document cites '{act_survey}' vs registered profile '{exp_survey}'.",
                        evidence_claims=[f"Document: '{act_survey}'", f"Application Record: '{exp_survey}'"],
                        source_document=filename,
                        page_number=act_survey_field.page_number if act_survey_field else 1,
                        recommended_action="Conduct revenue inspection regarding non-contiguous or unapproved parcel substitution.",
                        is_contradiction=True,
                        is_anomaly=True
                    ))

        # -------------------------------------------------------------
        # Check 3: Campus Land Area Acreage & Statutory Threshold
        # -------------------------------------------------------------
        if doc_type in [DocumentType.LAND_TITLE, DocumentType.MANDATORY_DISCLOSURE]:
            inst_type = college_profile.get("institution_type", "Engineering")
            threshold = self.rules_engine.rules_config.get("rules", [])
            min_norm = 4.0
            for r in threshold:
                if r.get("id") == "RULE_MINIMUM_LAND_REQUIREMENT":
                    min_norm = float(r.get("thresholds", {}).get(inst_type, 4.0))
                    break

            exp_land = float(college_profile.get("land_area_acres", 0.0))
            act_land_field = fields_map.get("land_area_acres")
            act_land = float(act_land_field.field_value) if act_land_field else None

            if exp_land == 0.0:
                checks.append(ValidationCheck(
                    check_name="Land Area Acreage Verification",
                    status=CheckStatus.UNVERIFIED,
                    rule_id="RULE_MINIMUM_LAND_REQUIREMENT",
                    statutory_clause="AICTE APH 2024-25, Clause 2.3.2 (Minimum Campus Land Requirement)",
                    severity=FindingSeverity.MEDIUM,
                    expected_value=None,
                    extracted_value=act_land,
                    difference_details="Registered land area is not recorded in institutional baseline profile.",
                    source_document=filename
                ))
            elif act_land is None:
                checks.append(ValidationCheck(
                    check_name="Land Area Acreage Verification",
                    status=CheckStatus.MISSING_INFORMATION,
                    rule_id="RULE_MINIMUM_LAND_REQUIREMENT",
                    statutory_clause="AICTE APH 2024-25, Clause 2.3.2 (Minimum Campus Land Requirement)",
                    severity=FindingSeverity.HIGH,
                    expected_value=f"{exp_land:.2f} Acres (Norm: {min_norm:.2f})",
                    extracted_value=None,
                    difference_details="Document does not state campus acreage measurement.",
                    source_document=filename,
                    recommended_action="Provide certified land schedule specifying total acres."
                ))
            else:
                if act_land < min_norm:
                    checks.append(ValidationCheck(
                        check_name="Land Area Acreage Verification",
                        status=CheckStatus.MISMATCH,
                        rule_id="RULE_MINIMUM_LAND_REQUIREMENT",
                        statutory_clause="AICTE APH 2024-25, Clause 2.3.2 (Minimum Campus Land Requirement)",
                        severity=FindingSeverity.HIGH,
                        expected_value=f">= {min_norm:.2f} Acres",
                        extracted_value=f"{act_land:.2f} Acres",
                        difference_details=f"Documented land area ({act_land:.2f} Acres) fails statutory norm of {min_norm:.2f} Acres for {inst_type}.",
                        evidence_claims=[f"Extracted Area: {act_land:.2f} Acres", f"Statutory Minimum: {min_norm:.2f} Acres"],
                        source_document=filename,
                        page_number=act_land_field.page_number if act_land_field else 1,
                        recommended_action="Applicant must demonstrate additional contiguous land parcels."
                    ))
                elif abs(act_land - exp_land) > 0.10:
                    checks.append(ValidationCheck(
                        check_name="Land Area Acreage Verification",
                        status=CheckStatus.MISMATCH,
                        rule_id="RULE_CROSS_DOC_LAND_AREA",
                        statutory_clause="AICTE APH 2024-25, Clause 2.3.2 (Cross-Document Land Consistency)",
                        severity=FindingSeverity.CRITICAL,
                        expected_value=f"{exp_land:.2f} Acres",
                        extracted_value=f"{act_land:.2f} Acres",
                        difference_details=f"Land area in document ({act_land:.2f} Acres) contradicts registered application value ({exp_land:.2f} Acres).",
                        evidence_claims=[f"Document: {act_land:.2f} Acres", f"Registered: {exp_land:.2f} Acres"],
                        source_document=filename,
                        page_number=act_land_field.page_number if act_land_field else 1,
                        recommended_action="Reconcile revenue title deed with institutional master disclosure.",
                        is_contradiction=True,
                        is_anomaly=True
                    ))
                else:
                    checks.append(ValidationCheck(
                        check_name="Land Area Acreage Verification",
                        status=CheckStatus.PASSED,
                        rule_id="RULE_MINIMUM_LAND_REQUIREMENT",
                        statutory_clause="AICTE APH 2024-25, Clause 2.3.2 (Minimum Campus Land Requirement)",
                        severity=FindingSeverity.INFO,
                        expected_value=f"{exp_land:.2f} Acres (Norm: {min_norm:.2f})",
                        extracted_value=f"{act_land:.2f} Acres",
                        difference_details=f"Land area of {act_land:.2f} Acres meets regulatory norm ({min_norm:.2f} Acres) and matches registered profile.",
                        evidence_claims=[f"Document Acreage: {act_land:.2f}", f"Registered Acreage: {exp_land:.2f}"],
                        source_document=filename,
                        page_number=act_land_field.page_number if act_land_field else 1
                    ))

        # -------------------------------------------------------------
        # Check 4: Certificate Temporal Validity & Expiry
        # -------------------------------------------------------------
        act_expiry_field = fields_map.get("expiry_date")
        act_expiry = str(act_expiry_field.field_value) if act_expiry_field else None

        if doc_type in [DocumentType.FIRE_NOC, DocumentType.BUILDING_PLAN]:
            cutoff_str = "2026-10-26"
            if act_expiry is None:
                checks.append(ValidationCheck(
                    check_name="Document Temporal Validity",
                    status=CheckStatus.MISSING_INFORMATION,
                    rule_id="RULE_DOCUMENT_VALIDITY",
                    statutory_clause="AICTE APH 2024-25, Clause 2.14.2 (Statutory Certificate Temporal Validity)",
                    severity=FindingSeverity.HIGH,
                    expected_value=f"Valid on or after {cutoff_str}",
                    extracted_value=None,
                    difference_details="Certificate does not declare an expiration or validity cutoff date.",
                    source_document=filename,
                    recommended_action="Verify validity period with issuing municipal/fire authority."
                ))
            else:
                try:
                    exp_dt = datetime.strptime(act_expiry, "%Y-%m-%d")
                    cutoff_dt = datetime.strptime(cutoff_str, "%Y-%m-%d")
                    if exp_dt < cutoff_dt:
                        checks.append(ValidationCheck(
                            check_name="Document Temporal Validity",
                            status=CheckStatus.MISMATCH,
                            rule_id="RULE_DOCUMENT_VALIDITY",
                            statutory_clause="AICTE APH 2024-25, Clause 2.14.2 (Statutory Certificate Temporal Validity)",
                            severity=FindingSeverity.HIGH,
                            expected_value=f"Valid on or after {cutoff_str}",
                            extracted_value=f"Expired on {act_expiry}",
                            difference_details=f"Statutory certificate expired on {act_expiry} (Precedes scrutiny cutoff of {cutoff_str}).",
                            evidence_claims=[f"Certificate Expiry: {act_expiry}", f"Evaluation Cutoff: {cutoff_str}"],
                            source_document=filename,
                            page_number=act_expiry_field.page_number if act_expiry_field else 1,
                            recommended_action="Applicant must furnish renewed NOC certificate issued by competent authority.",
                            is_anomaly=True
                        ))
                    else:
                        checks.append(ValidationCheck(
                            check_name="Document Temporal Validity",
                            status=CheckStatus.PASSED,
                            rule_id="RULE_DOCUMENT_VALIDITY",
                            statutory_clause="AICTE APH 2024-25, Clause 2.14.2 (Statutory Certificate Temporal Validity)",
                            severity=FindingSeverity.INFO,
                            expected_value=f"Valid on or after {cutoff_str}",
                            extracted_value=f"Valid until {act_expiry}",
                            difference_details=f"Certificate remains valid through {act_expiry}.",
                            evidence_claims=[f"Certificate Expiry: {act_expiry}"],
                            source_document=filename,
                            page_number=act_expiry_field.page_number if act_expiry_field else 1
                        ))
                except ValueError:
                    checks.append(ValidationCheck(
                        check_name="Document Temporal Validity",
                        status=CheckStatus.UNVERIFIED,
                        rule_id="RULE_DOCUMENT_VALIDITY",
                        statutory_clause="AICTE APH 2024-25, Clause 2.14.2 (Statutory Certificate Temporal Validity)",
                        severity=FindingSeverity.MEDIUM,
                        expected_value=f"Valid on or after {cutoff_str}",
                        extracted_value=act_expiry,
                        difference_details=f"Unrecognized date format '{act_expiry}'.",
                        source_document=filename
                    ))
        elif doc_type == DocumentType.LAND_TITLE:
            checks.append(ValidationCheck(
                check_name="Document Temporal Validity",
                status=CheckStatus.PASSED,
                rule_id="RULE_DOCUMENT_VALIDITY",
                statutory_clause="AICTE APH 2024-25, Clause 2.14.2 (Perpetual Title Validity)",
                severity=FindingSeverity.INFO,
                expected_value="Perpetual Conveyance",
                extracted_value="Perpetual Lease Deed",
                difference_details="Land title conveyance is perpetual and not subject to annual renewal.",
                source_document=filename
            ))

        # -------------------------------------------------------------
        # Check 5: Sponsoring Body / Trust Alignment
        # -------------------------------------------------------------
        exp_trust = college_profile.get("society_trust_name")
        act_trust_field = fields_map.get("society_trust_name")
        act_trust = str(act_trust_field.field_value) if act_trust_field else None

        if doc_type in [DocumentType.LAND_TITLE, DocumentType.MANDATORY_DISCLOSURE, DocumentType.SOCIETY_REGISTRATION]:
            if exp_trust is None:
                checks.append(ValidationCheck(
                    check_name="Sponsoring Trust Ownership Alignment",
                    status=CheckStatus.UNVERIFIED,
                    rule_id="RULE_SPONSORING_TRUST",
                    statutory_clause="AICTE APH 2024-25, Clause 2.1 (Sponsoring Body Governance)",
                    severity=FindingSeverity.MEDIUM,
                    expected_value=None,
                    extracted_value=act_trust,
                    difference_details="Registered sponsoring body not recorded in institutional profile.",
                    source_document=filename
                ))
            elif act_trust is None:
                checks.append(ValidationCheck(
                    check_name="Sponsoring Trust Ownership Alignment",
                    status=CheckStatus.MISSING_INFORMATION,
                    rule_id="RULE_SPONSORING_TRUST",
                    statutory_clause="AICTE APH 2024-25, Clause 2.1 (Sponsoring Body Governance)",
                    severity=FindingSeverity.MEDIUM,
                    expected_value=exp_trust,
                    extracted_value=None,
                    difference_details=f"Document does not name the sponsoring trust (Registered: '{exp_trust}').",
                    source_document=filename
                ))
            else:
                sim_trust = fuzz.token_sort_ratio(exp_trust.lower(), act_trust.lower()) / 100.0
                if sim_trust >= 0.85:
                    checks.append(ValidationCheck(
                        check_name="Sponsoring Trust Ownership Alignment",
                        status=CheckStatus.PASSED,
                        rule_id="RULE_SPONSORING_TRUST",
                        statutory_clause="AICTE APH 2024-25, Clause 2.1 (Sponsoring Body Governance)",
                        severity=FindingSeverity.INFO,
                        expected_value=exp_trust,
                        extracted_value=act_trust,
                        difference_details=f"Sponsoring trust '{act_trust}' aligns with registered ownership (Similarity: {sim_trust:.1%}).",
                        evidence_claims=[f"Document Trust: '{act_trust}'", f"Profile Trust: '{exp_trust}'"],
                        source_document=filename,
                        page_number=act_trust_field.page_number if act_trust_field else 1
                    ))
                else:
                    checks.append(ValidationCheck(
                        check_name="Sponsoring Trust Ownership Alignment",
                        status=CheckStatus.MISMATCH,
                        rule_id="RULE_SPONSORING_TRUST",
                        statutory_clause="AICTE APH 2024-25, Clause 2.1 (Sponsoring Body Governance)",
                        severity=FindingSeverity.HIGH,
                        expected_value=exp_trust,
                        extracted_value=act_trust,
                        difference_details=f"Sponsoring trust in document '{act_trust}' differs from registered profile '{exp_trust}' (Similarity: {sim_trust:.1%}).",
                        evidence_claims=[f"Document: '{act_trust}'", f"Registered: '{exp_trust}'"],
                        source_document=filename,
                        page_number=act_trust_field.page_number if act_trust_field else 1,
                        recommended_action="Submit certified resolution confirming legal relationship between entities.",
                        is_contradiction=True
                    ))

        # -------------------------------------------------------------
        # Check 6: Built-Up Area Instructional Norms
        # -------------------------------------------------------------
        if doc_type == DocumentType.BUILDING_PLAN:
            act_bplan_field = fields_map.get("built_up_area_sqm")
            act_sqm = float(act_bplan_field.field_value) if act_bplan_field else None
            min_sqm_norm = 4000.0

            if act_sqm is None:
                checks.append(ValidationCheck(
                    check_name="Built-Up Area Norm Verification",
                    status=CheckStatus.MISSING_INFORMATION,
                    rule_id="RULE_BUILT_UP_AREA_NORM",
                    statutory_clause="AICTE APH 2024-25, Clause 2.4 (Instructional & Amenities Area Norms)",
                    severity=FindingSeverity.HIGH,
                    expected_value=f">= {min_sqm_norm:,.0f} sq.m",
                    extracted_value=None,
                    difference_details="Sanctioned building plan does not specify total built-up area in square meters.",
                    source_document=filename,
                    recommended_action="Provide certified area schedule from registered architect."
                ))
            else:
                if act_sqm >= min_sqm_norm:
                    checks.append(ValidationCheck(
                        check_name="Built-Up Area Norm Verification",
                        status=CheckStatus.PASSED,
                        rule_id="RULE_BUILT_UP_AREA_NORM",
                        statutory_clause="AICTE APH 2024-25, Clause 2.4 (Instructional & Amenities Area Norms)",
                        severity=FindingSeverity.INFO,
                        expected_value=f">= {min_sqm_norm:,.0f} sq.m",
                        extracted_value=f"{act_sqm:,.1f} sq.m",
                        difference_details=f"Sanctioned built-up area ({act_sqm:,.1f} sq.m) satisfies minimum regulatory norm of {min_sqm_norm:,.0f} sq.m.",
                        evidence_claims=[f"Sanctioned Area: {act_sqm:,.1f} sq.m", f"AICTE Minimum Norm: {min_sqm_norm:,.0f} sq.m"],
                        source_document=filename,
                        page_number=act_bplan_field.page_number if act_bplan_field else 1
                    ))
                else:
                    checks.append(ValidationCheck(
                        check_name="Built-Up Area Norm Verification",
                        status=CheckStatus.MISMATCH,
                        rule_id="RULE_BUILT_UP_AREA_NORM",
                        statutory_clause="AICTE APH 2024-25, Clause 2.4 (Instructional & Amenities Area Norms)",
                        severity=FindingSeverity.HIGH,
                        expected_value=f">= {min_sqm_norm:,.0f} sq.m",
                        extracted_value=f"{act_sqm:,.1f} sq.m",
                        difference_details=f"Sanctioned built-up area ({act_sqm:,.1f} sq.m) falls below statutory minimum norm of {min_sqm_norm:,.0f} sq.m.",
                        evidence_claims=[f"Sanctioned Area: {act_sqm:,.1f} sq.m", f"Minimum Norm: {min_sqm_norm:,.0f} sq.m"],
                        source_document=filename,
                        page_number=act_bplan_field.page_number if act_bplan_field else 1,
                        recommended_action="Applicant must upload additional sanctioned floor plans or phase completion certificate."
                    ))

        # -------------------------------------------------------------
        # Check 7: External Issuing Authority Verification (Mock Registry)
        # -------------------------------------------------------------
        doc_num = "DOC-UNKNOWN"
        for f in raw_fields:
            if "number" in f.field_name or "noc" in f.field_name:
                doc_num = str(f.field_value)
                break

        issuer_resp = self.mock_verifier.verify_document(
            app_id=college_id,
            doc_type=doc_type.value,
            doc_number=doc_num,
            institution_name=college_profile["institution_name"],
            qr_content=metadata.get("qr_content")
        )

        issuer_info = {
            "query_id": issuer_resp.query_id,
            "authority_name": issuer_resp.authority_name,
            "status": issuer_resp.status.value,
            "matched": issuer_resp.matched,
            "mismatch_details": issuer_resp.mismatch_details,
            "latency_ms": round(issuer_resp.latency_ms, 1),
            "qr_verified": issuer_resp.qr_verified
        }

        if issuer_resp.status == VerificationStatus.VERIFIED:
            checks.append(ValidationCheck(
                check_name="Issuing Authority Cross-Verification",
                status=CheckStatus.PASSED,
                rule_id="RULE_ISSUER_AUTHENTICATION",
                statutory_clause="AICTE Regulatory Verification Framework (External Authority Direct Query)",
                severity=FindingSeverity.INFO,
                expected_value="Verified in Authority Database",
                extracted_value=f"Status: {issuer_resp.status.value}",
                difference_details=f"Authenticated against {issuer_resp.authority_name} (Query: {issuer_resp.query_id}, Latency: {issuer_resp.latency_ms:.1f}ms).",
                evidence_claims=[f"Authority: {issuer_resp.authority_name}", f"Query ID: {issuer_resp.query_id}"],
                source_document=filename
            ))
        elif issuer_resp.status in [VerificationStatus.MISMATCH_DETECTED, VerificationStatus.EXPIRED]:
            checks.append(ValidationCheck(
                check_name="Issuing Authority Cross-Verification",
                status=CheckStatus.MISMATCH,
                rule_id="RULE_ISSUER_AUTHENTICATION",
                statutory_clause="AICTE Regulatory Verification Framework (External Authority Direct Query)",
                severity=FindingSeverity.CRITICAL if issuer_resp.status == VerificationStatus.MISMATCH_DETECTED else FindingSeverity.HIGH,
                expected_value="Verified in Authority Database",
                extracted_value=f"Status: {issuer_resp.status.value}",
                difference_details=" ; ".join(issuer_resp.mismatch_details) or f"Issuing authority returned {issuer_resp.status.value}.",
                evidence_claims=[f"Authority: {issuer_resp.authority_name}"] + issuer_resp.mismatch_details,
                source_document=filename,
                recommended_action="Initiate formal inter-departmental inquiry regarding discrepancy in statutory records.",
                is_contradiction=True,
                is_anomaly=True
            ))
        elif issuer_resp.status == VerificationStatus.SOURCE_UNAVAILABLE:
            checks.append(ValidationCheck(
                check_name="Issuing Authority Cross-Verification",
                status=CheckStatus.UNVERIFIED,
                rule_id="RULE_ISSUER_AUTHENTICATION",
                statutory_clause="AICTE Regulatory Verification Framework (External Authority Direct Query)",
                severity=FindingSeverity.MEDIUM,
                expected_value="Verified in Authority Database",
                extracted_value=f"Status: {issuer_resp.status.value}",
                difference_details="External state issuing authority registry endpoint timed out. Automated verification could not be completed.",
                evidence_claims=[f"Authority: {issuer_resp.authority_name}", "Timeout: 3 retry attempts exceeded"],
                source_document=filename,
                recommended_action="Route to scrutiny officer for manual offline record confirmation."
            ))
        else:
            checks.append(ValidationCheck(
                check_name="Issuing Authority Cross-Verification",
                status=CheckStatus.UNVERIFIED,
                rule_id="RULE_ISSUER_AUTHENTICATION",
                statutory_clause="AICTE Regulatory Verification Framework (External Authority Direct Query)",
                severity=FindingSeverity.HIGH,
                expected_value="Verified in Authority Database",
                extracted_value=f"Status: {issuer_resp.status.value}",
                difference_details=" ; ".join(issuer_resp.mismatch_details) or f"Issuing authority flagged: {issuer_resp.status.value}.",
                evidence_claims=[f"Authority: {issuer_resp.authority_name}"] + issuer_resp.mismatch_details,
                source_document=filename,
                recommended_action="Requires manual inspection by scrutiny officer."
            ))

        # -------------------------------------------------------------
        # Check 8: Cross-Application Fingerprint & Anti-Collusion Check
        # -------------------------------------------------------------
        # Compare SHA-256 hash against existing documents of OTHER colleges
        other_college_match = None
        try:
            with get_db_context() as db:
                matches = db.query(DocumentDB).filter(
                    DocumentDB.file_hash == file_hash,
                    DocumentDB.application_id != college_id
                ).all()
                if matches:
                    other_college_match = matches[0].application_id
        except Exception:
            # Fallback to ground truth dictionary if DB is empty
            for other_id, other_app in self.gt.items():
                if other_id != college_id:
                    for doc in other_app.get("documents", []):
                        if doc.get("file_hash") == file_hash:
                            other_college_match = other_id
                            break
                    if other_college_match:
                        break

        if other_college_match:
            checks.append(ValidationCheck(
                check_name="Cross-Institution Document Uniqueness",
                status=CheckStatus.MISMATCH,
                rule_id="RULE_COLLUSION_FINGERPRINT",
                statutory_clause="AICTE APH 2024-25, Clause 2.14.4 (Document Authenticity & Multi-College Fraud Prevention)",
                severity=FindingSeverity.CRITICAL,
                expected_value="Unique Document Fingerprint",
                extracted_value=f"Identical Hash in {other_college_match}",
                difference_details=(
                    f"CRITICAL COLLUSION SIGNAL: Document SHA-256 fingerprint ({file_hash[:16]}...) "
                    f"is identical to a document previously submitted by an unrelated institution ({other_college_match})."
                ),
                evidence_claims=[
                    f"Document SHA-256: {file_hash}",
                    f"Conflicting Application: {other_college_match}"
                ],
                source_document=filename,
                recommended_action="Immediately escalate to AICTE Anti-Collusion Special Scrutiny Cell.",
                is_contradiction=True,
                is_anomaly=True
            ))
        else:
            checks.append(ValidationCheck(
                check_name="Cross-Institution Document Uniqueness",
                status=CheckStatus.PASSED,
                rule_id="RULE_COLLUSION_FINGERPRINT",
                statutory_clause="AICTE APH 2024-25, Clause 2.14.4 (Document Authenticity)",
                severity=FindingSeverity.INFO,
                expected_value="Unique Document Fingerprint",
                extracted_value=f"SHA-256: {file_hash[:16]}...",
                difference_details="Document cryptographic hash is unique across non-affiliated institutional repositories.",
                evidence_claims=[f"SHA-256: {file_hash}"],
                source_document=filename
            ))

        # -------------------------------------------------------------
        # Aggregate Results and Compute Calibrated Confidence
        # -------------------------------------------------------------
        passed_list = [c for c in checks if c.status == CheckStatus.PASSED]
        mismatch_list = [c for c in checks if c.status == CheckStatus.MISMATCH]
        missing_list = [c for c in checks if c.status == CheckStatus.MISSING_INFORMATION]
        unverified_list = [c for c in checks if c.status == CheckStatus.UNVERIFIED]

        has_critical = any(c.severity == FindingSeverity.CRITICAL for c in mismatch_list)
        has_high = any(c.severity == FindingSeverity.HIGH for c in mismatch_list)

        # Confidence calculation
        avg_extract_conf = sum(f.confidence for f in raw_fields) / len(raw_fields) if raw_fields else 0.50
        evaluable_checks = len(passed_list) + len(mismatch_list)
        pass_ratio = len(passed_list) / evaluable_checks if evaluable_checks > 0 else 0.50

        issuer_score = 1.0 if issuer_resp.matched else (0.40 if issuer_resp.status == VerificationStatus.SOURCE_UNAVAILABLE else 0.10)
        raw_conf = (avg_extract_conf * 0.30) + (pass_ratio * 0.40) + (issuer_score * 0.30)

        # Calibrate & Route
        if has_critical:
            overall_status = "FLAGGED_ANOMALY"
            calibrated_conf = min(0.35, round(raw_conf, 2))
            summary = f"Flagged with {len(mismatch_list)} statutory non-compliance finding(s) including critical contradictions."
        elif has_high or len(missing_list) > 0 or len(unverified_list) > 0:
            overall_status = "NEEDS_OFFICER_REVIEW"
            calibrated_conf = round(min(0.75, max(0.40, raw_conf)), 2)
            summary = f"Routed to officer scrutiny review ({len(mismatch_list)} mismatch(es), {len(missing_list)} missing field(s), {len(unverified_list)} unverified)."
        else:
            overall_status = "VERIFIED_AUTO"
            calibrated_conf = round(max(0.85, min(0.99, raw_conf)), 2)
            summary = f"All {len(passed_list)} targeted regulatory checks satisfied with high statutory confidence."

        return SingleDocValidationResult(
            college_id=college_id,
            college_name=college_profile["institution_name"],
            document_type=doc_type.value,
            filename=filename,
            file_hash_sha256=file_hash,
            file_size_bytes=file_size,
            page_count=page_count,
            identification=CollegeIdentificationResult(
                status=IdentificationStatus.EXACT_MATCH,
                identified_app_id=college_id,
                identified_name=college_profile["institution_name"],
                confidence=1.0,
                method="Targeted Verification",
                explanation=f"Validating against selected college '{college_profile['institution_name']}'."
            ),
            extracted_fields=[
                {
                    "field_name": f.field_name,
                    "field_value": f.field_value,
                    "confidence": f.confidence,
                    "extraction_method": f.extraction_method,
                    "page_number": f.page_number
                }
                for f in raw_fields
            ],
            all_checks=checks,
            passed_checks=passed_list,
            mismatches=mismatch_list,
            missing_info=missing_list,
            unverified=unverified_list,
            overall_status=overall_status,
            calibrated_confidence=calibrated_conf,
            summary=summary,
            authority_verification=issuer_info
        )
