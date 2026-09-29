"""Deterministic risk scoring.

The score is an additive sum of fixed weights over the compliance matrix. Reasons are
generated from the actual failing rows, so two different cases produce two different
explanations.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import AuditEventType, ComplianceStatus, RiskLevel
from ..models import (
    ComplianceResult,
    Requirement,
    RiskAssessment,
    Verification,
    VerificationResult,
)
from .audit import AuditService
from .fixtures import (
    RISK_BANDS,
    RISK_RATIO_THRESHOLD,
    RISK_WEIGHT_FAIL,
    RISK_WEIGHT_LOW_VERIFIED_RATIO,
    RISK_WEIGHT_MISSING_MANDATORY,
    RISK_WEIGHT_REVIEW,
)


def _band_for(score: float) -> str:
    for floor, level in RISK_BANDS:
        if score >= floor:
            return level
    return RiskLevel.LOW.value


def assess_risk(
    db: Session, audit: AuditService, verification: Verification
) -> tuple[RiskAssessment, list[dict]]:
    """Compute (or recompute) the risk assessment for a case.

    Returns the assessment row plus the list of contributing signals. Idempotent:
    an unchanged case is not re-audited and keeps its original ``computed_at``.
    """
    compliance = db.scalars(
        select(ComplianceResult).where(ComplianceResult.verification_id == verification.id)
    ).all()
    requirements = db.scalars(
        select(Requirement).where(Requirement.verification_id == verification.id)
    ).all()
    results = db.scalars(
        select(VerificationResult).where(VerificationResult.verification_id == verification.id)
    ).all()

    mandatory_by_id = {r.id: r for r in requirements}
    title_by_id = {r.id: r.title for r in requirements}
    result_by_requirement = {r.requirement_id: r for r in results}

    total = len(compliance)
    verified = sum(1 for r in compliance if r.status == ComplianceStatus.PASS.value)
    ratio = (verified / total) if total else 0.0

    score = 0.0
    reasons: list[str] = []
    signals: list[dict] = []

    failed_rows = [c for c in compliance if c.status == ComplianceStatus.FAIL.value]
    review_rows = [c for c in compliance if c.status == ComplianceStatus.REVIEW.value]
    missing_mandatory = [
        c
        for c in compliance
        if c.requirement_id in result_by_requirement
        and result_by_requirement[c.requirement_id].status == "MISSING"
        and mandatory_by_id.get(c.requirement_id, None) is not None
        and mandatory_by_id[c.requirement_id].is_mandatory
    ]

    if failed_rows:
        score += RISK_WEIGHT_FAIL
        names = ", ".join(title_by_id.get(c.requirement_id, "requirement") for c in failed_rows)
        reasons.append(f"Non-compliant mandatory requirement(s): {names}.")
        signals.append(
            {
                "code": "NON_COMPLIANT_REQUIREMENTS",
                "message": f"{len(failed_rows)} requirement(s) failed compliance.",
                "weight": RISK_WEIGHT_FAIL,
            }
        )

    if review_rows:
        score += RISK_WEIGHT_REVIEW
        names = ", ".join(title_by_id.get(c.requirement_id, "requirement") for c in review_rows)
        reasons.append(f"Requirement(s) needing officer judgement: {names}.")
        signals.append(
            {
                "code": "REVIEW_REQUIRED",
                "message": f"{len(review_rows)} requirement(s) need officer judgement.",
                "weight": RISK_WEIGHT_REVIEW,
            }
        )

    if missing_mandatory:
        score += RISK_WEIGHT_MISSING_MANDATORY
        names = ", ".join(
            title_by_id.get(c.requirement_id, "requirement") for c in missing_mandatory
        )
        reasons.append(f"Evidence incomplete — document not submitted for: {names}.")
        signals.append(
            {
                "code": "MISSING_EVIDENCE",
                "message": f"Mandatory document(s) not submitted for {len(missing_mandatory)} requirement(s).",
                "weight": RISK_WEIGHT_MISSING_MANDATORY,
            }
        )

    if total and ratio < RISK_RATIO_THRESHOLD:
        score += RISK_WEIGHT_LOW_VERIFIED_RATIO
        reasons.append(
            f"Only {verified} of {total} requirements verified "
            f"({ratio * 100:.1f}%, below the {RISK_RATIO_THRESHOLD * 100:.0f}% threshold)."
        )
        signals.append(
            {
                "code": "LOW_VERIFIED_RATIO",
                "message": (
                    f"Only {verified} of {total} requirements verified "
                    f"({ratio * 100:.1f}%), below the "
                    f"{RISK_RATIO_THRESHOLD * 100:.0f}% threshold."
                ),
                "weight": RISK_WEIGHT_LOW_VERIFIED_RATIO,
            }
        )

    if review_rows or failed_rows:
        reasons.append("Officer review required before a final decision can be recorded.")

    score = max(0.0, min(100.0, score))
    level = _band_for(score)

    assessment = db.scalars(
        select(RiskAssessment).where(RiskAssessment.verification_id == verification.id)
    ).first()
    if assessment is None:
        assessment = RiskAssessment(verification_id=verification.id)
        db.add(assessment)
        changed = True
    else:
        changed = (
            assessment.level != level
            or assessment.score != score
            or list(assessment.reasons or []) != reasons
            or assessment.verified_count != verified
            or assessment.total_count != total
        )

    assessment.level = level
    assessment.score = score
    assessment.reasons = reasons
    assessment.verified_count = verified
    assessment.total_count = total
    if changed:
        assessment.computed_at = datetime.now(timezone.utc)

    db.flush()

    if changed:
        audit.record(
            verification.id,
            AuditEventType.RISK_CALCULATED,
            f"Risk assessed as {level} (score {score:.0f}).",
            stage="Risk",
            metadata={"level": level, "score": score, "reasons": reasons},
        )
    return assessment, signals
