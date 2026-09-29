"""Evidence chain: Bidder -> Document -> Extracted Data -> Verification ->
Requirement -> Compliance Result.

Every level is built from rows that actually exist for the case.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import ComplianceStatus
from ..models import (
    Bidder,
    ComplianceResult,
    Document,
    ExtractedField,
    Requirement,
    Verification,
    VerificationResult,
)


def build_evidence(db: Session, verification: Verification) -> dict:
    """Return the 6-level chain plus one chain row per extracted field."""
    bidder = verification.bidder
    documents = db.scalars(
        select(Document)
        .where(Document.verification_id == verification.id)
        .order_by(Document.id)
    ).all()
    fields = db.scalars(
        select(ExtractedField)
        .where(ExtractedField.verification_id == verification.id)
        .order_by(ExtractedField.id)
    ).all()
    results = db.scalars(
        select(VerificationResult)
        .where(VerificationResult.verification_id == verification.id)
        .order_by(VerificationResult.id)
    ).all()
    requirements = db.scalars(
        select(Requirement)
        .where(Requirement.verification_id == verification.id)
        .order_by(Requirement.sort_order)
    ).all()

    compliance = db.scalars(
        select(ComplianceResult).where(ComplianceResult.verification_id == verification.id)
    ).all()

    result_by_field: dict[int, VerificationResult] = {}
    for item in results:
        if item.extracted_field_id is not None:
            result_by_field.setdefault(item.extracted_field_id, item)

    requirement_by_id = {r.id: r for r in requirements}
    compliance_by_requirement = {c.requirement_id: c for c in compliance}
    document_by_id = {d.id: d for d in documents}

    chains = []
    for item in fields:
        result = result_by_field.get(item.id)
        document = document_by_id.get(item.document_id)
        requirement = requirement_by_id.get(result.requirement_id) if result else None
        compliance_row = (
            compliance_by_requirement.get(result.requirement_id) if result else None
        )
        # An extracted field that maps to no requirement is informational. Reporting it
        # as REVIEW would invent an exception that does not exist.
        if compliance_row is not None:
            compliance_status = compliance_row.status
            compliance_reason = compliance_row.reason
        else:
            compliance_status = ComplianceStatus.NOT_APPLICABLE.value
            compliance_reason = "Not linked to a tender requirement — informational only."

        chains.append(
            {
                "document_id": item.document_id,
                "document_label": document.label if document else "",
                "doc_type": document.doc_type if document else "",
                "field_name": item.field_name,
                "field_value": item.field_value,
                "confidence": item.confidence,
                "requirement_code": requirement.code if requirement else "",
                "requirement_title": requirement.title if requirement else "Not linked to a requirement",
                "verification_status": result.status if result else "NOT_LINKED",
                "verification_detail": result.detail if result else "",
                "compliance_status": compliance_status,
                "compliance_reason": compliance_reason,
            }
        )

    pass_count = sum(1 for c in compliance if c.status == ComplianceStatus.PASS.value)
    levels = [
        {
            "level": 1,
            "entity": "Bidder",
            "label": "Bidder",
            "title": bidder.name if bidder else "No bidder assigned",
            "detail": f"Bidder record #{bidder.id}" if bidder else "",
            "status": None,
            "ref_id": bidder.id if bidder else None,
        },
        {
            "level": 2,
            "entity": "Document",
            "label": "Submitted documents",
            "title": f"{len(documents)} document(s) on record",
            "detail": ", ".join(d.label for d in documents) if documents else "None submitted",
            "status": None,
            "ref_id": None,
        },
        {
            "level": 3,
            "entity": "ExtractedData",
            "label": "Extracted fields",
            "title": f"{len(fields)} field(s) extracted",
            "detail": ", ".join(f"{f.field_name}={f.field_value}" for f in fields[:4])
            or "No extraction performed",
            "status": None,
            "ref_id": None,
        },
        {
            "level": 4,
            "entity": "Verification",
            "label": "Verification results",
            "title": f"{len(results)} check(s) executed",
            "detail": ", ".join(
                sorted({r.source for r in results})
            )
            or "Verification not run",
            "status": None,
            "ref_id": None,
        },
        {
            "level": 5,
            "entity": "Requirement",
            "label": "Tender requirements",
            "title": f"{len(requirements)} requirement(s) from tender",
            "detail": ", ".join(r.title for r in requirements[:4]),
            "status": None,
            "ref_id": None,
        },
        {
            "level": 6,
            "entity": "ComplianceResult",
            "label": "Compliance result",
            "title": f"{pass_count} of {len(compliance)} requirement(s) pass",
            "detail": "Final compliance position for this verification",
            "status": ComplianceStatus.PASS.value if pass_count == len(compliance) and compliance else ComplianceStatus.REVIEW.value,
            "ref_id": None,
        },
    ]

    return {
        "verification_id": verification.id,
        "bidder": (
            {
                "id": bidder.id,
                "name": bidder.name,
                "code": bidder.code,
                "document_count": len(documents),
            }
            if bidder
            else None
        ),
        "levels": levels,
        "chains": chains,
        "compliance_status": levels[-1]["status"],
    }
