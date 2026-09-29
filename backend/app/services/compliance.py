"""Compliance matrix built from stored verification results.

Every status here is derived: AI extraction + deterministic rules + verification.
Nothing is hard-coded to a particular case.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import AuditEventType, ComplianceStatus, VerificationOutcome
from ..models import (
    ComplianceResult,
    Requirement,
    Verification,
    VerificationResult,
)
from .audit import AuditService

_PASSING = {VerificationOutcome.VERIFIED.value}
_FAILING = {VerificationOutcome.INVALID.value, VerificationOutcome.MISMATCH.value}


def compute_compliance(
    db: Session, audit: AuditService, verification: Verification
) -> list[ComplianceResult]:
    """Recompute the matrix. Idempotent via the unique (verification, requirement) key."""
    requirements = db.scalars(
        select(Requirement)
        .where(Requirement.verification_id == verification.id)
        .order_by(Requirement.sort_order)
    ).all()

    results = db.scalars(
        select(VerificationResult).where(VerificationResult.verification_id == verification.id)
    ).all()
    by_requirement: dict[int, VerificationResult] = {r.requirement_id: r for r in results}

    existing = {
        c.requirement_id: c
        for c in db.scalars(
            select(ComplianceResult).where(ComplianceResult.verification_id == verification.id)
        ).all()
    }

    rows: list[ComplianceResult] = []
    any_changed = False
    for requirement in requirements:
        result = by_requirement.get(requirement.id)
        status, reason, evidence = _decide(requirement, result)

        row = existing.get(requirement.id)
        if row is None:
            row = ComplianceResult(
                verification_id=verification.id, requirement_id=requirement.id
            )
            db.add(row)
            any_changed = True
        elif row.status != status.value or row.reason != reason or row.evidence_ref != evidence:
            # The matrix really changed: refresh when it was last computed.
            row.computed_at = datetime.now(timezone.utc)
            any_changed = True

        row.status = status.value
        row.reason = reason
        row.evidence_ref = evidence
        rows.append(row)

    db.flush()

    pass_count = sum(1 for r in rows if r.status == ComplianceStatus.PASS.value)
    review_count = sum(1 for r in rows if r.status == ComplianceStatus.REVIEW.value)
    fail_count = sum(1 for r in rows if r.status == ComplianceStatus.FAIL.value)

    if any_changed:
        audit.record(
            verification.id,
            AuditEventType.COMPLIANCE_CALCULATED,
            f"Compliance matrix computed: {pass_count} pass, {review_count} review, "
            f"{fail_count} fail of {len(rows)} requirement(s).",
            stage="Compliance",
            metadata={"pass": pass_count, "review": review_count, "fail": fail_count},
        )
    return rows


def _decide(
    requirement: Requirement, result: VerificationResult | None
) -> tuple[ComplianceStatus, str, str]:
    """Map a verification result onto a compliance status."""
    if result is None:
        if requirement.is_mandatory:
            return (
                ComplianceStatus.REVIEW,
                "No verification result was produced for this mandatory requirement.",
                "",
            )
        return (ComplianceStatus.NOT_APPLICABLE, "Optional requirement; not evaluated.", "")

    evidence = result.observed_value or ""
    if evidence:
        evidence = f"{result.method}: {evidence}"

    if result.status in _FAILING:
        return (ComplianceStatus.FAIL, result.detail or "Requirement not satisfied.", evidence)

    if result.status == VerificationOutcome.MISSING.value:
        return (
            ComplianceStatus.REVIEW,
            "Required document not submitted — officer judgement required.",
            evidence,
        )

    if result.status == VerificationOutcome.NOT_VERIFIED.value:
        return (ComplianceStatus.REVIEW, "Verification not completed.", evidence)

    if result.status in _PASSING:
        return (ComplianceStatus.PASS, result.detail or "Requirement satisfied.", evidence)

    return (ComplianceStatus.REVIEW, result.detail or "Unrecognised verification status.", evidence)
