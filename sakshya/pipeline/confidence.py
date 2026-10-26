"""
Sakshya Confidence Evaluation & Status Routing Engine
Uses scikit-learn isotonic regression calibration to estimate reliable confidence
and automatically route applications to automated approval, officer review, or anomaly queue.
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sakshya.core.config import settings
from sakshya.core.models import (
    ApplicationStatus, VerificationStatus, Finding, FindingSeverity, ExtractedField
)


class ConfidenceRouter:
    """Evaluates multi-signal confidence and routes applications to human/AI workflows."""

    def __init__(self):
        self.calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        self._fit_calibrator_baseline()

    def _fit_calibrator_baseline(self):
        """
        Fit isotonic calibrator on canonical empirical calibration points.
        Maps raw composite feature scores to calibrated probabilities of documentary validity.
        """
        raw_scores = np.array([0.15, 0.30, 0.45, 0.60, 0.72, 0.85, 0.95, 1.0])
        calibrated_probs = np.array([0.05, 0.20, 0.40, 0.58, 0.70, 0.88, 0.97, 0.99])
        self.calibrator.fit(raw_scores, calibrated_probs)

    def calculate_raw_confidence(
        self,
        extracted_fields: List[ExtractedField],
        issuer_statuses: List[VerificationStatus],
        findings: List[Finding],
        ocr_confidence: float = 0.95
    ) -> float:
        """
        Compute weighted multi-signal heuristic score before calibration:
        - Extraction confidence (30%)
        - OCR & scan quality (20%)
        - Authority verification results (35%)
        - Severity of findings penalty (15%)
        """
        # 1. Extraction confidence
        if extracted_fields:
            avg_ext = np.mean([f.confidence for f in extracted_fields])
        else:
            avg_ext = 0.50

        # 2. Issuer score
        issuer_scores = []
        for s in issuer_statuses:
            if s == VerificationStatus.VERIFIED:
                issuer_scores.append(1.0)
            elif s in (VerificationStatus.VERIFICATION_PENDING, VerificationStatus.SOURCE_UNAVAILABLE):
                issuer_scores.append(0.5)
            elif s == VerificationStatus.MANUAL_REVIEW_REQUIRED:
                issuer_scores.append(0.3)
            else:  # MISMATCH or EXPIRED
                issuer_scores.append(0.0)

        avg_issuer = np.mean(issuer_scores) if issuer_scores else 0.5

        # 3. Findings penalty
        penalty = 0.0
        for f in findings:
            if f.severity == FindingSeverity.CRITICAL:
                penalty += 0.40
            elif f.severity == FindingSeverity.HIGH:
                penalty += 0.20
            elif f.severity == FindingSeverity.MEDIUM:
                penalty += 0.10

        findings_factor = max(0.0, 1.0 - penalty)

        raw_score = (
            0.30 * avg_ext +
            0.20 * ocr_confidence +
            0.35 * avg_issuer +
            0.15 * findings_factor
        )
        return float(np.clip(raw_score, 0.0, 1.0))

    def evaluate_routing(
        self,
        raw_confidence: float,
        findings: List[Finding],
        issuer_statuses: List[VerificationStatus],
        is_ring_member: bool = False
    ) -> Tuple[float, ApplicationStatus, str]:
        """
        Calibrate score and determine routing status:
        - VERIFIED_AUTO: High confidence, clean findings, verified authorities
        - FLAGGED_ANOMALY: Active contradictions, metadata tampering, or ring cluster
        - NEEDS_OFFICER_REVIEW: Missing docs, expired certs, low confidence, or pending/unavailable authority
        """
        calibrated_score = float(self.calibrator.predict([raw_confidence])[0])

        has_contradiction = any(f.is_contradiction for f in findings)
        has_critical = any(f.severity == FindingSeverity.CRITICAL for f in findings)
        has_anomaly = any(f.is_anomaly for f in findings)

        has_unverified_issuer = any(
            s in (
                VerificationStatus.MISMATCH_DETECTED,
                VerificationStatus.EXPIRED,
                VerificationStatus.SOURCE_UNAVAILABLE,
                VerificationStatus.MANUAL_REVIEW_REQUIRED,
                VerificationStatus.VERIFICATION_PENDING
            )
            for s in issuer_statuses
        )

        # Decision Tree Logic
        has_suspicious_alteration = any("SUSPICIOUS" in f.code or "METADATA" in f.code for f in findings)
        
        if has_contradiction or is_ring_member or has_suspicious_alteration or (has_anomaly and has_critical):
            status = ApplicationStatus.FLAGGED_ANOMALY
            reason = "Documentary contradiction, high-risk ring correlation, or critical alteration detected."
        elif has_critical or has_unverified_issuer or has_anomaly or calibrated_score < settings.CONFIDENCE_HIGH_THRESHOLD:
            status = ApplicationStatus.NEEDS_OFFICER_REVIEW
            reason = "Unresolved findings, pending/unavailable authority check, degraded scan, or confidence below automated threshold."
        else:
            status = ApplicationStatus.VERIFIED_AUTO
            reason = "High calibrated confidence (>0.85), all statutory checks passed, authorities verified."

        return round(calibrated_score, 3), status, reason
