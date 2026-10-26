"""
Sakshya Field Extraction Engine
Extracts structured claims from raw document text using Regex,
Layout Heuristics, and RapidFuzz string matching.
"""

import re
from typing import Dict, Any, List, Optional
from rapidfuzz import fuzz
from sakshya.core.models import ExtractedField, DocumentType


class FieldExtractor:
    """Robust extractor mapping unstructured text into canonical claim fields."""

    def __init__(self):
        # Regular expressions for standard statutory patterns
        self.date_regex = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b")
        self.acre_regex = re.compile(r"(\d+(?:\.\d+)?)\s*(?:Acres|acres|Acre|acre)")
        self.sqm_regex = re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:sq\.?\s*meters|sqm|sq\s*mtrs)", re.IGNORECASE)
        self.survey_regex = re.compile(r"(?:Survey\s+(?:Number|No\.?)|Plot|Khasra)\s*[:\-]?\s*([A-Za-z0-9\-/\s]+?)(?:,|\.|\n|measuring|situated)", re.IGNORECASE)
        self.noc_regex = re.compile(r"(?:Fire\s*NOC\s*(?:Certificate\s*)?No\.?|Reference)\s*[:\-]?\s*([A-Za-z0-9\-]+)", re.IGNORECASE)
        self.deed_reg_regex = re.compile(r"Deed\s*Registration\s*No\.?\s*[:\-]?\s*([A-Za-z0-9\-]+)", re.IGNORECASE)
        self.bplan_sanct_regex = re.compile(r"Sanction\s*Order\s*No\.?\s*[:\-]?\s*([A-Za-z0-9\-/\.]+)", re.IGNORECASE)
        self.architect_regex = re.compile(r"Ar\.\s*([^,\n]+,\s*CA/\d{4}/\d+)", re.IGNORECASE)
        self.intake_regex = re.compile(r"Approved\s*Student\s*Intake\s*[:\-]?\s*(\d+)", re.IGNORECASE)

    def extract_from_land_title(self, text: str, filename: str) -> List[ExtractedField]:
        """Extract fields from Land Title / Lease Deed."""
        fields = []

        # 1. Deed Registration No
        m = self.deed_reg_regex.search(text)
        if m:
            fields.append(ExtractedField(
                field_name="registration_number",
                field_value=m.group(1).strip(),
                confidence=0.98,
                source_document=filename,
                extraction_method="regex"
            ))

        # 2. Survey Number
        m = self.survey_regex.search(text)
        if m:
            val = m.group(1).strip().replace("Number:", "").strip()
            fields.append(ExtractedField(
                field_name="survey_number",
                field_value=val,
                confidence=0.95,
                source_document=filename,
                extraction_method="regex"
            ))

        # 3. Land Area in Acres
        m = self.acre_regex.search(text)
        if m:
            val = float(m.group(1))
            fields.append(ExtractedField(
                field_name="land_area_acres",
                field_value=val,
                confidence=0.99,
                source_document=filename,
                extraction_method="regex"
            ))

        # 4. Dates
        dates = self.date_regex.findall(text)
        if dates:
            fields.append(ExtractedField(
                field_name="issue_date",
                field_value=dates[0],
                confidence=0.92,
                source_document=filename,
                extraction_method="regex"
            ))

        # 5. Institution Name (via legal clause layout or fuzzy keyword)
        inst_m = re.search(r"operation\s+of\s+([^\n,]+?),?\s*hereinafter", text, re.IGNORECASE)
        if inst_m:
            fields.append(ExtractedField(
                field_name="institution_name",
                field_value=inst_m.group(1).strip(),
                confidence=0.90,
                source_document=filename,
                extraction_method="layout_context"
            ))

        # 6. Sponsoring Society / Trust Name
        trust_m = re.search(r"sponsoring\s+body\s+([^\n,]+?),?\s*for\s+the\s+establishment", text, re.IGNORECASE)
        if not trust_m:
            trust_m = re.search(r"(?:Sponsoring\s*Society|Trust|Sponsoring\s*Body)\s*[:\-]?\s*([^\n,]+)", text, re.IGNORECASE)
        if trust_m:
            fields.append(ExtractedField(
                field_name="society_trust_name",
                field_value=trust_m.group(1).strip(),
                confidence=0.92,
                source_document=filename,
                extraction_method="layout_context"
            ))

        return fields

    def extract_from_building_plan(self, text: str, filename: str) -> List[ExtractedField]:
        """Extract fields from Building Plan Approval."""
        fields = []

        # 1. Sanction Order Number
        m = self.bplan_sanct_regex.search(text)
        if m:
            fields.append(ExtractedField(
                field_name="approval_number",
                field_value=m.group(1).strip(),
                confidence=0.98,
                source_document=filename,
                extraction_method="regex"
            ))

        # 2. Institution Name
        inst_m = re.search(r"Institution\s*Name\s*[:\-]?\s*([^\n]+)", text, re.IGNORECASE)
        if inst_m:
            fields.append(ExtractedField(
                field_name="institution_name",
                field_value=inst_m.group(1).strip(),
                confidence=0.95,
                source_document=filename,
                extraction_method="regex"
            ))

        # 3. Survey Reference
        m = re.search(r"(?:Survey\s*/\s*Plot\s*Reference|on\s+plot\s+bearing)\s*[:\-]?\s*([A-Za-z0-9\-/\s]+?)(?:\.|\n|<)", text, re.IGNORECASE)
        if m:
            fields.append(ExtractedField(
                field_name="survey_number",
                field_value=m.group(1).strip(),
                confidence=0.94,
                source_document=filename,
                extraction_method="regex"
            ))

        # 4. Built-up Area
        m = self.sqm_regex.search(text)
        if m:
            raw_val = m.group(1).replace(",", "")
            fields.append(ExtractedField(
                field_name="built_up_area_sqm",
                field_value=float(raw_val),
                confidence=0.95,
                source_document=filename,
                extraction_method="regex"
            ))

        # 5. Architect License
        m = re.search(r"Architect\s*License\s*[:\-]?\s*([^\n]+)", text, re.IGNORECASE)
        if m:
            fields.append(ExtractedField(
                field_name="architect_license",
                field_value=m.group(1).strip(),
                confidence=0.96,
                source_document=filename,
                extraction_method="regex"
            ))

        # 6. Dates (Sanction Date & Expiry Date)
        m_sanc = re.search(r"Sanction\s*Date\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
        if m_sanc:
            fields.append(ExtractedField(
                field_name="approval_date",
                field_value=m_sanc.group(1).strip(),
                confidence=0.95,
                source_document=filename,
                extraction_method="regex"
            ))

        m_exp = re.search(r"(?:Validity\s*/\s*Expiry\s*Date|Expiry\s*Date)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
        if m_exp:
            fields.append(ExtractedField(
                field_name="expiry_date",
                field_value=m_exp.group(1).strip(),
                confidence=0.95,
                source_document=filename,
                extraction_method="regex"
            ))

        return fields

    def extract_from_fire_noc(self, text: str, filename: str) -> List[ExtractedField]:
        """Extract fields from Fire Safety NOC."""
        fields = []

        # 1. NOC Certificate Number
        m = self.noc_regex.search(text)
        if m:
            fields.append(ExtractedField(
                field_name="noc_number",
                field_value=m.group(1).strip(),
                confidence=0.98,
                source_document=filename,
                extraction_method="regex"
            ))

        # 2. Institution Name
        inst_m = re.search(r"Certified\s*Institution\s*[:\-]?\s*([^\n]+)", text, re.IGNORECASE)
        if inst_m:
            fields.append(ExtractedField(
                field_name="institution_name",
                field_value=inst_m.group(1).strip(),
                confidence=0.95,
                source_document=filename,
                extraction_method="regex"
            ))

        # 3. Dates (Issue and Expiry)
        m_issue = re.search(r"(?:Date\s*of\s*Issuance|inspected\s*on)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
        if m_issue:
            fields.append(ExtractedField(
                field_name="issue_date",
                field_value=m_issue.group(1).strip(),
                confidence=0.96,
                source_document=filename,
                extraction_method="regex"
            ))

        m_exp = re.search(r"(?:Valid\s*Until\s*\(Expiry\s*Date\)|valid\s*until)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
        if m_exp:
            fields.append(ExtractedField(
                field_name="expiry_date",
                field_value=m_exp.group(1).strip(),
                confidence=0.96,
                source_document=filename,
                extraction_method="regex"
            ))

        return fields

    def extract_from_mandatory_disclosure(self, text: str, filename: str) -> List[ExtractedField]:
        """Extract fields from Mandatory Disclosure."""
        fields = []

        # 1. Institution Name
        m = re.search(r"Name\s*of\s*the\s*Institution\s*[:\-]?\s*([^\n]+)", text, re.IGNORECASE)
        if m:
            fields.append(ExtractedField(
                field_name="institution_name",
                field_value=m.group(1).strip(),
                confidence=0.98,
                source_document=filename,
                extraction_method="regex"
            ))

        # 2. Sponsoring Society/Trust
        m = re.search(r"Sponsoring\s*Society\s*/\s*Trust\s*[:\-]?\s*([^\n]+)", text, re.IGNORECASE)
        if m:
            fields.append(ExtractedField(
                field_name="society_trust_name",
                field_value=m.group(1).strip(),
                confidence=0.95,
                source_document=filename,
                extraction_method="regex"
            ))

        # 3. Land Area in Acres
        m = re.search(r"Total\s*Campus\s*Land\s*Area\s*\(Acres\)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*Acres?", text, re.IGNORECASE)
        if m:
            fields.append(ExtractedField(
                field_name="land_area_acres",
                field_value=float(m.group(1)),
                confidence=0.99,
                source_document=filename,
                extraction_method="regex"
            ))

        # 4. Survey Number
        m = re.search(r"Survey\s*/\s*Khasra\s*Number\s*[:\-]?\s*([^\n]+)", text, re.IGNORECASE)
        if m:
            fields.append(ExtractedField(
                field_name="survey_number",
                field_value=m.group(1).strip(),
                confidence=0.96,
                source_document=filename,
                extraction_method="regex"
            ))

        # 5. Fire NOC Reference
        m = re.search(r"Fire\s*Safety\s*NOC\s*Reference\s*[:\-]?\s*([^\n]+)", text, re.IGNORECASE)
        if m:
            fields.append(ExtractedField(
                field_name="fire_noc_number",
                field_value=m.group(1).strip(),
                confidence=0.97,
                source_document=filename,
                extraction_method="regex"
            ))

        # 6. Applied Intake
        m = self.intake_regex.search(text)
        if m:
            fields.append(ExtractedField(
                field_name="applied_intake",
                field_value=int(m.group(1)),
                confidence=0.98,
                source_document=filename,
                extraction_method="regex"
            ))

        return fields

    def extract_document_fields(self, doc_type: DocumentType, text: str, filename: str) -> List[ExtractedField]:
        """Dispatch extraction by document type."""
        if doc_type == DocumentType.LAND_TITLE:
            return self.extract_from_land_title(text, filename)
        elif doc_type == DocumentType.BUILDING_PLAN:
            return self.extract_from_building_plan(text, filename)
        elif doc_type == DocumentType.FIRE_NOC:
            return self.extract_from_fire_noc(text, filename)
        elif doc_type == DocumentType.MANDATORY_DISCLOSURE:
            return self.extract_from_mandatory_disclosure(text, filename)
        return []

    def compute_string_similarity(self, s1: str, s2: str) -> float:
        """RapidFuzz token set ratio for robust fuzzy string similarity."""
        if not s1 or not s2:
            return 0.0
        return fuzz.token_sort_ratio(s1.lower(), s2.lower()) / 100.0
