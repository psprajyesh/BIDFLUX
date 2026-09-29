"""Dashboard aggregates and the summary report."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..enums import RiskLevel, VerificationStatus
from ..models import Requirement, Verification, VerificationResult
from .cases import CAPABILITY_NOTICE, summarise

RECENT_LIMIT = 8


def _verified_count(db: Session, verification_id: str) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(VerificationResult)
            .where(
                VerificationResult.verification_id == verification_id,
                VerificationResult.status == "VERIFIED",
            )
        )
        or 0
    )


def _requirement_count(db: Session, verification_id: str) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Requirement)
            .where(Requirement.verification_id == verification_id)
        )
        or 0
    )


def dashboard(db: Session) -> dict:
    verifications = db.scalars(
        select(Verification).order_by(Verification.created_at.desc())
    ).all()
    summaries = [summarise(db, v) for v in verifications]

    total_matrix = sum(s["compliance_total"] or 0 for s in summaries)
    total_pass = sum(s["compliance_pass"] or 0 for s in summaries)

    return {
        "total_verifications": len(summaries),
        "pending_review": sum(
            1 for s in summaries if s["status"] == VerificationStatus.REVIEW_REQUIRED.value
        ),
        "high_risk_cases": sum(
            1
            for s in summaries
            if s["risk_level"] in {RiskLevel.HIGH.value, RiskLevel.CRITICAL.value}
        ),
        "completed_decisions": sum(
            1 for s in summaries if s["status"] == VerificationStatus.FINAL_DECISION.value
        ),
        "compliance_rate": round((total_pass / total_matrix) * 100, 1) if total_matrix else 0.0,
        "demo_cases": sum(1 for s in summaries if s["is_demo"]),
        "recent": summaries[:RECENT_LIMIT],
        "capability_notice": CAPABILITY_NOTICE,
    }


def report_rows(db: Session) -> list[dict]:
    verifications = db.scalars(
        select(Verification).order_by(Verification.created_at.desc())
    ).all()

    rows = []
    for verification in verifications:
        summary = summarise(db, verification)
        rows.append(
            {
                "verification_id": summary["id"],
                "title": summary["title"],
                "tender_reference": summary["tender_reference"],
                "bidder": summary["bidder_name"],
                "status": summary["status"],
                "risk_level": summary["risk_level"],
                "risk_score": summary["risk_score"],
                "verified_count": _verified_count(db, verification.id),
                "total_requirements": _requirement_count(db, verification.id),
                "decision": summary["decision"],
                "updated_at": summary["updated_at"],
            }
        )
    return rows
