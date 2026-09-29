"""BIDFLUX API entry point.

Single FastAPI process. No authentication by design — this is a demonstration
system and it says so plainly in the health payload and the OpenAPI description.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db
from .errors import register_error_handlers
from .routers import demo, evidence, system, verifications, workflow
from .services.cases import API_VERSION

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("bidflux")

settings = get_settings()

DESCRIPTION = """
**AI-Powered Procurement Compliance Platform** — SIH demonstration build.

No authentication: the application opens directly on the dashboard.

**What is real**

- Verification case lifecycle, tender and document storage, file validation
- Compliance matrix, risk scoring, officer decision, audit trail, evidence chain

**What is simulated (flagged as `MOCK` in responses and in the UI)**

- Requirement extraction from tender text (`AI_MODE=mock`)
- Document OCR / field extraction and confidence scores
- GST / PAN / Udyam checks — local structural rules only, **no government API is contacted**

The system never decides automatically. The officer records the final decision.
""".strip()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "BIDFLUX API %s ready (env=%s, ai_mode=%s)",
        API_VERSION,
        settings.app_env,
        settings.ai_mode,
    )
    yield


app = FastAPI(
    title="BIDFLUX API",
    description=DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Exact-origin allow-list. Never wildcard in production.
allowed = settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
    expose_headers=["Content-Disposition"],
    max_age=3600,
)
if "*" in allowed and settings.is_production:  # pragma: no cover - guardrail
    logger.error("CORS_ORIGINS contains '*' while APP_ENV=production. Fix this.")

register_error_handlers(app)

app.include_router(system.router, prefix="/api")
app.include_router(verifications.router, prefix="/api")
app.include_router(workflow.router, prefix="/api")
app.include_router(evidence.router, prefix="/api")
app.include_router(demo.router, prefix="/api")


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "name": "BIDFLUX API",
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }
