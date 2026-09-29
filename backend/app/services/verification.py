"""Deterministic verification rules.

IMPORTANT: this module deliberately imports **no HTTP client**. GST, PAN and Udyam are
checked with local structural rules only — no government registry is contacted. Every
result therefore records ``LOCAL_RULE_SOURCE`` so the UI and the audit trail cannot
imply otherwise.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import (
    AuditEventType,
    VerificationMethod,
    VerificationOutcome,
)
from ..models import (
    ExtractedField,
    Requirement,
    Verification,
    VerificationResult,
)
from .audit import AuditService

#: Human-readable provenance attached to every result.
LOCAL_RULE_SOURCE = "LOCAL_RULE (no government API)"

#: Structural checks only. These validate *shape*, not registry authenticity.
#: GSTIN: 2-digit state code + 11 alphanumerics (PAN + entity number) + 'Z' + checksum.
#: Masked values (e.g. "37XXXXXXXXXX1Z5") are accepted because tender documents
#: routinely redact the PAN segment.
_GSTIN_SHAPE = re.compile(r"^\d{2}[A-Z0-9]{11}Z[0-9A-Z]$", re.I)
_PAN_SHAPE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$", re.I)
_UDYAM_SHAPE = re.compile(r"^UDYAM[-\s][A-Z]{2}[-\s][A-Z0-9]{2}[-\s][A-Z0-9]{4,7}$", re.I)

_SHAPES: dict[str, re.Pattern[str]] = {
    "GSTIN": _GSTIN_SHAPE,
    "PAN": _PAN_SHAPE,
    "Udyam Number": _UDYAM_SHAPE,
}


@dataclass(frozen=True)
class Outcome:
    status: VerificationOutcome
    method: VerificationMethod
    detail: str
    observed_value: str
    source: str = LOCAL_RULE_SOURCE


def check_value(field_name: str, value: str, method: VerificationMethod, threshold: float | None) -> Outcome:
    """Evaluate one extracted value against a requirement's rule."""
    cleaned = (value or "").strip()

    if not cleaned:
        return Outcome(
            VerificationOutcome.MISSING,
            VerificationMethod.PRESENCE,
            f"No value was extracted for '{field_name}'.",
            "",
        )

    if method is VerificationMethod.PRESENCE:
        return Outcome(
            VerificationOutcome.VERIFIED,
            VerificationMethod.PRESENCE,
            f"'{field_name}' is present in the submitted evidence.",
            cleaned,
        )

    if method is VerificationMethod.FORMAT_CHECK:
        shape = _SHAPES.get(field_name)
        if shape is None:
            return Outcome(
                VerificationOutcome.VERIFIED,
                VerificationMethod.FORMAT_CHECK,
                f"'{field_name}' present; no structural rule defined.",
                cleaned,
            )
        if shape.match(cleaned):
            return Outcome(
                VerificationOutcome.VERIFIED,
                VerificationMethod.FORMAT_CHECK,
                f"'{cleaned}' matches the expected {field_name} structure.",
                cleaned,
            )
        return Outcome(
            VerificationOutcome.INVALID,
            VerificationMethod.FORMAT_CHECK,
            f"'{cleaned}' does not match the expected {field_name} structure.",
            cleaned,
        )

    # THRESHOLD
    try:
        numeric = float(cleaned.replace(",", "").strip())
    except ValueError:
        return Outcome(
            VerificationOutcome.INVALID,
            VerificationMethod.THRESHOLD,
            f"'{cleaned}' is not a numeric value and cannot be compared to the threshold.",
            cleaned,
        )

    if threshold is None:
        return Outcome(
            VerificationOutcome.VERIFIED,
            VerificationMethod.THRESHOLD,
            f"Observed {cleaned:g}; no threshold defined for this requirement.",
            cleaned,
        )
    if numeric >= threshold:
        return Outcome(
            VerificationOutcome.VERIFIED,
            VerificationMethod.THRESHOLD,
            f"Observed {numeric:,.0f} meets the required minimum {threshold:,.0f}.",
            cleaned,
        )
    return Outcome(
        VerificationOutcome.INVALID,
        VerificationMethod.THRESHOLD,
        f"Observed {numeric:,.0f} is below the required minimum {threshold:,.0f}.",
        cleaned,
    )


#: Kept in one place so verification reads like the requirement catalogue.
_METHOD_BY_CODE: dict[str, VerificationMethod] = {
    "GST_REGISTRATION": VerificationMethod.FORMAT_CHECK,
    "PAN": VerificationMethod.FORMAT_CHECK,
    "UDYAM_REGISTRATION": VerificationMethod.FORMAT_CHECK,
    "OEM_AUTHORIZATION": VerificationMethod.PRESENCE,
    "MINIMUM_EXPERIENCE": VerificationMethod.THRESHOLD,
    "TURNOVER": VerificationMethod.THRESHOLD,
    "TECHNICAL_SPECIFICATION": VerificationMethod.PRESENCE,
    "FINANCIAL_ELIGIBILITY": VerificationMethod.THRESHOLD,
}

_FIELD_BY_CODE: dict[str, str] = {
    "GST_REGISTRATION": "GSTIN",
    "PAN": "PAN",
    "UDYAM_REGISTRATION": "Udyam Number",
    "OEM_AUTHORIZATION": "OEM Reference",
    "MINIMUM_EXPERIENCE": "Years of Experience",
    "TURNOVER": "Annual Turnover",
    "TECHNICAL_SPECIFICATION": "Technical Compliance",
    "FINANCIAL_ELIGIBILITY": "Net Worth",
}


def run_verification(
    db: Session, audit: AuditService, verification: Verification
) -> tuple[int, int, int]:
    """Recompute verification results for every requirement.

    Returns ``(results, verified, missing)``. Idempotent: existing rows are replaced.
    """
    requirements = db.scalars(
        select(Requirement)
        .where(Requirement.verification_id == verification.id)
        .order_by(Requirement.sort_order)
    ).all()
    if not requirements:
        return 0, 0, 0

    fields = db.scalars(
        select(ExtractedField).where(ExtractedField.verification_id == verification.id)
    ).all()

    # field_name -> extracted field (first match wins; ids are insertion-ordered)
    by_name: dict[str, ExtractedField] = {}
    field_docs: dict[str, int] = {}
    for item in fields:
        by_name.setdefault(item.field_name, item)
        field_docs.setdefault(item.field_name, item.document_id)

    for stale in db.scalars(
        select(VerificationResult).where(VerificationResult.verification_id == verification.id)
    ).all():
        db.delete(stale)
    db.flush()

    verified = 0
    missing = 0

    for requirement in requirements:
        field_name = _FIELD_BY_CODE.get(requirement.code, requirement.title)
        method = _METHOD_BY_CODE.get(requirement.code, VerificationMethod.PRESENCE)
        extracted = by_name.get(field_name)

        if extracted is None:
            outcome = Outcome(
                VerificationOutcome.MISSING,
                method,
                f"Required evidence for '{requirement.title}' was not submitted.",
                "",
            )
            missing += 1
            doc_id = None
            field_id = None
        else:
            outcome = check_value(
                field_name, extracted.field_value, method, requirement.threshold_value
            )
            doc_id = field_docs.get(field_name)
            field_id = extracted.id
            if outcome.status is VerificationOutcome.VERIFIED:
                verified += 1

        db.add(
            VerificationResult(
                verification_id=verification.id,
                requirement_id=requirement.id,
                extracted_field_id=field_id,
                document_id=doc_id,
                status=outcome.status.value,
                method=outcome.method.value,
                detail=outcome.detail,
                observed_value=outcome.observed_value,
                source=outcome.source,
                verified_by="SYSTEM",
            )
        )

        if outcome.status is VerificationOutcome.VERIFIED:
            audit.record(
                verification.id,
                AuditEventType.FIELD_VERIFIED,
                f"{requirement.title} verified ({outcome.method.value}).",
                stage="Verification",
                metadata={
                    "requirement": requirement.code,
                    "method": outcome.method.value,
                    "source": outcome.source,
                },
            )
        elif outcome.status is VerificationOutcome.MISSING:
            audit.record(
                verification.id,
                AuditEventType.DOCUMENT_MISSING,
                f"{requirement.title} evidence missing.",
                stage="Verification",
                metadata={"requirement": requirement.code},
            )

    db.flush()

    audit.record(
        verification.id,
        AuditEventType.VERIFICATION_COMPLETED,
        f"Verification completed: {verified} verified, {missing} missing "
        f"of {len(requirements)} requirement(s).",
        stage="Verification",
        metadata={"verified": verified, "missing": missing, "total": len(requirements)},
    )
    return len(requirements), verified, missing
