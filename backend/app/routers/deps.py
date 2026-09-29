"""Shared router dependencies."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import get_db
from ..models import Verification
from ..services.audit import AuditService
from ..services.cases import get_verification


def get_audit(db: Session = Depends(get_db)) -> AuditService:
    """One audit writer per request; every service receives the same instance."""
    return AuditService(db)


def get_case(verification_id: str, db: Session = Depends(get_db)) -> Verification:
    return get_verification(db, verification_id)


__all__ = [
    "AuditService",
    "Settings",
    "get_audit",
    "get_case",
    "get_db",
    "get_settings",
]
