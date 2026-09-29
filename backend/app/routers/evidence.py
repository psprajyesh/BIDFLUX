"""Evidence chain and audit trail."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuditEvent, Verification
from ..schemas import AuditEventOut, EvidenceResponse
from ..services import cases as cases_service
from ..services import evidence as evidence_service
from .deps import get_case, get_db

router = APIRouter(prefix="/verifications", tags=["evidence"])


@router.get("/{verification_id}/evidence", response_model=EvidenceResponse)
def get_evidence(
    case: Verification = Depends(get_case),
    db: Session = Depends(get_db),
) -> dict:
    payload = evidence_service.build_evidence(db, case)
    return payload | {"generated_at": datetime.now(timezone.utc)}


@router.get("/{verification_id}/audit", response_model=list[AuditEventOut])
def get_audit_trail(
    verification_id: str,
    db: Session = Depends(get_db),
    event_type: str | None = Query(default=None),
) -> list[dict]:
    verification = cases_service.get_verification(db, verification_id)
    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.verification_id == verification.id)
        .order_by(AuditEvent.id)
    ).all()

    rows = []
    for event in events:
        if event_type and event.event_type != event_type:
            continue
        rows.append(AuditEventOut.model_validate(event).model_dump())
    return rows
