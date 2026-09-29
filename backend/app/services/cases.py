"""Verification case lifecycle: creation, listing, aggregates and the officer decision."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..enums import (
    ActorType,
    AuditEventType,
    ComplianceStatus,
    DecisionType,
    ProcessingMode,
    RiskLevel,
    VerificationStatus,
)
from ..errors import NotFoundError
from ..models import (
    Bidder,
    ComplianceResult,
    Document,
    OfficerDecision,
    Requirement,
    RiskAssessment,
    Tender,
    Verification,
    VerificationResult,
)
from .audit import AuditService
from .storage import save_upload
from .workflow import compute_state

API_VERSION = "1.0.0"

CAPABILITIES: dict[str, str] = {
    "case_management": "real",
    "file_storage": "real",
    "compliance_rules": "real",
    "risk_scoring": "real",
    "audit_trail": "real",
    "evidence_chain": "real",
    "officer_decision": "real",
    "requirement_extraction": "mock",
    "document_ocr_extraction": "mock",
    "registry_verification": "mock (no government API)",
    "recommendation_text": "mock (rule-generated)",
}

CAPABILITY_NOTICE = (
    "Requirement extraction, document OCR and GST/PAN/Udyam registry checks are "
    "simulated for this demo. Compliance, risk and audit are computed from stored data."
)


# --------------------------------------------------------------------------- #
# IDs
# --------------------------------------------------------------------------- #


def next_verification_id(db: Session) -> str:
    """Monotonic per-year ID: VER-2026-000001."""
    year = datetime.now(timezone.utc).year
    prefix = f"VER-{year}-"
    highest = 0
    for row in db.scalars(
        select(Verification.id).where(Verification.id.like(f"{prefix}%"))
    ).all():
        try:
            highest = max(highest, int(row.rsplit("-", 1)[-1]))
        except ValueError:  # pragma: no cover - defensive
            continue
    return f"{prefix}{highest + 1:06d}"


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def create_verification(
    db: Session,
    audit: AuditService,
    *,
    title: str,
    tender_reference: str = "",
    tenderer: str = "",
    is_demo: bool = False,
) -> Verification:
    verification = Verification(
        id=next_verification_id(db),
        title=title,
        tender_reference=tender_reference,
        tenderer=tenderer,
        status=VerificationStatus.DRAFT.value,
        current_step="Tender",
        is_demo=is_demo,
    )
    db.add(verification)
    db.flush()

    # Every case carries exactly one bidder; created upfront so uploads always work.
    bidder = Bidder(verification_id=verification.id, name="Pending assignment", code="")
    db.add(bidder)
    db.flush()

    audit.record(
        verification.id,
        AuditEventType.VERIFICATION_CREATED,
        f"Verification {verification.id} created.",
        stage="Tender",
        metadata={"title": title, "tender_reference": tender_reference},
    )
    db.flush()
    return verification


def assign_bidder(db: Session, verification: Verification, name: str, code: str = "") -> Bidder:
    bidder = db.scalars(
        select(Bidder).where(Bidder.verification_id == verification.id)
    ).first()
    if bidder is None:
        bidder = Bidder(verification_id=verification.id, name=name, code=code)
        db.add(bidder)
    else:
        bidder.name = name
        bidder.code = code or bidder.code
    db.flush()
    return bidder


def attach_tender(
    db: Session,
    audit: AuditService,
    settings,
    verification: Verification,
    *,
    data: bytes,
    filename: str | None,
    content_type: str | None,
    reference_no: str,
    title: str,
) -> Tender:
    """Store a tender file and attach it to the case."""
    stored = save_upload(
        data, original_name=filename, content_type=content_type, settings=settings
    )
    tender = Tender(
        verification_id=verification.id,
        reference_no=reference_no,
        title=title,
        file_name=stored.original_name,
        stored_name=stored.stored_name,
        file_size=stored.size,
        content_type=stored.content_type,
        analysis_mode=ProcessingMode.RULE.value,
    )
    db.add(tender)
    db.flush()

    audit.record(
        verification.id,
        AuditEventType.TENDER_UPLOADED,
        f"Tender uploaded: {reference_no} ({stored.original_name}).",
        stage="Tender",
        metadata={"reference_no": reference_no, "size": stored.size},
    )
    return tender


def set_tender_text(db: Session, verification: Verification, text: str) -> None:
    verification.tender.raw_text = text


def record_decision(
    db: Session,
    audit: AuditService,
    verification: Verification,
    *,
    decision: DecisionType,
    comment: str,
    officer_name: str,
    officer_id: str,
) -> OfficerDecision:
    """Persist the officer's decision. This is the only path to FINAL_DECISION."""
    record = OfficerDecision(
        verification_id=verification.id,
        decision=decision.value,
        comment=comment,
        officer_name=officer_name,
        officer_id=officer_id,
    )
    db.add(record)

    audit.record(
        verification.id,
        AuditEventType.OFFICER_DECISION_RECORDED,
        f"Decision recorded: {decision.value} by {officer_name} ({officer_id}).",
        stage="Decision",
        actor=ActorType.OFFICER,
        metadata={
            "decision": decision.value,
            "officer_name": officer_name,
            "officer_id": officer_id,
        },
    )
    db.flush()
    return record


# --------------------------------------------------------------------------- #
# Queries
# --------------------------------------------------------------------------- #


def get_verification(db: Session, verification_id: str) -> Verification:
    verification = db.get(Verification, verification_id)
    if verification is None:
        raise NotFoundError(f"Verification '{verification_id}' was not found.")
    return verification


def _active_tender(db: Session, verification: Verification) -> Tender:
    tender = verification.tender
    if tender is None:
        raise NotFoundError("No tender has been uploaded for this verification.")
    return tender


def summarise(db: Session, verification: Verification) -> dict:
    """Compact per-case summary used by lists, the dashboard and reports."""
    state = compute_state(db, verification)

    bidder = verification.bidder
    tender = verification.tender
    risk = db.scalars(
        select(RiskAssessment).where(RiskAssessment.verification_id == verification.id)
    ).first()
    decision = db.scalars(
        select(OfficerDecision)
        .where(OfficerDecision.verification_id == verification.id)
        .order_by(OfficerDecision.id.desc())
    ).first()

    compliance_total = state["counts"]["compliance"]
    compliance_pass = 0
    if compliance_total:
        compliance_pass = int(
            db.scalar(
                select(func.count())
                .select_from(ComplianceResult)
                .where(
                    ComplianceResult.verification_id == verification.id,
                    ComplianceResult.status == ComplianceStatus.PASS.value,
                )
            )
            or 0
        )

    verified = int(
        db.scalar(
            select(func.count())
            .select_from(VerificationResult)
            .where(
                VerificationResult.verification_id == verification.id,
                VerificationResult.status == "VERIFIED",
            )
        )
        or 0
    )

    return {
        "id": verification.id,
        "title": verification.title,
        "tender_reference": verification.tender_reference,
        "tenderer": verification.tenderer,
        "status": state["status"],
        "current_step": state["current_step"],
        "is_demo": verification.is_demo,
        "bidder_name": bidder.name if bidder else None,
        "tender_title": tender.title if tender else None,
        "risk_level": risk.level if risk else None,
        "risk_score": risk.score if risk else None,
        "compliance_pass": compliance_pass if compliance_total else None,
        "compliance_total": compliance_total or None,
        "decision": decision.decision if decision else None,
        "created_at": verification.created_at,
        "updated_at": verification.updated_at,
    }


def list_verifications(
    db: Session,
    *,
    status: str | None = None,
    risk: str | None = None,
    search: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    rows = db.scalars(select(Verification).order_by(Verification.created_at.desc())).all()
    summaries = [summarise(db, v) for v in rows]

    if status:
        summaries = [s for s in summaries if s["status"] == status]
    if risk:
        wanted = {r.strip().upper() for r in risk.split(",") if r.strip()}
        summaries = [s for s in summaries if (s["risk_level"] or "") in wanted]
    if search:
        needle = search.strip().lower()
        summaries = [
            s
            for s in summaries
            if needle in s["id"].lower()
            or needle in s["title"].lower()
            or needle in (s["bidder_name"] or "").lower()
            or needle in (s["tender_reference"] or "").lower()
        ]
    if limit is not None:
        summaries = summaries[offset : offset + limit]
    return summaries


def detail(db: Session, verification: Verification) -> dict:
    """Full case aggregate for the workflow page."""
    state = compute_state(db, verification)
    base = summarise(db, verification)

    bidder = verification.bidder
    tender = verification.tender

    requirements = db.scalars(
        select(Requirement)
        .where(Requirement.verification_id == verification.id)
        .order_by(Requirement.sort_order)
    ).all()
    total_requirements = len(requirements)
    verified = int(
        db.scalar(
            select(func.count())
            .select_from(VerificationResult)
            .where(
                VerificationResult.verification_id == verification.id,
                VerificationResult.status == "VERIFIED",
            )
        )
        or 0
    )
    exceptions = int(
        db.scalar(
            select(func.count())
            .select_from(VerificationResult)
            .where(
                VerificationResult.verification_id == verification.id,
                VerificationResult.status != "VERIFIED",
            )
        )
        or 0
    )

    return {
        **base,
        "tender": (
            {
                "id": tender.id,
                "reference_no": tender.reference_no,
                "title": tender.title,
                "file_name": tender.file_name,
                "file_size": tender.file_size,
                "content_type": tender.content_type,
                "analysis_mode": tender.analysis_mode,
                "requirement_count": total_requirements,
                "created_at": tender.created_at,
            }
            if tender
            else None
        ),
        "bidder": (
            {
                "id": bidder.id,
                "name": bidder.name,
                "code": bidder.code,
                "document_count": int(
                    db.scalar(
                        select(func.count())
                        .select_from(Document)
                        .where(Document.bidder_id == bidder.id)
                    )
                    or 0
                ),
            }
            if bidder
            else None
        ),
        "requirements": [
            {
                "id": r.id,
                "code": r.code,
                "title": r.title,
                "description": r.description,
                "category": r.category,
                "is_mandatory": r.is_mandatory,
                "source": r.source,
                "confidence": r.confidence,
                "threshold_value": r.threshold_value,
                "sort_order": r.sort_order,
                "validated_by_officer": r.validated_by_officer,
            }
            for r in requirements
        ],
        "document_count": state["counts"]["documents"],
        "processed_document_count": state["counts"]["processed_documents"],
        "verified_count": verified,
        "total_requirements": total_requirements,
        "exception_count": exceptions,
        "audit_event_count": len(verification.audit_events),
        "has_verification": state["has_verification"],
        "has_compliance": state["has_compliance"],
        "has_risk": state["has_risk"],
        "has_recommendation": state["has_recommendation"],
        "has_decision": state["has_decision"],
    }
