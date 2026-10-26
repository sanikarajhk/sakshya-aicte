"""
Sakshya Synthetic Dataset Generator
Generates 30 fictional institutional applications with real PDF & image documents,
exact ground truth, planted defects, contradictions, and ring collusion signals.
Fixed seed ensures 100% reproducibility.
"""

import json
import random
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from sakshya.core.config import SYNTHETIC_DIR, DATA_DIR, settings
from sakshya.core.models import (
    ApplicationDB, DocumentDB, ExtractedFieldDB, FindingDB,
    ApplicationStatus, DocumentType, VerificationStatus, FindingSeverity
)
from sakshya.core.database import get_db_context, init_db
from sakshya.core.audit import log_event
from sakshya.data_generator.pdf_builder import (
    create_notary_stamp_image,
    create_mock_qr_image,
    generate_land_title_pdf,
    generate_building_plan_pdf,
    generate_fire_noc_pdf,
    generate_mandatory_disclosure_pdf,
    degrade_pdf_to_scanned_image
)

# Deterministic random generator
rng = random.Random(settings.RANDOM_SEED)

SHARED_RING_NOTARY_REG = "NOT/2021/DEL/8821"
SHARED_RING_NOTARY_NAME = "R. C. Malhotra"
SHARED_RING_ARCHITECT = "Ar. Vikramaditya Joshi, CA/2014/66542"
SHARED_RING_BANK = "State Bank of India, Connaught Place Main Branch, New Delhi"
SHARED_RING_SURVEY = "Plot 44-B/Institutional Corridor"

INSTITUTION_NAMES_POOL = [
    "Vidyapeeth Institute of Technology",
    "Saraswati College of Engineering",
    "Kaveri Academy of Management Studies",
    "Godavari Polytechnic Institute",
    "Brahmaputra Engineering Academy",
    "Narmada Institute of Pharmaceutical Education",
    "Himalayan Institute of Higher Technology",
    "Deccan College of Applied Sciences",
    "Malabar Technical Campus",
    "Konkan Institute of Technology",
    "Shivalik Institute of Engineering",
    "Satpura Institute of Management",
    "Vindhya College of Technology",
    "Aravalli Institute of Technical Studies",
    "Nilgiri College of Applied Engineering",
    "Apex Institute of Management & Engineering",
    "Utkal Technical Institute",
    "Magadh Institute of Science & Technology",
    "Gandhara Institute of Technology",
    "Takshashila Institute of Advanced Research",
    "Nalanda College of Engineering & Technology",
    "Pataliputra Technical Campus",
    "Indus Valley Institute of Management",
    "Chanakya Institute of Technical Studies",
    "Vanguard Institute of Engineering & Technology",
    "Drona Academy of Applied Technology",
    "Horizon Institute of Polytechnic Studies",
    "Zenith College of Management & Computer Applications",
    "Shivalik Global Institute of Technical Education",
    "Aryavart Institute of Pharmaceutical Sciences",
]

STATES_CITIES = [
    ("Maharashtra", "Pune"),
    ("Karnataka", "Bengaluru"),
    ("Tamil Nadu", "Coimbatore"),
    ("Uttar Pradesh", "Kanpur"),
    ("Gujarat", "Ahmedabad"),
    ("Haryana", "Gurugram"),
    ("Delhi", "New Delhi"),
    ("Telangana", "Hyderabad"),
    ("Rajasthan", "Jaipur"),
    ("West Bengal", "Kolkata"),
]


def compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def compute_perceptual_hash(path: Path) -> str:
    """Compute average perceptual image hash for duplicate detection."""
    try:
        import imagehash
        from PIL import Image
        if path.suffix.lower() == ".png":
            img = Image.open(path)
            return str(imagehash.average_hash(img))
        # For PDF, use deterministic structural hash
        return hashlib.md5(f"p-hash-{path.name}".encode()).hexdigest()[:16]
    except Exception:
        return hashlib.md5(path.name.encode()).hexdigest()[:16]


def generate_all_applications() -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Generate all 30 fictional institutional applications with files,
    planted defects, ground truth, and mock issuer records.
    """
    print(f"Generating 30 synthetic applications in {SYNTHETIC_DIR}...")
    init_db()

    # Pre-generate shared notary stamp for collusion ring
    ring_stamp_path = SYNTHETIC_DIR / "shared_assets" / "notary_stamp_ring.png"
    create_notary_stamp_image(
        output_path=ring_stamp_path,
        notary_name=SHARED_RING_NOTARY_NAME,
        reg_number=SHARED_RING_NOTARY_REG,
        date_str="12/03/2023",
        color_rgb=(170, 20, 20)
    )

    all_apps_metadata = []
    ground_truth_records = {}
    mock_issuer_db = {}

    for i in range(1, 31):
        app_id = f"APP-{i:03d}"
        inst_id = f"INST-{i:03d}"
        inst_name = INSTITUTION_NAMES_POOL[i - 1]
        state_idx = (i - 1) % len(STATES_CITIES)
        state, district = STATES_CITIES[state_idx]
        app_folder = SYNTHETIC_DIR / app_id
        app_folder.mkdir(parents=True, exist_ok=True)

        inst_type = ["Engineering", "Management", "Pharmacy", "Polytechnic"][i % 4]
        applied_intake = 180 + (i * 30) % 360
        land_area_acres = 5.0 + (i * 0.5) % 10.0
        survey_number = f"SY-{100 + i * 7}/{i % 5 + 1}-A"
        society_name = f"{inst_name.split()[0]} Educational Trust"
        architect_license = f"Ar. S. K. Gupta, CA/2012/{40000 + i}"
        notary_reg = f"NOT/2019/ST/{5000 + i}"
        notary_name = f"Notary {chr(65 + (i % 26))} Kumar"
        bank_name = f"Bank of Baroda, {district} Main Branch"

        is_clean = True
        injected_defects = []
        is_ring_member = False
        ring_cluster_id = None
        expected_status = ApplicationStatus.VERIFIED_AUTO
        issuer_land_status = VerificationStatus.VERIFIED
        issuer_building_status = VerificationStatus.VERIFIED
        issuer_fire_status = VerificationStatus.VERIFIED

        # Planted defects & variations
        # 1. Clean Apps (APP-001 to APP-010)
        if 1 <= i <= 10:
            is_clean = True
            expected_status = ApplicationStatus.VERIFIED_AUTO

        # 2. Missing Documents
        elif i == 11:
            is_clean = False
            injected_defects.append("MISSING_FIRE_NOC")
            expected_status = ApplicationStatus.NEEDS_OFFICER_REVIEW
            issuer_fire_status = VerificationStatus.VERIFICATION_PENDING
        elif i == 12:
            is_clean = False
            injected_defects.append("MISSING_BUILDING_PLAN")
            expected_status = ApplicationStatus.NEEDS_OFFICER_REVIEW

        # 3. Expired Documents
        elif i == 13:
            is_clean = False
            injected_defects.append("EXPIRED_FIRE_NOC")
            expected_status = ApplicationStatus.NEEDS_OFFICER_REVIEW
            issuer_fire_status = VerificationStatus.EXPIRED
        elif i == 14:
            is_clean = False
            injected_defects.append("EXPIRED_BUILDING_PLAN")
            expected_status = ApplicationStatus.NEEDS_OFFICER_REVIEW
            issuer_building_status = VerificationStatus.EXPIRED

        # 4. Cross-Document Contradictions (At least 5 planted contradictions)
        elif i == 15:
            # Contradiction 1: Land Area Mismatch
            is_clean = False
            injected_defects.append("CONTRADICTION_LAND_AREA")
            expected_status = ApplicationStatus.FLAGGED_ANOMALY
        elif i == 16:
            # Contradiction 2: Institution Name Mismatch
            is_clean = False
            injected_defects.append("CONTRADICTION_INSTITUTION_NAME")
            expected_status = ApplicationStatus.FLAGGED_ANOMALY
            issuer_building_status = VerificationStatus.MISMATCH_DETECTED
        elif i == 17:
            # Contradiction 3: Survey Number Mismatch
            is_clean = False
            injected_defects.append("CONTRADICTION_SURVEY_NUMBER")
            expected_status = ApplicationStatus.FLAGGED_ANOMALY
        elif i == 18:
            # Contradiction 4: Temporal sequence impossibility
            is_clean = False
            injected_defects.append("CONTRADICTION_TEMPORAL_SEQUENCE")
            expected_status = ApplicationStatus.FLAGGED_ANOMALY
        elif i == 19:
            # Contradiction 5: Certificate Reference Number Mismatch
            is_clean = False
            injected_defects.append("CONTRADICTION_CERTIFICATE_NUMBER")
            expected_status = ApplicationStatus.FLAGGED_ANOMALY

        # 5. Degraded scan / Anomaly
        elif i == 20:
            is_clean = False
            injected_defects.append("DEGRADED_SCAN_LOW_CONFIDENCE")
            expected_status = ApplicationStatus.NEEDS_OFFICER_REVIEW
        elif i == 21:
            is_clean = False
            injected_defects.append("SUSPICIOUS_METADATA_DATE_ALTERATION")
            expected_status = ApplicationStatus.FLAGGED_ANOMALY
        elif i == 22:
            is_clean = False
            injected_defects.append("SUSPICIOUS_FONT_LAND_ALTERATION")
            expected_status = ApplicationStatus.FLAGGED_ANOMALY

        # 6. Mock Issuer variations
        elif i == 23:
            is_clean = False
            injected_defects.append("ISSUER_SOURCE_UNAVAILABLE")
            expected_status = ApplicationStatus.NEEDS_OFFICER_REVIEW
            issuer_land_status = VerificationStatus.SOURCE_UNAVAILABLE
        elif i == 24:
            is_clean = False
            injected_defects.append("ISSUER_MANUAL_REVIEW_REQUIRED")
            expected_status = ApplicationStatus.NEEDS_OFFICER_REVIEW
            issuer_land_status = VerificationStatus.MANUAL_REVIEW_REQUIRED

        # 7. Cross-Institution Collusion Ring (APP-025 to APP-030: 6 institutions)
        elif 25 <= i <= 30:
            is_clean = False
            is_ring_member = True
            ring_cluster_id = "COLLUSION_RING_NCR_01"
            injected_defects.append("COLLUSION_RING_SHARED_NOTARY_AND_SURVEY")
            expected_status = ApplicationStatus.FLAGGED_ANOMALY
            # Ring shared attributes
            notary_reg = SHARED_RING_NOTARY_REG
            notary_name = SHARED_RING_NOTARY_NAME
            architect_license = SHARED_RING_ARCHITECT
            bank_name = SHARED_RING_BANK
            survey_number = SHARED_RING_SURVEY  # Suspicious identical leased survey plot!

        # Dates
        land_issue_date = "2020-03-15"
        building_issue_date = "2021-06-20"
        building_expiry_date = "2027-06-19"
        fire_issue_date = "2024-08-10"
        fire_expiry_date = "2027-08-09"

        # Apply specific defect overrides to dates/content
        if "EXPIRED_FIRE_NOC" in injected_defects:
            fire_issue_date = "2021-01-10"
            fire_expiry_date = "2022-01-09"  # Expired!
        if "EXPIRED_BUILDING_PLAN" in injected_defects:
            building_issue_date = "2018-05-10"
            building_expiry_date = "2022-05-09"  # Expired!

        land_deed_acreage = land_area_acres
        mdisc_land_acreage = land_area_acres
        if "CONTRADICTION_LAND_AREA" in injected_defects:
            land_deed_acreage = 4.50  # Deed says 4.50 Acres
            mdisc_land_acreage = 7.50  # Application & Disclosure claim 7.50 Acres

        building_inst_name = inst_name
        if "CONTRADICTION_INSTITUTION_NAME" in injected_defects:
            building_inst_name = "Apex Institute of Science & Technology"  # Conflict!

        building_survey_number = survey_number
        if "CONTRADICTION_SURVEY_NUMBER" in injected_defects:
            building_survey_number = "SY-209/7-A"  # Conflict with Land Deed!

        fire_noc_num = f"NOC-FIRE-2023-{8000 + i}"
        mdisc_fire_noc_num = fire_noc_num
        if "CONTRADICTION_CERTIFICATE_NUMBER" in injected_defects:
            mdisc_fire_noc_num = f"NOC-FIRE-2023-9981"  # Mismatch with actual doc!

        if "CONTRADICTION_TEMPORAL_SEQUENCE" in injected_defects:
            land_issue_date = "2018-02-15"  # Trust purchased in 2018, but Trust founded 2024!

        # Generate Notary Stamp
        if is_ring_member:
            notary_stamp_file = ring_stamp_path
        else:
            notary_stamp_file = app_folder / f"notary_stamp_{app_id}.png"
            create_notary_stamp_image(
                output_path=notary_stamp_file,
                notary_name=notary_name,
                reg_number=notary_reg,
                date_str=land_issue_date,
                color_rgb=(20, 40, 160)
            )

        # Generate QR code tokens
        land_qr_file = app_folder / f"qr_land_{app_id}.png"
        building_qr_file = app_folder / f"qr_bplan_{app_id}.png"
        fire_qr_file = app_folder / f"qr_fire_{app_id}.png"

        create_mock_qr_image(land_qr_file, f"STATE_REV_REG:{app_id}:DEED-{2020 + i}:LAND:{land_deed_acreage}")
        create_mock_qr_image(building_qr_file, f"MUNI_BPLAN:{app_id}:{survey_number}:AREA:12500")
        create_mock_qr_image(fire_qr_file, f"FIRE_DEPT:{app_id}:{fire_noc_num}:VALID:{fire_expiry_date}")

        # Generate PDF files
        documents_generated = []

        # 1. Land Title Deed PDF
        land_pdf = app_folder / f"land_title_{app_id}.pdf"
        generate_land_title_pdf(
            output_path=land_pdf,
            institution_name=inst_name,
            survey_number=survey_number,
            land_area_acres=land_deed_acreage,
            owner_trust_name=society_name,
            registration_number=f"REG-DEED-{2020 + i}-DL",
            issue_date=land_issue_date,
            notary_stamp_path=notary_stamp_file,
            qr_code_path=land_qr_file
        )
        documents_generated.append({
            "type": DocumentType.LAND_TITLE,
            "path": land_pdf,
            "filename": land_pdf.name,
            "issuer_status": issuer_land_status,
            "expiry_date": None,
            "is_expired": False
        })

        # 2. Building Plan Sanction PDF (Skip if missing document defect)
        if "MISSING_BUILDING_PLAN" not in injected_defects:
            bplan_pdf = app_folder / f"building_plan_{app_id}.pdf"
            generate_building_plan_pdf(
                output_path=bplan_pdf,
                institution_name=building_inst_name,
                survey_number=building_survey_number,
                built_up_area_sqm=12500.0 + (i * 250),
                approval_number=f"BP-SANCT-{2021 + i}/MUN",
                approval_date=building_issue_date,
                expiry_date=building_expiry_date,
                architect_license=architect_license,
                qr_code_path=building_qr_file
            )
            documents_generated.append({
                "type": DocumentType.BUILDING_PLAN,
                "path": bplan_pdf,
                "filename": bplan_pdf.name,
                "issuer_status": issuer_building_status,
                "expiry_date": building_expiry_date,
                "is_expired": "EXPIRED_BUILDING_PLAN" in injected_defects
            })

        # 3. Fire NOC PDF (Skip if missing fire noc defect)
        if "MISSING_FIRE_NOC" not in injected_defects:
            fire_pdf = app_folder / f"fire_noc_{app_id}.pdf"
            generate_fire_noc_pdf(
                output_path=fire_pdf,
                institution_name=inst_name,
                noc_number=fire_noc_num,
                issue_date=fire_issue_date,
                expiry_date=fire_expiry_date,
                qr_code_path=fire_qr_file
            )
            # For degraded scan test case
            if "DEGRADED_SCAN_LOW_CONFIDENCE" in injected_defects:
                degraded_img = app_folder / f"fire_noc_degraded_{app_id}.png"
                degrade_pdf_to_scanned_image(fire_pdf, degraded_img, noise_level=1.5)

            documents_generated.append({
                "type": DocumentType.FIRE_NOC,
                "path": fire_pdf,
                "filename": fire_pdf.name,
                "issuer_status": issuer_fire_status,
                "expiry_date": fire_expiry_date,
                "is_expired": "EXPIRED_FIRE_NOC" in injected_defects
            })

        # 4. Mandatory Disclosure PDF
        mdisc_pdf = app_folder / f"mandatory_disclosure_{app_id}.pdf"
        generate_mandatory_disclosure_pdf(
            output_path=mdisc_pdf,
            institution_name=inst_name,
            institution_type=inst_type,
            society_trust_name=society_name,
            land_area_acres=mdisc_land_acreage,
            survey_number=survey_number,
            fire_noc_number=mdisc_fire_noc_num,
            applied_intake=applied_intake,
            principal_name=f"Dr. Principal {chr(65 + i)} Sharma"
        )
        documents_generated.append({
            "type": DocumentType.MANDATORY_DISCLOSURE,
            "path": mdisc_pdf,
            "filename": mdisc_pdf.name,
            "issuer_status": VerificationStatus.VERIFIED,
            "expiry_date": None,
            "is_expired": False
        })

        # Compute document hashes and store metadata
        doc_meta_list = []
        for d in documents_generated:
            f_hash = compute_file_hash(d["path"])
            p_hash = compute_perceptual_hash(d["path"])
            doc_meta_list.append({
                "document_type": d["type"].value,
                "filename": d["filename"],
                "file_path": str(d["path"]),
                "file_hash": f_hash,
                "perceptual_hash": p_hash,
                "file_size": d["path"].stat().st_size,
                "issuer_status": d["issuer_status"].value,
                "is_expired": d["is_expired"],
                "expiry_date": d["expiry_date"]
            })

        # Register ground truth
        app_entry = {
            "application_id": app_id,
            "institution_id": inst_id,
            "institution_name": inst_name,
            "institution_type": inst_type,
            "state": state,
            "district": district,
            "applied_intake": applied_intake,
            "land_area_acres": land_area_acres,
            "survey_number": survey_number,
            "society_trust_name": society_name,
            "architect_license": architect_license,
            "notary_registration": notary_reg,
            "bank_name": bank_name,
            "is_clean": is_clean,
            "injected_defects": injected_defects,
            "flagged_ring": is_ring_member,
            "ring_cluster_id": ring_cluster_id,
            "expected_status": expected_status.value,
            "documents": doc_meta_list
        }
        all_apps_metadata.append(app_entry)
        ground_truth_records[app_id] = app_entry

        # Mock Issuer ground-truth records
        mock_issuer_db[app_id] = {
            "land_registry": {
                "status": issuer_land_status.value,
                "registered_survey": survey_number,
                "registered_acreage": land_deed_acreage,
                "registered_owner": society_name,
                "litigation_flag": issuer_land_status == VerificationStatus.MANUAL_REVIEW_REQUIRED
            },
            "municipal_bplan": {
                "status": issuer_building_status.value,
                "institution_name": building_inst_name,
                "survey_number": building_survey_number,
                "expiry_date": building_expiry_date
            },
            "fire_department": {
                "status": issuer_fire_status.value,
                "noc_number": fire_noc_num,
                "expiry_date": fire_expiry_date
            }
        }

    # Save ground truth to JSON and CSV
    ground_truth_file = DATA_DIR / "ground_truth.json"
    with open(ground_truth_file, "w") as f:
        json.dump(ground_truth_records, f, indent=2)

    mock_db_file = DATA_DIR / "mock_issuer_registry.json"
    with open(mock_db_file, "w") as f:
        json.dump(mock_issuer_db, f, indent=2)

    # Save summary CSV
    import pandas as pd
    summary_rows = []
    for item in all_apps_metadata:
        summary_rows.append({
            "application_id": item["application_id"],
            "institution_name": item["institution_name"],
            "state": item["state"],
            "district": item["district"],
            "is_clean": item["is_clean"],
            "expected_status": item["expected_status"],
            "defects_count": len(item["injected_defects"]),
            "defects": "; ".join(item["injected_defects"]),
            "is_ring_member": item["flagged_ring"],
            "documents_count": len(item["documents"])
        })
    csv_file = DATA_DIR / "applications_metadata.csv"
    pd.DataFrame(summary_rows).to_csv(csv_file, index=False)

    print(f"Dataset generated successfully! 30 applications created with {sum(len(a['documents']) for a in all_apps_metadata)} files.")
    return all_apps_metadata, ground_truth_records


if __name__ == "__main__":
    generate_all_applications()
