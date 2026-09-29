"""Compliance, risk, recommendation, decision and the workflow stepper."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ComplianceResult, OfficerDecision, Requirement, Verification, VerificationResult
from ..schemas import (
    ComplianceResponse,
    ComplianceRow,
    OfficerDecisionCreate,
    OfficerDecisionOut,
    RecommendationResponse,
    RiskResponse,
    WorkflowStateResponse,
)
from ..errors import ConflictError
from ..enums import DecisionType
from ..services import cases as cases_service
from ..services import compliance as compliance_service
from ..services import recommendation as recommendation_service
from ..services import risk as risk_service
from ..services import workflow as workflow_service
from ..services.audit import AuditService
from .deps import get_audit, get_case, get_db

router = APIRouter(prefix="/verifications", tags=["workflow"])


def _sync(db: Session, verification: Verification) -> None:
    workflow_service.sync_state(db, verification)


# --------------------------------------------------------------------------- #
# Workflow state (drives the frontend stepper)
# --------------------------------------------------------------------------- #


@router.get("/{verification_id}/workflow", response_model=WorkflowStateResponse)
def get_workflow_state(
    case: Verification = Depends(get_case),
    db: Session = Depends(get_db),
) -> dict:
    state = workflow_service.compute_state(db, case)
    return {
        "verification_id": case.id,
        "current_step": state["current_step"],
        "step_index": state["step_index"],
        "status": state["status"],
        "steps": state["steps"],
        "has_tender": state["has_tender"],
        "has_requirements": state["has_requirements"],
        "has_documents": state["has_documents"],
        "documents_processed": state["documents_processed"],
        "has_verification": state["has_verification"],
        "has_compliance": state["has_compliance"],
        "has_risk": state["has_risk"],
        "has_recommendation": state["has_recommendation"],
        "has_decision": state["has_decision"],
    }


# --------------------------------------------------------------------------- #
# Compliance
# --------------------------------------------------------------------------- #


@router.get("/{verification_id}/compliance", response_model=ComplianceResponse)
def get_compliance(
    verification_id: str,
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit),
) -> dict:
    verification = cases_service.get_verification(db, verification_id)

    if not verification.requirements:
        raise ConflictError("Extract tender requirements before computing compliance.")
    if not verification.verification_results:
        raise ConflictError("Run verification before computing the compliance matrix.")

    compliance_service.compute_compliance(db, audit, verification)
    _sync(db, verification)
    db.commit()

    return _compliance_payload(db, verification)


def _compliance_payload(db: Session, verification: Verification) -> dict:
    rows = db.scalars(
        select(ComplianceResult)
        .where(ComplianceResult.verification_id == verification.id)
        .order_by(ComplianceResult.id)
    ).all()
    requirements = {
        r.id: r
        for r in db.scalars(
            select(Requirement).where(Requirement.verification_id == verification.id)
        ).all()
    }
    results = {
        r.requirement_id: r
        for r in db.scalars(
            select(VerificationResult).where(
                VerificationResult.verification_id == verification.id
            )
        ).all()
    }

    payload = []
    for row in rows:
        requirement = requirements.get(row.requirement_id)
        result = results.get(row.requirement_id)
        payload.append(
            ComplianceRow(
                requirement_id=row.requirement_id,
                requirement_code=requirement.code if requirement else "",
                requirement_title=requirement.title if requirement else "",
                category=requirement.category if requirement else "",
                is_mandatory=requirement.is_mandatory if requirement else True,
                status=row.status,
                reason=row.reason,
                evidence_ref=row.evidence_ref,
                verification_status=result.status if result else "NOT_RUN",
                observed_value=result.observed_value if result else "",
                computed_at=row.computed_at,
            ).model_dump()
        )

    computed_at = max((row.computed_at for row in rows), default=None) or datetime.now(timezone.utc)

    return {
        "verification_id": verification.id,
        "rows": payload,
        "pass_count": sum(1 for r in payload if r["status"] == "PASS"),
        "fail_count": sum(1 for r in payload if r["status"] == "FAIL"),
        "review_count": sum(1 for r in payload if r["status"] == "REVIEW"),
        "not_applicable_count": sum(1 for r in payload if r["status"] == "NOT_APPLICABLE"),
        "total": len(payload),
        "computed_at": computed_at,
    }


# --------------------------------------------------------------------------- #
# Risk
# --------------------------------------------------------------------------- #


@router.get("/{verification_id}/risk", response_model=RiskResponse)
def get_risk(
    verification_id: str,
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit),
) -> dict:
    verification = cases_service.get_verification(db, verification_id)
    if not verification.compliance_results:
        raise ConflictError("Compute the compliance matrix before assessing risk.")

    assessment, signals = risk_service.assess_risk(db, audit, verification)
    _sync(db, verification)
    db.commit()

    return {
        "verification_id": verification.id,
        "level": assessment.level,
        "score": assessment.score,
        "reasons": list(assessment.reasons or []),
        "signals": signals,
        "verified_count": assessment.verified_count,
        "total_count": assessment.total_count,
        "computed_at": assessment.computed_at,
    }


# --------------------------------------------------------------------------- #
# Recommendation
# --------------------------------------------------------------------------- #


@router.get("/{verification_id}/recommendation", response_model=RecommendationResponse)
def get_recommendation(
    verification_id: str,
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit),
) -> dict:
    verification = cases_service.get_verification(db, verification_id)
    payload = recommendation_service.build_recommendation(db, audit, verification)
    _sync(db, verification)
    db.commit()
    return payload | {"generated_at": datetime.now(timezone.utc)}


# --------------------------------------------------------------------------- #
# Officer decision
# --------------------------------------------------------------------------- #


@router.post("/{verification_id}/decision", response_model=OfficerDecisionOut)
def record_decision(
    verification_id: str,
    payload: OfficerDecisionCreate,
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit),
) -> dict:
    verification = cases_service.get_verification(db, verification_id)
    if not verification.risk_assessment:
        raise ConflictError("Assess risk before recording an officer decision.")

    record = cases_service.record_decision(
        db,
        audit,
        verification,
        decision=DecisionType(payload.decision),
        comment=payload.comment,
        officer_name=payload.officer_name,
        officer_id=payload.officer_id,
    )
    _sync(db, verification)
    db.commit()
    return OfficerDecisionOut.model_validate(record).model_dump()


@router.get("/{verification_id}/decision", response_model=OfficerDecisionOut | None)
def get_decision(verification_id: str, db: Session = Depends(get_db)) -> dict | None:
    verification = cases_service.get_verification(db, verification_id)
    record = db.scalars(
        select(OfficerDecision)
        .where(OfficerDecision.verification_id == verification.id)
        .order_by(OfficerDecision.id.desc())
    ).first()
    return OfficerDecisionOut.model_validate(record).model_dump() if record else None
