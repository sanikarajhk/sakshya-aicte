"""
Sakshya Unit & Integration Tests: Document Upload and Targeted College Validation
Verifies all 8 required upload-to-validation scenarios:
1. Valid PDF belonging to a known college.
2. Document whose college can only be identified after user selection.
3. Unknown college.
4. Ambiguous college match.
5. Document with a mismatched field.
6. Corrupted or unreadable PDF.
7. Missing reference data.
8. Two consecutive uploads belonging to different colleges (state isolation).
"""

import io
from pathlib import Path
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from sakshya.data_generator.ground_truth import load_ground_truth
from sakshya.core.models import DocumentType, FindingSeverity
from sakshya.pipeline.single_doc_validator import (
    SingleDocValidator, IdentificationStatus, CheckStatus
)


@pytest.fixture
def validator():
    return SingleDocValidator()


@pytest.fixture
def ground_truth():
    return load_ground_truth()


def create_simple_pdf_bytes(text_lines: list[str]) -> bytes:
    """Helper to generate an in-memory PDF with arbitrary text lines."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    y = 750
    for line in text_lines:
        c.drawString(50, y, line)
        y -= 25
    c.save()
    buffer.seek(0)
    return buffer.read()


# -----------------------------------------------------------------------------
# Scenario 1: Valid PDF belonging to a known college
# -----------------------------------------------------------------------------
def test_valid_pdf_known_college(validator, ground_truth):
    """Test 1: Valid PDF belonging to APP-001 (Vidyapeeth Institute of Technology)."""
    app_data = ground_truth["APP-001"]
    doc_meta = app_data["documents"][0]  # Land title
    doc_path = Path(doc_meta["file_path"])

    with open(doc_path, "rb") as f:
        pdf_bytes = f.read()

    # 1. Validate PDF bytes
    is_valid, err, meta = validator.validate_pdf_bytes(pdf_bytes, doc_path.name)
    assert is_valid is True
    assert err == ""
    assert meta["page_count"] >= 1
    assert len(meta["sha256"]) == 64

    # 2. Identify College
    ident = validator.identify_college(meta["full_text"], meta["filename"])
    assert ident.status in [IdentificationStatus.EXACT_MATCH, IdentificationStatus.HIGH_CONFIDENCE_FUZZY]
    assert ident.identified_app_id == "APP-001"
    assert ident.confidence >= 0.85
    assert "Vidyapeeth" in ident.identified_name

    # 3. Targeted Validation against APP-001
    doc_type = validator.infer_document_type(meta["full_text"], meta["filename"])
    res = validator.validate_document_against_college(ident.identified_app_id, doc_type, meta["filename"], meta)

    assert res.college_id == "APP-001"
    assert res.overall_status == "VERIFIED_AUTO"
    assert res.calibrated_confidence >= 0.85
    assert len(res.mismatches) == 0
    assert len(res.passed_checks) >= 5

    # Check that identity and survey number passed
    check_names = {c.check_name: c.status for c in res.all_checks}
    assert check_names.get("Institutional Name Alignment") == CheckStatus.PASSED
    assert check_names.get("Survey / Plot Number Concordance") == CheckStatus.PASSED


# -----------------------------------------------------------------------------
# Scenario 2: Document whose college can only be identified after user selection
# -----------------------------------------------------------------------------
def test_document_requiring_user_selection(validator, ground_truth):
    """Test 2: Document with generic title where user manually selects target college."""
    # Create generic document that does not name any college directly
    generic_text = [
        "*** REGULATORY COMPLIANCE CERTIFICATE ***",
        "DIRECTORATE OF MUNICIPAL TOWN PLANNING",
        "Sanction Order No: BP-GEN-2024/99",
        "Sanction Date: 2024-01-15",
        "Validity / Expiry Date: 2028-01-14",
        "Institution Name: Campus Knowledge Wing A",
        "Survey / Plot Reference: SY-107/2-A",
        "Total Approved Built-Up Area: 8500.0 sqm",
        "Certified that instructional building layout complies with norms."
    ]
    pdf_bytes = create_simple_pdf_bytes(generic_text)

    is_valid, _, meta = validator.validate_pdf_bytes(pdf_bytes, "generic_bplan.pdf")
    assert is_valid is True

    ident = validator.identify_college(meta["full_text"], meta["filename"])
    # Automated identification cannot be exact because "Campus Knowledge Wing A" is generic
    assert ident.status in [IdentificationStatus.AMBIGUOUS_MATCH, IdentificationStatus.UNKNOWN_COLLEGE]
    assert ident.identified_app_id is None

    # User manually selects APP-001 (which has survey SY-107/2-A)
    user_selected_app_id = "APP-001"
    doc_type = validator.infer_document_type(meta["full_text"], meta["filename"])
    res = validator.validate_document_against_college(user_selected_app_id, doc_type, meta["filename"], meta)

    assert res.college_id == "APP-001"
    # Survey number matches APP-001, but name will be flagged as mismatch/needs review
    assert any(c.check_name == "Survey / Plot Number Concordance" and c.status == CheckStatus.PASSED for c in res.all_checks)
    assert res.overall_status in ["NEEDS_OFFICER_REVIEW", "FLAGGED_ANOMALY"]


# -----------------------------------------------------------------------------
# Scenario 3: Unknown college
# -----------------------------------------------------------------------------
def test_unknown_college(validator):
    """Test 3: Document belonging to an unregistered external institution."""
    unknown_text = [
        "*** OXFORD INTERNATIONAL LAW ACADEMY ***",
        "Affidavit of Infrastructure Compliance",
        "Institution Name: Oxford International Law Academy",
        "Survey Number: PLOT-OX-999",
        "Area: 15.0 Acres",
        "Sponsoring Society: Oxford International Trust"
    ]
    pdf_bytes = create_simple_pdf_bytes(unknown_text)

    is_valid, _, meta = validator.validate_pdf_bytes(pdf_bytes, "oxford_law.pdf")
    assert is_valid is True

    ident = validator.identify_college(meta["full_text"], meta["filename"])
    assert ident.status == IdentificationStatus.UNKNOWN_COLLEGE
    assert ident.identified_app_id is None
    assert "does not belong to any of the 30 registered AICTE colleges" in ident.explanation


# -----------------------------------------------------------------------------
# Scenario 4: Ambiguous college match
# -----------------------------------------------------------------------------
def test_ambiguous_college_match(validator):
    """Test 4: Document with ambiguous name where automated match must not guess."""
    # Text with partially overlapping generic name words
    ambig_text = [
        "*** STATE HIGHER EDUCATION REGISTRY ***",
        "Certificate of Affiliation Endorsement",
        "Institution Name: College of Engineering and Technology",
        "Survey Number: SY-000/0-A"
    ]
    pdf_bytes = create_simple_pdf_bytes(ambig_text)

    is_valid, _, meta = validator.validate_pdf_bytes(pdf_bytes, "ambiguous_college.pdf")
    assert is_valid is True

    ident = validator.identify_college(meta["full_text"], meta["filename"])
    # Must NOT silently assign an exact match
    assert ident.status != IdentificationStatus.EXACT_MATCH
    assert ident.identified_app_id is None
    assert len(ident.top_candidates) > 0


# -----------------------------------------------------------------------------
# Scenario 5: Document with a mismatched field
# -----------------------------------------------------------------------------
def test_document_with_mismatched_field(validator, ground_truth):
    """Test 5: Document for APP-001 with deliberate survey number and land area mismatches."""
    tampered_text = [
        "*** SYNTHETIC TEST DOCUMENT - AICTE SIH26261 TESTING ONLY ***",
        "GOVERNMENT OF STATE REGISTRATION DEPARTMENT",
        "DEED OF PERPETUAL LEASE AND CONVEYANCE",
        "Deed Registration No: REG-TAMPERED-001",
        "Execution Date: 2021-04-10",
        "THIS INDENTURE is made between Land Authority and Vidyapeeth Educational Trust,",
        "for the establishment and perpetual institutional operation of Vidyapeeth Institute of Technology,",
        "SCHEDULE OF PROPERTY:",
        "All that piece of land bearing Survey Number: SY-CONTRADICTION-999, measuring a total area",
        "of 1.20 Acres (equivalent to 4856.2 square meters), situated in Rural Sector.",
        "Attested by Notary Public."
    ]
    pdf_bytes = create_simple_pdf_bytes(tampered_text)

    _, _, meta = validator.validate_pdf_bytes(pdf_bytes, "tampered_deed.pdf")
    ident = validator.identify_college(meta["full_text"], meta["filename"])
    assert ident.identified_app_id == "APP-001"

    doc_type = DocumentType.LAND_TITLE
    res = validator.validate_document_against_college("APP-001", doc_type, meta["filename"], meta)

    # Must detect mismatches: Survey number contradiction and deficient land area
    assert res.overall_status in ["FLAGGED_ANOMALY", "NEEDS_OFFICER_REVIEW"]
    assert len(res.mismatches) >= 2

    mismatch_checks = {m.check_name for m in res.mismatches}
    assert "Survey / Plot Number Concordance" in mismatch_checks
    assert "Land Area Acreage Verification" in mismatch_checks

    survey_mismatch = next(m for m in res.mismatches if m.check_name == "Survey / Plot Number Concordance")
    assert survey_mismatch.severity == FindingSeverity.CRITICAL
    assert survey_mismatch.is_contradiction is True


# -----------------------------------------------------------------------------
# Scenario 6: Corrupted or unreadable PDF
# -----------------------------------------------------------------------------
def test_corrupted_or_unreadable_pdf(validator):
    """Test 6: Corrupted bytes, empty files, and non-PDF formats."""
    # 6a. Empty file
    valid_empty, err_empty, _ = validator.validate_pdf_bytes(b"", "empty.pdf")
    assert valid_empty is False
    assert "empty" in err_empty.lower()

    # 6b. Non-PDF magic header
    valid_corrupt, err_corrupt, _ = validator.validate_pdf_bytes(b"HELLO NOT A PDF", "fake.pdf")
    assert valid_corrupt is False
    assert "PDF signature" in err_corrupt

    # 6c. Header present but truncated/corrupt stream
    truncated_pdf = b"%PDF-1.4\n%%EOF_CORRUPTED_STREAM_GARBAGE_BYTES_123456789"
    valid_trunc, err_trunc, _ = validator.validate_pdf_bytes(truncated_pdf, "corrupted.pdf")
    assert valid_trunc is False
    assert "Corrupted or unreadable PDF" in err_trunc


# -----------------------------------------------------------------------------
# Scenario 7: Missing reference data in college profile
# -----------------------------------------------------------------------------
def test_missing_reference_data(validator):
    """Test 7: College profile missing reference survey number yields UNVERIFIED, not false PASS."""
    # Build a modified validator with sparse reference data
    sparse_gt = {
        "APP-SPARSE": {
            "application_id": "APP-SPARSE",
            "institution_id": "INST-SPARSE",
            "institution_name": "Sparse Polytechnic Institute",
            "institution_type": "Engineering",
            "land_area_acres": 0.0,  # Missing / unrecorded
            "survey_number": None,    # Missing survey number
            "society_trust_name": None,
            "documents": []
        }
    }
    sparse_validator = SingleDocValidator(ground_truth=sparse_gt)

    sparse_text = [
        "*** SPARSE POLYTECHNIC INSTITUTE ***",
        "DEED OF PERPETUAL LEASE",
        "operation of Sparse Polytechnic Institute",
        "Survey Number: SY-SPARSE-101",
        "measuring a total area of 5.00 Acres"
    ]
    pdf_bytes = create_simple_pdf_bytes(sparse_text)
    _, _, meta = sparse_validator.validate_pdf_bytes(pdf_bytes, "sparse_deed.pdf")

    res = sparse_validator.validate_document_against_college("APP-SPARSE", DocumentType.LAND_TITLE, "sparse_deed.pdf", meta)

    # Checks with missing reference data must NOT be marked PASSED
    unverified_checks = {c.check_name for c in res.unverified}
    assert "Survey / Plot Number Concordance" in unverified_checks
    assert "Land Area Acreage Verification" in unverified_checks

    survey_check = next(c for c in res.all_checks if c.check_name == "Survey / Plot Number Concordance")
    assert survey_check.status == CheckStatus.UNVERIFIED


# -----------------------------------------------------------------------------
# Scenario 8: Consecutive uploads belonging to different colleges
# -----------------------------------------------------------------------------
def test_two_consecutive_uploads_isolation(validator, ground_truth):
    """Test 8: Consecutive uploads for APP-001 and APP-002 maintain strict isolation."""
    # Upload 1: Land Title for APP-001
    doc1_path = Path(ground_truth["APP-001"]["documents"][0]["file_path"])
    with open(doc1_path, "rb") as f:
        bytes1 = f.read()

    _, _, meta1 = validator.validate_pdf_bytes(bytes1, doc1_path.name)
    ident1 = validator.identify_college(meta1["full_text"], meta1["filename"])
    assert ident1.identified_app_id == "APP-001"

    res1 = validator.validate_document_against_college("APP-001", DocumentType.LAND_TITLE, meta1["filename"], meta1)
    assert res1.college_id == "APP-001"
    assert "Vidyapeeth" in res1.college_name

    # Upload 2: Land Title for APP-002
    doc2_path = Path(ground_truth["APP-002"]["documents"][0]["file_path"])
    with open(doc2_path, "rb") as f:
        bytes2 = f.read()

    _, _, meta2 = validator.validate_pdf_bytes(bytes2, doc2_path.name)
    ident2 = validator.identify_college(meta2["full_text"], meta2["filename"])
    assert ident2.identified_app_id == "APP-002"

    res2 = validator.validate_document_against_college("APP-002", DocumentType.LAND_TITLE, meta2["filename"], meta2)
    assert res2.college_id == "APP-002"
    assert "Saraswati" in res2.college_name

    # Verify no cross-contamination between results
    assert res1.college_id != res2.college_id
    assert res1.file_hash_sha256 != res2.file_hash_sha256
    assert res1.college_name != res2.college_name
