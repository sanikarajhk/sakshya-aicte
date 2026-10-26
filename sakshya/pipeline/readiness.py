"""
Sakshya Institution Pre-Submission Readiness Check
Computes deterministic readiness score using an explicit checklist formula.
Transparently evaluates missing documents, expiry issues, and inconsistencies.
NOTE: This score represents regulatory checklist completeness, NOT probability of approval.
"""

from typing import List, Dict, Any
from sakshya.core.models import ReadinessResult, ReadinessItem, Finding, VerificationStatus


class ReadinessEvaluator:
    """Pre-submission validator helping institutions submit complete, compliant dossiers."""

    def evaluate_readiness(
        self,
        application_data: Dict[str, Any],
        documents: List[Dict[str, Any]],
        findings: List[Finding],
        issuer_statuses: List[VerificationStatus]
    ) -> ReadinessResult:
        """
        Evaluate statutory checklist items with fixed weights:
        Total Weight = 100
        Formula: Score = (Sum(Passed Weight) / Sum(Total Weight)) * 100
        """
        checklist = []
        present_types = {d.get("document_type") for d in documents}

        # 1. Mandatory Documents (Weight: 40)
        req_types = ["LAND_TITLE", "BUILDING_PLAN", "FIRE_NOC", "MANDATORY_DISCLOSURE"]
        for r in req_types:
            passed = r in present_types
            checklist.append(ReadinessItem(
                check_name=f"Mandatory Document: {r}",
                category="Mandatory Document",
                status=passed,
                score=10.0 if passed else 0.0,
                weight=10.0,
                details="Uploaded and indexed." if passed else "MISSING: Required statutory document not uploaded."
            ))

        # 2. Expiry Status (Weight: 20)
        has_expired = any("EXPIRED" in f.code for f in findings)
        checklist.append(ReadinessItem(
            check_name="Statutory Certificate Validity",
            category="Validity",
            status=not has_expired,
            score=20.0 if not has_expired else 0.0,
            weight=20.0,
            details="All submitted certificates are within validity window." if not has_expired else "EXPIRED: One or more certificates have lapsed."
        ))

        # 3. Cross-Document Consistency (Weight: 20)
        has_contradictions = any(f.is_contradiction for f in findings)
        checklist.append(ReadinessItem(
            check_name="Cross-Document Concordance",
            category="Consistency",
            status=not has_contradictions,
            score=20.0 if not has_contradictions else 0.0,
            weight=20.0,
            details="Extracted figures and titles agree across documents." if not has_contradictions else "CONTRADICTION: Conflicting land, survey, or name values found across documents."
        ))

        # 4. Authority Pre-Validation (Weight: 20)
        authority_passed = not any(s in (VerificationStatus.MISMATCH_DETECTED, VerificationStatus.MANUAL_REVIEW_REQUIRED) for s in issuer_statuses)
        checklist.append(ReadinessItem(
            check_name="Issuing Authority Record Concordance",
            category="Verification",
            status=authority_passed,
            score=20.0 if authority_passed else 0.0,
            weight=20.0,
            details="Mock authority pre-check indicates records align." if authority_passed else "ATTENTION: Authority records report mismatch or active encumbrance caveat."
        ))

        total_weight = sum(item.weight for item in checklist)
        earned_score = sum(item.score for item in checklist)
        final_score = round((earned_score / total_weight) * 100.0, 1)

        is_ready = final_score >= 80.0 and not has_contradictions and not has_expired

        if is_ready:
            summary = "Application satisfies readiness checklist and is ready for formal regulatory submission."
        else:
            summary = "Application dossier has unresolved checklist deficiencies. Please address flagged items before submission."

        return ReadinessResult(
            readiness_score=final_score,
            is_ready_for_submission=is_ready,
            summary=summary,
            checklist=checklist
        )
