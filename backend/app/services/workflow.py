"""Derived workflow state.

`current_step` and `status` are computed from what actually exists in the database —
never stored as truth — so the stepper can never drift out of sync with the data.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..enums import WORKFLOW_STEPS, VerificationStatus
from ..models import (
    ComplianceResult,
    Document,
    OfficerDecision,
    Requirement,
    RiskAssessment,
    Verification,
    VerificationResult,
)

#: Step order. Each entry names the state flag that completes that step.
STEP_FLAGS: tuple[str, ...] = (
    "has_tender",
    "has_requirements",
    "has_documents",
    "documents_processed",
    "has_verification",
    "has_compliance",
    "has_risk",
    "has_recommendation",
    "has_decision",
)


def _count(db: Session, model: type, *conditions) -> int:
    """Row count for ``model`` filtered by the given WHERE conditions."""
    statement = select(func.count()).select_from(model)
    for condition in conditions:
        statement = statement.where(condition)
    return int(db.scalar(statement) or 0)


def compute_state(db: Session, verification: Verification) -> dict:
    """Return the flag map, current step, status and per-step list for a case."""
    vid = verification.id

    documents = _count(db, Document, Document.verification_id == vid)
    processed = _count(
        db, Document, Document.verification_id == vid, Document.status == "PROCESSED"
    )

    flags: dict[str, bool] = {
        "has_tender": verification.tender is not None,
        "has_requirements": _count(db, Requirement, Requirement.verification_id == vid) > 0,
        "has_documents": documents > 0,
        "documents_processed": documents > 0 and processed == documents,
        "has_verification": _count(db, VerificationResult, VerificationResult.verification_id == vid) > 0,
        "has_compliance": _count(db, ComplianceResult, ComplianceResult.verification_id == vid) > 0,
        "has_risk": _count(db, RiskAssessment, RiskAssessment.verification_id == vid) > 0,
        "has_recommendation": _count(db, RiskAssessment, RiskAssessment.verification_id == vid) > 0,
        "has_decision": _count(db, OfficerDecision, OfficerDecision.verification_id == vid) > 0,
    }

    current_index = next(
        (i for i, key in enumerate(STEP_FLAGS) if not flags[key]), len(STEP_FLAGS) - 1
    )
    complete_all = all(flags[key] for key in STEP_FLAGS)

    steps = []
    for index, (key, label) in enumerate(zip(STEP_FLAGS, WORKFLOW_STEPS)):
        if complete_all or index < current_index:
            state = "complete"
        elif index == current_index:
            state = "active"
        else:
            state = "pending"
        steps.append(
            {
                "key": key,
                "label": label,
                "index": index,
                "state": state,
                "complete": state == "complete",
                "active": state == "active",
            }
        )

    return {
        **flags,
        "step_index": current_index,
        "current_step": WORKFLOW_STEPS[current_index],
        "status": _status_for(flags),
        "steps": steps,
        "counts": {
            "requirements": _count(db, Requirement, Requirement.verification_id == vid),
            "documents": documents,
            "processed_documents": processed,
            "compliance": _count(db, ComplianceResult, ComplianceResult.verification_id == vid),
            "decisions": _count(db, OfficerDecision, OfficerDecision.verification_id == vid),
        },
    }


def _status_for(flags: dict) -> str:
    """First unmet milestone wins. Each enum member is used exactly once."""
    if flags["has_decision"]:
        return VerificationStatus.FINAL_DECISION.value
    if flags["has_recommendation"]:
        return VerificationStatus.REVIEW_REQUIRED.value
    if flags["has_risk"]:
        return VerificationStatus.COMPLIANCE_READY.value
    if flags["has_compliance"]:
        return VerificationStatus.VERIFICATION_COMPLETE.value
    if flags["has_verification"]:
        return VerificationStatus.DOCUMENTS_PROCESSED.value
    if flags["documents_processed"]:
        return VerificationStatus.DOCUMENTS_UPLOADED.value
    if flags["has_documents"]:
        return VerificationStatus.REQUIREMENTS_EXTRACTED.value
    if flags["has_requirements"]:
        return VerificationStatus.TENDER_UPLOADED.value
    if flags["has_tender"]:
        return VerificationStatus.DRAFT.value
    return VerificationStatus.DRAFT.value


def sync_state(db: Session, verification: Verification) -> dict:
    """Compute state and persist the denormalised columns on the row."""
    state = compute_state(db, verification)
    verification.current_step = state["current_step"]
    verification.status = state["status"]
    db.flush()
    return state
