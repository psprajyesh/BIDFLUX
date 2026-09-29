"""Demo dataset controls."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..schemas import DemoLoadResponse, DemoResetResponse
from ..services import demo as demo_service
from ..services.audit import AuditService
from .deps import get_audit, get_db

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/load", response_model=DemoLoadResponse)
def load_demo_data(
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Seed the deterministic SIH case. Idempotent: re-loading replaces it."""
    payload = demo_service.load_demo(db, audit, settings)
    db.commit()
    return payload


@router.post("/reset", response_model=DemoResetResponse)
def reset_demo_data(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Delete every demo case, its dependent rows and stored files.

    Audit events are case-scoped and cascade with the case, so a reset leaves no
    orphaned trail — which is the desired behaviour for a clean demo start.
    """
    deleted = demo_service.reset_demo(db, settings)
    db.commit()
    return {
        "deleted_verifications": deleted,
        "message": f"Removed {deleted} demo verification(s).",
    }
