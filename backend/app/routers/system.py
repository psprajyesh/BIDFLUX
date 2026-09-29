"""Health, dashboard aggregates and the summary report."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..schemas import DashboardResponse, HealthResponse, ReportsResponse
from ..services import reports as reports_service
from ..services.cases import API_VERSION, CAPABILITIES
from .deps import get_db

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "api_version": API_VERSION,
        "app_env": settings.app_env,
        "ai_mode": settings.ai_mode,
        "capabilities": CAPABILITIES,
    }


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db)) -> dict:
    return reports_service.dashboard(db)


@router.get("/reports/summary", response_model=ReportsResponse)
def reports_summary(db: Session = Depends(get_db)) -> dict:
    rows = reports_service.report_rows(db)
    return {
        "rows": rows,
        "total": len(rows),
        "generated_at": datetime.now(timezone.utc),
    }
