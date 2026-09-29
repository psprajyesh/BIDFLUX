"""Verification cases, tender upload, documents and verification execution."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..enums import AuditEventType, DocumentType
from ..errors import ConflictError
from ..models import (
    Document,
    ExtractedField,
    OfficerDecision,
    Requirement,
    RiskAssessment,
    Verification,
    VerificationResult,
)
from ..schemas import (
    DocumentOut,
    ExtractedFieldOut,
    MessageResponse,
    ProcessResponse,
    RequirementOut,
    RunVerificationResponse,
    TenderOut,
    VerificationCreate,
    VerificationDetail,
    VerificationResultOut,
    VerificationSummary,
)
from ..services import cases as cases_service
from ..services import documents as documents_service
from ..services import tender as tender_service
from ..services import verification as verification_service
from ..services import workflow as workflow_service
from ..services.audit import AuditService
from ..services.fixtures import AI_VALIDATION_NOTICE
from ..services.storage import read_text
from .deps import get_audit, get_case, get_db

router = APIRouter(prefix="/verifications", tags=["verifications"])


# --------------------------------------------------------------------------- #
# Cases
# --------------------------------------------------------------------------- #


@router.post("", response_model=VerificationDetail, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: VerificationCreate,
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit),
) -> dict:
    verification = cases_service.create_verification(
        db,
        audit,
        title=payload.title,
        tender_reference=payload.tender_reference,
        tenderer=payload.tenderer,
    )
    db.commit()
    return cases_service.detail(db, verification)


@router.get("", response_model=list[VerificationSummary])
def list_cases(
    status_filter: str | None = Query(default=None, alias="status"),
    risk: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict]:
    return cases_service.list_verifications(
        db, status=status_filter, risk=risk, search=q, limit=limit, offset=offset
    )


@router.get("/{verification_id}", response_model=VerificationDetail)
def get_case_detail(
    case: Verification = Depends(get_case),
    db: Session = Depends(get_db),
) -> dict:
    return cases_service.detail(db, case)


# --------------------------------------------------------------------------- #
# Tender
# --------------------------------------------------------------------------- #


@router.post("/{verification_id}/tender", response_model=MessageResponse)
async def upload_tender(
    verification_id: str,
    file: UploadFile = File(...),
    reference_no: str = Form(default=""),
    title: str = Form(default=""),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit),
    settings: Settings = Depends(get_settings),
) -> dict:
    verification = cases_service.get_verification(db, verification_id)
    data = await file.read()

    reference = (reference_no or verification.tender_reference or verification.id).strip()
    tender_title = (title or verification.title or "Untitled tender").strip()

    tender = cases_service.attach_tender(
        db,
        audit,
        settings,
        verification,
        data=data,
        filename=file.filename,
        content_type=file.content_type,
        reference_no=reference,
        title=tender_title,
    )
    cases_service.set_tender_text(db, verification, read_text(tender.stored_name, settings))

    workflow_service.sync_state(db, verification)
    db.commit()

    return {
        "message": f"Tender {reference} uploaded. Analyse it to extract requirements.",
        "verification_id": verification.id,
    }


@router.get("/{verification_id}/tender")
def get_tender(
    verification_id: str,
    db: Session = Depends(get_db),
) -> dict:
    verification = cases_service.get_verification(db, verification_id)
    tender = cases_service._active_tender(db, verification)

    return {
        "tender": TenderOut.model_validate(tender).model_dump()
        | {"requirement_count": len(verification.requirements)},
        "requirements": [
            RequirementOut.model_validate(r).model_dump() for r in verification.requirements
        ],
        "notice": AI_VALIDATION_NOTICE,
    }


@router.post("/{verification_id}/tender/analyse", response_model=MessageResponse)
def analyse_tender(
    verification_id: str,
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit),
    settings: Settings = Depends(get_settings),
) -> dict:
    verification = cases_service.get_verification(db, verification_id)
    tender = cases_service._active_tender(db, verification)

    specs, mode = tender_service.extract_requirements(tender.raw_text, settings)
    tender.analysis_mode = mode

    for stale in db.scalars(
        select(Requirement).where(Requirement.verification_id == verification.id)
    ).all():
        db.delete(stale)
    # Risk and any decision were derived from the old requirements; re-analysis makes
    # them stale, so drop them too rather than showing an outdated risk level.
    for derived in db.scalars(
        select(RiskAssessment).where(RiskAssessment.verification_id == verification.id)
    ).all():
        db.delete(derived)
    for derived in db.scalars(
        select(OfficerDecision).where(OfficerDecision.verification_id == verification.id)
    ).all():
        db.delete(derived)
    db.flush()

    for row in tender_service.build_requirement_rows(specs, tender.id, verification.id):
        db.add(row)
    db.flush()

    audit.record(
        verification.id,
        AuditEventType.REQUIREMENTS_EXTRACTED,
        f"{len(specs)} requirement(s) extracted from the tender ({mode}).",
        stage="Requirements",
        metadata={"count": len(specs), "mode": mode},
    )
    workflow_service.sync_state(db, verification)
    db.commit()

    return {
        "message": f"{len(specs)} requirement(s) extracted ({mode}). Officer validation required.",
        "verification_id": verification.id,
    }


# --------------------------------------------------------------------------- #
# Documents
# --------------------------------------------------------------------------- #


@router.post(
    "/{verification_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    verification_id: str,
    file: UploadFile = File(...),
    doc_type: DocumentType = Form(default=DocumentType.OTHER),
    label: str = Form(default=""),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit),
    settings: Settings = Depends(get_settings),
) -> dict:
    verification = cases_service.get_verification(db, verification_id)
    if not verification.requirements:
        raise ConflictError("Upload and analyse the tender before adding bidder documents.")

    data = await file.read()
    document = documents_service.add_document(
        db,
        audit,
        settings,
        verification,
        data=data,
        filename=file.filename,
        content_type=file.content_type,
        doc_type=doc_type,
        label=label,
    )
    workflow_service.sync_state(db, verification)
    db.commit()
    return DocumentOut.model_validate(document).model_dump()


@router.get("/{verification_id}/documents")
def list_documents(verification_id: str, db: Session = Depends(get_db)) -> dict:
    verification = cases_service.get_verification(db, verification_id)
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

    by_document: dict[int, list[dict]] = {}
    for item in fields:
        payload = ExtractedFieldOut.model_validate(item).model_dump()
        payload["document_label"] = next(
            (d.label for d in documents if d.id == item.document_id), ""
        )
        by_document.setdefault(item.document_id, []).append(payload)

    return {
        "verification_id": verification.id,
        "documents": [
            DocumentOut.model_validate(d).model_dump()
            | {"extracted_fields": by_document.get(d.id, [])}
            for d in documents
        ],
        "missing_expected": documents_service.missing_expected_labels(documents),
    }


@router.post("/{verification_id}/documents/process", response_model=ProcessResponse)
def process_documents(
    verification_id: str,
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit),
    settings: Settings = Depends(get_settings),
) -> dict:
    verification = cases_service.get_verification(db, verification_id)
    processed, fields = documents_service.process_documents(db, audit, settings, verification)
    workflow_service.sync_state(db, verification)
    db.commit()

    if not processed:
        return {
            "message": "All submitted documents have already been processed.",
            "verification_id": verification.id,
            "documents_processed": 0,
            "fields_extracted": 0,
            "mode": "RULE",
        }
    return {
        "message": f"Processed {processed} document(s); extracted {fields} field(s).",
        "verification_id": verification.id,
        "documents_processed": processed,
        "fields_extracted": fields,
        "mode": "MOCK",
    }


# --------------------------------------------------------------------------- #
# Verification execution
# --------------------------------------------------------------------------- #


@router.post("/{verification_id}/verification/run", response_model=RunVerificationResponse)
def run_verification(
    verification_id: str,
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit),
) -> dict:
    verification = cases_service.get_verification(db, verification_id)
    if not verification.requirements:
        raise ConflictError("Extract tender requirements before running verification.")

    total, verified, missing = verification_service.run_verification(db, audit, verification)
    workflow_service.sync_state(db, verification)
    db.commit()

    return {
        "message": f"Verification complete: {verified} verified, {missing} missing of {total}.",
        "verification_id": verification.id,
        "results": total,
        "verified": verified,
        "missing": missing,
        "mode": "RULE",
    }


@router.get("/{verification_id}/verification", response_model=list[VerificationResultOut])
def get_verification_results(verification_id: str, db: Session = Depends(get_db)) -> list[dict]:
    verification = cases_service.get_verification(db, verification_id)
    results = db.scalars(
        select(VerificationResult)
        .where(VerificationResult.verification_id == verification.id)
        .order_by(VerificationResult.id)
    ).all()
    requirements = {
        r.id: r
        for r in db.scalars(
            select(Requirement).where(Requirement.verification_id == verification.id)
        ).all()
    }

    rows = []
    for item in results:
        requirement = requirements.get(item.requirement_id)
        payload = VerificationResultOut.model_validate(item).model_dump()
        payload["requirement_code"] = requirement.code if requirement else ""
        payload["requirement_title"] = requirement.title if requirement else ""
        payload["category"] = requirement.category if requirement else ""
        payload["is_mandatory"] = requirement.is_mandatory if requirement else True
        rows.append(payload)
    return rows
