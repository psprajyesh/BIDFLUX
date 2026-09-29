"""Rule-based AI recommendation.

The wording is templated, but the conclusion is computed from the stored compliance and
risk rows. There is deliberately **no** code path that recommends approval as a final
outcome — the officer always disposes.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import AuditEventType, ComplianceStatus, RiskLevel
from ..models import ComplianceResult, Requirement, RiskAssessment, Verification
from .audit import AuditService

CODE_REVIEW = "REQUIRES_OFFICER_REVIEW"
CODE_ELIGIBLE = "ELIGIBLE_PENDING_OFFICER_CONFIRMATION"

BLOCKING_RISK = {RiskLevel.HIGH.value, RiskLevel.CRITICAL.value}


def build_recommendation(
    db: Session, audit: AuditService, verification: Verification
) -> dict:
    """Return the recommendation payload for a case (and audit it once)."""
    risk = db.scalars(
        select(RiskAssessment).where(RiskAssessment.verification_id == verification.id)
    ).first()
    if risk is None:
        from ..errors import ConflictError

        raise ConflictError("Assess risk before requesting a recommendation.")

    compliance = db.scalars(
        select(ComplianceResult).where(ComplianceResult.verification_id == verification.id)
    ).all()
    requirements = db.scalars(
        select(Requirement).where(Requirement.verification_id == verification.id)
    ).all()
    title_by_id = {r.id: r.title for r in requirements}

    review_rows = [c for c in compliance if c.status == ComplianceStatus.REVIEW.value]
    fail_rows = [c for c in compliance if c.status == ComplianceStatus.FAIL.value]
    pass_count = sum(1 for c in compliance if c.status == ComplianceStatus.PASS.value)

    blocking = bool(review_rows or fail_rows or risk.level in BLOCKING_RISK)

    if blocking:
        code = CODE_REVIEW
        headline = "REQUIRES OFFICER REVIEW"
        rationale: list[str] = [
            f"Automated analysis recommends human review; risk is {risk.level} "
            f"(score {risk.score:.0f})."
        ]
        if review_rows:
            names = ", ".join(title_by_id.get(c.requirement_id, "requirement") for c in review_rows)
            rationale.append(f"Requirements needing officer judgement: {names}.")
        if fail_rows:
            names = ", ".join(title_by_id.get(c.requirement_id, "requirement") for c in fail_rows)
            rationale.append(f"Requirements not satisfied: {names}.")
        if not pass_count:
            rationale.append("No requirement could be confirmed from the submitted evidence.")
        rationale.extend(risk.reasons or [])
        rationale.append(
            "This is an advisory output only. The final decision rests with the reviewing officer."
        )
    else:
        code = CODE_ELIGIBLE
        headline = "ALL REQUIREMENTS SATISFIED — OFFICER CONFIRMATION REQUIRED"
        rationale = [
            f"All {risk.total_count} requirement(s) are marked pass; risk is {risk.level}.",
            "Automated analysis found no blocking exception.",
            "An officer must still confirm before the case can be closed.",
        ]

    already_logged = any(
        event.event_type == AuditEventType.RECOMMENDATION_GENERATED.value
        for event in verification.audit_events
    )
    if not already_logged:
        audit.record(
            verification.id,
            AuditEventType.RECOMMENDATION_GENERATED,
            f"Recommendation generated: {headline}",
            stage="Review",
            metadata={"code": code, "risk_level": risk.level, "mode": "RULE"},
        )

    return {
        "verification_id": verification.id,
        "code": code,
        "headline": headline,
        "rationale": rationale,
        "mode": "RULE",
        "risk_level": risk.level,
        "verified_count": risk.verified_count,
        "total_count": risk.total_count,
    }
