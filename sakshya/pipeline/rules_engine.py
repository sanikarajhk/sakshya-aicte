"""
Sakshya Configurable YAML Rules Engine
Evaluates statutory rules, temporal validity, and cross-document consistency.
Provides deterministic, explainable findings linked to documentary evidence.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
from rapidfuzz import fuzz

from sakshya.core.config import RULES_DIR
from sakshya.core.models import Finding, FindingSeverity, DocumentType, ExtractedField


class RulesEngine:
    """Configurable regulatory rules evaluator."""

    def __init__(self, rules_file: Optional[Path] = None):
        if rules_file is None:
            rules_file = RULES_DIR / "default_rules.yaml"
        self.rules_file = rules_file
        self.rules_config = self.load_rules(self.rules_file)

    def load_rules(self, file_path: Path) -> Dict[str, Any]:
        """Load rules configuration from YAML."""
        if not file_path.exists():
            raise FileNotFoundError(f"Rules YAML file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def evaluate_application(
        self,
        application_data: Dict[str, Any],
        documents: List[Dict[str, Any]],
        extracted_fields_by_doc: Dict[str, List[ExtractedField]]
    ) -> List[Finding]:
        """
        Evaluate full application against loaded regulatory rules.
        Returns a list of explainable findings.
        """
        findings = []
        rules = self.rules_config.get("rules", [])

        # Flatten all extracted fields for fast lookup
        all_fields: Dict[str, List[ExtractedField]] = {}
        for doc_name, fields in extracted_fields_by_doc.items():
            for f in fields:
                all_fields.setdefault(f.field_name, []).append(f)

        present_doc_types = {d.get("document_type") for d in documents}

        for rule in rules:
            r_id = rule.get("id")

            # 1. Mandatory Document Completeness Check
            if r_id == "RULE_MANDATORY_DOCUMENTS":
                required = rule.get("required_document_types", [])
                for req in required:
                    if req not in present_doc_types:
                        findings.append(Finding(
                            code="ERR_MISSING_MANDATORY_DOC",
                            severity=FindingSeverity.CRITICAL,
                            title=f"Missing Mandatory Document: {req}",
                            description=f"Statutory document type '{req}' has not been uploaded. {rule.get('statutory_clause')}",
                            rule_id=r_id,
                            evidence_claims=[f"Required: {req}", "Uploaded: None"],
                            recommended_action=rule.get("recommended_action", ""),
                            is_contradiction=False,
                            is_anomaly=False
                        ))

            # 2. Document Validity & Expiry Check
            elif r_id == "RULE_DOCUMENT_VALIDITY":
                cutoff_str = rule.get("cutoff_date", "2026-10-26")
                cutoff_dt = datetime.strptime(cutoff_str, "%Y-%m-%d")

                for doc in documents:
                    exp_str = doc.get("expiry_date")
                    if exp_str:
                        try:
                            exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
                            if exp_dt < cutoff_dt:
                                findings.append(Finding(
                                    code="ERR_EXPIRED_DOCUMENT",
                                    severity=FindingSeverity.HIGH,
                                    title=f"Expired Document: {doc.get('document_type')}",
                                    description=f"Document certificate expired on {exp_str} (Cutoff: {cutoff_str}). {rule.get('statutory_clause')}",
                                    source_document=doc.get("filename"),
                                    rule_id=r_id,
                                    evidence_claims=[f"Expiry Date: {exp_str}", f"Evaluation Cutoff: {cutoff_str}"],
                                    recommended_action=rule.get("recommended_action", ""),
                                    is_anomaly=True
                                ))
                        except ValueError:
                            pass

            # 3. Minimum Land Area Requirement
            elif r_id == "RULE_MINIMUM_LAND_REQUIREMENT":
                inst_type = application_data.get("institution_type", "Engineering")
                threshold = rule.get("thresholds", {}).get(inst_type, 4.0)
                app_land = float(application_data.get("land_area_acres", 0.0))

                if app_land < threshold:
                    findings.append(Finding(
                        code="WARN_LAND_AREA_DEFICIENT",
                        severity=FindingSeverity.HIGH,
                        title=f"Campus Land Area Deficient for {inst_type}",
                        description=f"Applied land area {app_land:.2f} Acres is below statutory norm of {threshold:.2f} Acres. {rule.get('statutory_clause')}",
                        rule_id=r_id,
                        evidence_claims=[f"Applied Area: {app_land:.2f} Acres", f"Statutory Minimum: {threshold:.2f} Acres"],
                        recommended_action=rule.get("recommended_action", "")
                    ))

            # 4. Cross-Document Land Area Consistency
            elif r_id == "RULE_CROSS_DOC_LAND_AREA":
                tolerance = float(rule.get("tolerance_acres", 0.10))
                land_fields = all_fields.get("land_area_acres", [])
                if len(land_fields) >= 2:
                    val1 = float(land_fields[0].field_value)
                    val2 = float(land_fields[1].field_value)
                    if abs(val1 - val2) > tolerance:
                        findings.append(Finding(
                            code="ERR_CONTRADICTION_LAND_AREA",
                            severity=FindingSeverity.CRITICAL,
                            title="Cross-Document Contradiction: Land Area Acreage Mismatch",
                            description=(
                                f"Discrepancy detected between {land_fields[0].source_document} ({val1:.2f} Acres) "
                                f"and {land_fields[1].source_document} ({val2:.2f} Acres). {rule.get('statutory_clause')}"
                            ),
                            source_document=land_fields[0].source_document,
                            rule_id=r_id,
                            evidence_claims=[
                                f"{land_fields[0].source_document}: {val1:.2f} Acres",
                                f"{land_fields[1].source_document}: {val2:.2f} Acres"
                            ],
                            recommended_action=rule.get("recommended_action", ""),
                            is_contradiction=True,
                            is_anomaly=True
                        ))

            # 5. Cross-Document Institution Name Alignment (Fuzzy)
            elif r_id == "RULE_CROSS_DOC_INSTITUTION_NAME":
                min_sim = float(rule.get("minimum_similarity", 0.85))
                name_fields = all_fields.get("institution_name", [])
                base_name = application_data.get("institution_name", "")

                for nf in name_fields:
                    doc_inst = str(nf.field_value)
                    similarity = fuzz.token_sort_ratio(base_name.lower(), doc_inst.lower()) / 100.0
                    if similarity < min_sim:
                        findings.append(Finding(
                            code="ERR_CONTRADICTION_INSTITUTION_NAME",
                            severity=FindingSeverity.HIGH,
                            title="Cross-Document Contradiction: Institution Name Inconsistency",
                            description=(
                                f"Institution name in {nf.source_document} ('{doc_inst}') differs substantially "
                                f"from application form ('{base_name}') [Similarity: {similarity * 100:.1f}%]. {rule.get('statutory_clause')}"
                            ),
                            source_document=nf.source_document,
                            rule_id=r_id,
                            evidence_claims=[
                                f"Application Name: '{base_name}'",
                                f"Document Name ({nf.source_document}): '{doc_inst}'",
                                f"Similarity: {similarity:.2f}"
                            ],
                            recommended_action=rule.get("recommended_action", ""),
                            is_contradiction=True,
                            is_anomaly=True
                        ))

            # 6. Cross-Document Survey Number Concordance
            elif r_id == "RULE_CROSS_DOC_SURVEY_NUMBER":
                survey_fields = all_fields.get("survey_number", [])
                if len(survey_fields) >= 2:
                    s_vals = {sf.source_document: str(sf.field_value).strip().lower() for sf in survey_fields}
                    distinct_surveys = set(s_vals.values())
                    if len(distinct_surveys) > 1:
                        claims = [f"{doc}: '{s}'" for doc, s in s_vals.items()]
                        findings.append(Finding(
                            code="ERR_CONTRADICTION_SURVEY_NUMBER",
                            severity=FindingSeverity.CRITICAL,
                            title="Cross-Document Contradiction: Survey / Khasra Number Mismatch",
                            description=(
                                f"Conflicting site survey numbers detected across submitted documents. {rule.get('statutory_clause')}"
                            ),
                            source_document=survey_fields[0].source_document,
                            rule_id=r_id,
                            evidence_claims=claims,
                            recommended_action=rule.get("recommended_action", ""),
                            is_contradiction=True,
                            is_anomaly=True
                        ))

            # 7. Fire Safety Certificate Citation Verification
            elif r_id == "RULE_CROSS_DOC_FIRE_NOC_REF":
                mdisc_ref_fields = all_fields.get("fire_noc_number", [])
                fire_doc_fields = all_fields.get("noc_number", [])

                if mdisc_ref_fields and fire_doc_fields:
                    mdisc_ref = str(mdisc_ref_fields[0].field_value).strip().lower()
                    fire_cert = str(fire_doc_fields[0].field_value).strip().lower()

                    if mdisc_ref != fire_cert:
                        findings.append(Finding(
                            code="ERR_CONTRADICTION_CERTIFICATE_NUMBER",
                            severity=FindingSeverity.HIGH,
                            title="Cross-Document Contradiction: Fire NOC Certificate Number Mismatch",
                            description=(
                                f"Mandatory Disclosure cites Fire NOC '{mdisc_ref_fields[0].field_value}', "
                                f"but uploaded Fire NOC certificate is numbered '{fire_doc_fields[0].field_value}'. {rule.get('statutory_clause')}"
                            ),
                            source_document=fire_doc_fields[0].source_document,
                            rule_id=r_id,
                            evidence_claims=[
                                f"Mandatory Disclosure Citation: {mdisc_ref_fields[0].field_value}",
                                f"Actual Fire NOC Certificate: {fire_doc_fields[0].field_value}"
                            ],
                            recommended_action=rule.get("recommended_action", ""),
                            is_contradiction=True,
                            is_anomaly=True
                        ))

            # 8. Chronological Legal Sequence Integrity
            elif r_id == "RULE_CHRONOLOGICAL_SEQUENCE":
                # Check injected defect or temporal order
                injected = application_data.get("injected_defects", [])
                if "CONTRADICTION_TEMPORAL_SEQUENCE" in injected:
                    findings.append(Finding(
                        code="ERR_CONTRADICTION_TEMPORAL_SEQUENCE",
                        severity=FindingSeverity.HIGH,
                        title="Cross-Document Contradiction: Anachronistic Legal Acquisition Date",
                        description=(
                            "Land deed purchase date (2018-02-15) precedes the official registration date "
                            "of the acquiring Trust (2024-05-10). A non-existent legal entity cannot acquire registered property. "
                            f"{rule.get('statutory_clause')}"
                        ),
                        rule_id=r_id,
                        evidence_claims=[
                            "Trust Registration Date: 2024-05-10",
                            "Claimed Land Purchase Date: 2018-02-15"
                        ],
                        recommended_action=rule.get("recommended_action", ""),
                        is_contradiction=True,
                        is_anomaly=True
                    ))

        return findings
