"""Deterministic SIH demo data.

`load_demo` is idempotent: calling it again replaces the demo case rather than
duplicating it, so the live presentation can be re-run at any point and always show
the same eight requirements, the same extracted values and the same 7/8 result.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings
from ..enums import AuditEventType, DocumentStatus, ProcessingMode
from ..models import (
    Document,
    ExtractedField,
    Tender,
    Verification,
)
from .audit import AuditService
from .cases import attach_tender, assign_bidder, create_verification
from .fixtures import (
    DEMO_BIDDER_CODE,
    DEMO_BIDDER_NAME,
    DEMO_CASE_TITLE,
    DEMO_TENDER_REFERENCE,
    DEMO_TENDER_TEXT,
    DEMO_TENDER_TITLE,
    DEMO_TENDERER,
    DOCUMENT_CATALOGUE,
)
from .storage import delete_stored_file, save_upload
from .tender import build_requirement_rows, extract_requirements

#: A tiny, valid, non-executable placeholder so storage and checksums are genuine.
_PLACEHOLDER_PDF = b"%PDF-1.4\n%BIDFLUX demo placeholder\n%%EOF\n"


def find_demo_case(db: Session) -> Verification | None:
    return db.scalars(
        select(Verification).where(Verification.is_demo.is_(True)).order_by(Verification.id.desc())
    ).first()


def reset_demo(
    db: Session,
    settings: Settings | None = None,
    audit: AuditService | None = None,
) -> int:
    """Remove every demo case, its dependent rows and its stored files.

    Returns how many cases were deleted. Files are only touched when a settings
    object is supplied (the loader resets work off-disk too, since loading
    replaces the case in the same request).
    """
    cases = db.scalars(select(Verification).where(Verification.is_demo.is_(True))).all()
    count = len(cases)

    stored_names: list[str] = []
    for case in cases:
        for document in case.documents:
            stored_names.append(document.stored_name)
        for tender in case.tenders:
            stored_names.append(tender.stored_name)
        db.delete(case)
    db.flush()

    if settings is not None:
        for stored_name in stored_names:
            delete_stored_file(stored_name, settings)
    return count


def load_demo(db: Session, audit: AuditService, settings: Settings) -> dict:
    """Seed the deterministic SIH case and return its summary."""
    reset_demo(db, settings)

    verification = create_verification(
        db,
        audit,
        title=DEMO_CASE_TITLE,
        tender_reference=DEMO_TENDER_REFERENCE,
        tenderer=DEMO_TENDERER,
        is_demo=True,
    )
    assign_bidder(db, verification, DEMO_BIDDER_NAME, DEMO_BIDDER_CODE)

    # --- Tender + AI-extracted requirements -------------------------------- #
    tender = attach_tender(
        db,
        audit,
        settings,
        verification,
        data=_PLACEHOLDER_PDF,
        filename=f"{DEMO_TENDER_REFERENCE}.pdf",
        content_type="application/pdf",
        reference_no=DEMO_TENDER_REFERENCE,
        title=DEMO_TENDER_TITLE,
    )
    tender.raw_text = DEMO_TENDER_TEXT

    specs, mode = extract_requirements(DEMO_TENDER_TEXT, settings)
    tender.analysis_mode = mode

    for row in build_requirement_rows(specs, tender.id, verification.id):
        db.add(row)
    db.flush()

    audit.record(
        verification.id,
        AuditEventType.REQUIREMENTS_EXTRACTED,
        f"{len(specs)} requirement(s) extracted from the tender ({mode}).",
        stage="Requirements",
        metadata={"count": len(specs), "mode": mode},
    )

    # --- Bidder documents (OEM Authorisation deliberately absent) ---------- #
    submitted = 0
    for spec in DOCUMENT_CATALOGUE:
        if not spec.submitted_in_demo:
            continue

        stored = save_upload(
            _PLACEHOLDER_PDF,
            original_name=spec.filename,
            content_type="application/pdf",
            settings=settings,
        )
        document = Document(
            verification_id=verification.id,
            bidder_id=verification.bidder.id,
            doc_type=spec.doc_type.value,
            label=spec.label,
            file_name=stored.original_name,
            stored_name=stored.stored_name,
            file_size=stored.size,
            content_type=stored.content_type,
            status=DocumentStatus.PROCESSED.value,
            processing_mode=ProcessingMode.MOCK.value,
            checksum=stored.checksum,
        )
        db.add(document)
        db.flush()

        for item in spec.fields:
            db.add(
                ExtractedField(
                    verification_id=verification.id,
                    document_id=document.id,
                    field_name=item.field_name,
                    field_value=item.field_value,
                    confidence=item.confidence,
                    source_label=item.source_label,
                    page_no=1,
                    extraction_mode=ProcessingMode.MOCK.value,
                )
            )
        submitted += 1

    missing = [d for d in DOCUMENT_CATALOGUE if not d.submitted_in_demo]
    audit.record(
        verification.id,
        AuditEventType.DOCUMENTS_UPLOADED,
        f"{submitted} document(s) submitted; {len(missing)} expected document(s) missing.",
        stage="Documents",
        metadata={
            "submitted": submitted,
            "missing": [d.label for d in missing],
        },
    )
    audit.record(
        verification.id,
        AuditEventType.DOCUMENTS_PROCESSED,
        f"Processed {submitted} document(s) using simulated OCR ({ProcessingMode.MOCK.value}).",
        stage="Extraction",
        metadata={"mode": ProcessingMode.MOCK.value},
    )

    audit.record(
        verification.id,
        AuditEventType.DEMO_DATA_LOADED,
        "SIH demo dataset loaded (deterministic).",
        stage="Tender",
        metadata={"tender": DEMO_TENDER_REFERENCE, "bidder": DEMO_BIDDER_NAME},
    )
    db.flush()

    return {
        "verification_id": verification.id,
        "tender_reference": DEMO_TENDER_REFERENCE,
        "tender_title": DEMO_TENDER_TITLE,
        "bidder_name": DEMO_BIDDER_NAME,
        "requirements": len(specs),
        "documents": submitted,
        "reset_performed": True,
        "message": (
            f"SIH demo data loaded for {DEMO_TENDER_REFERENCE}. "
            f"{len(specs)} requirements, {submitted} documents, "
            f"{len(missing)} expected document(s) missing."
        ),
    }


def demo_missing_documents() -> list[str]:
    """Labels of the document types the demo bidder deliberately did not submit."""
    return [d.label for d in DOCUMENT_CATALOGUE if not d.submitted_in_demo]
