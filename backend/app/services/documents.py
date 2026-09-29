"""Document upload and MOCK OCR / field extraction.

Two extraction paths, both deterministic:

* ``RULE``  — the uploaded file carried readable text; fields are parsed from it with
  regular expressions and given a flat, lower confidence.
* ``MOCK``  — no readable text (PDF/image). Fields come from the fixed fixture set,
  which is what the SIH demo displays.

The seam for a real OCR + LLM implementation is :func:`extract_document_fields`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings
from ..enums import (
    AuditEventType,
    DocumentStatus,
    DocumentType,
    ProcessingMode,
)
from ..errors import NotFoundError
from ..models import Bidder, Document, ExtractedField, Verification
from .audit import AuditService
from .fixtures import DOCUMENT_CATALOGUE
from .storage import read_text, save_upload

#: Confidence applied to values parsed from genuinely uploaded text.
RULE_MODE_CONFIDENCE = 0.92

_GSTIN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z]\b", re.I)
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_UDYAM = re.compile(r"\bUDYAM[-\s][A-Z]{2}[-\s][A-Z0-9]{2}[-\s][A-Z0-9]{4,7}\b", re.I)
_YEARS = re.compile(r"(\d{1,2})\s*(?:years?|yrs?)\s*(?:of)?\s*experience", re.I)


@dataclass(frozen=True)
class FieldResult:
    field_name: str
    field_value: str
    confidence: float
    source_label: str
    page_no: int = 1


# --------------------------------------------------------------------------- #
# Extraction (the replaceable seam)
# --------------------------------------------------------------------------- #


def _extract_from_text(doc_type: DocumentType, text: str, label: str) -> list[FieldResult]:
    """Parse fields out of real uploaded text. Deterministic regex rules."""
    fields: list[FieldResult] = []

    def add(name: str, value: str | None) -> None:
        if value:
            fields.append(FieldResult(name, value, RULE_MODE_CONFIDENCE, label))

    if doc_type is DocumentType.GST_CERTIFICATE:
        add("GSTIN", _first(_GSTIN, text))
        add("Company", None)
    elif doc_type is DocumentType.PAN_DOCUMENT:
        add("PAN", _first(_PAN, text))
    elif doc_type is DocumentType.UDYAM_CERTIFICATE:
        add("Udyam Number", _first(_UDYAM, text))
    elif doc_type is DocumentType.EXPERIENCE:
        years = _YEARS.search(text)
        add("Years of Experience", years.group(1) if years else None)
    return fields


def _extract_from_fixture(doc_type: DocumentType, label: str) -> list[FieldResult]:
    spec = next((d for d in DOCUMENT_CATALOGUE if d.doc_type is doc_type), None)
    if spec is None:
        return []
    return [
        FieldResult(f.field_name, f.field_value, f.confidence, f.source_label)
        for f in spec.fields
    ]


def extract_document_fields(
    document: Document, settings: Settings
) -> tuple[list[FieldResult], str]:
    """Return the fields for ``document`` and the mode used.

    Replace the body of this function with an OCR + LLM call to go live; callers
    already carry the mode through to the API and the UI.
    """
    if not settings.ai_enabled:
        return [], ProcessingMode.RULE.value

    text = read_text(document.stored_name, settings)
    label = document.label or document.file_name
    doc_type = DocumentType(document.doc_type)

    if text.strip():
        fields = _extract_from_text(doc_type, text, label)
        if fields:
            return fields, ProcessingMode.RULE.value

    return _extract_from_fixture(doc_type, label), ProcessingMode.MOCK.value


def _first(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0).upper() if match else None


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def _get_bidder(db: Session, verification: Verification) -> Bidder:
    bidder = verification.bidder
    if bidder is None:
        raise NotFoundError("This verification has no bidder yet.")
    return bidder


def missing_expected_labels(documents: list[Document]) -> list[str]:
    """Expected document types this case has not submitted.

    Derived from the documents actually on the case, so uploading the missing
    document clears it instead of the gap being reported forever.
    """
    present = {doc.doc_type for doc in documents}
    return [spec.label for spec in DOCUMENT_CATALOGUE if spec.doc_type not in present]


def add_document(
    db: Session,
    audit: AuditService,
    settings: Settings,
    verification: Verification,
    *,
    data: bytes,
    filename: str | None,
    content_type: str | None,
    doc_type: DocumentType,
    label: str = "",
) -> Document:
    """Store one uploaded document against the case's bidder."""
    bidder = _get_bidder(db, verification)
    stored = save_upload(
        data, original_name=filename, content_type=content_type, settings=settings
    )

    document = Document(
        verification_id=verification.id,
        bidder_id=bidder.id,
        doc_type=doc_type.value,
        label=(label or stored.sanitized_name)[:255],
        file_name=stored.original_name,
        stored_name=stored.stored_name,
        file_size=stored.size,
        content_type=stored.content_type,
        status=DocumentStatus.UPLOADED.value,
        processing_mode=ProcessingMode.MOCK.value,
        checksum=stored.checksum,
    )
    db.add(document)
    audit.record(
        verification.id,
        AuditEventType.DOCUMENTS_UPLOADED,
        f"Document uploaded: {document.label}",
        stage="Documents",
        metadata={"doc_type": doc_type.value, "size": stored.size},
    )
    return document


def process_documents(
    db: Session, audit: AuditService, settings: Settings, verification: Verification
) -> tuple[int, int]:
    """Extract fields for every unprocessed document. Returns (documents, fields)."""
    pending = (
        db.scalars(
            select(Document)
            .where(
                Document.verification_id == verification.id,
                Document.status != DocumentStatus.PROCESSED.value,
            )
            .order_by(Document.id)
        )
        .all()
    )

    if not pending:
        return 0, 0

    field_count = 0
    for document in pending:
        # Remove any previous extraction so reprocessing stays idempotent.
        for existing in db.scalars(
            select(ExtractedField).where(ExtractedField.document_id == document.id)
        ).all():
            db.delete(existing)

        fields, mode = extract_document_fields(document, settings)
        for item in fields:
            db.add(
                ExtractedField(
                    verification_id=verification.id,
                    document_id=document.id,
                    field_name=item.field_name,
                    field_value=item.field_value,
                    confidence=item.confidence,
                    source_label=item.source_label,
                    page_no=item.page_no,
                    extraction_mode=mode,
                )
            )
            field_count += 1

        document.status = DocumentStatus.PROCESSED.value
        document.processing_mode = mode
        document.processed_at = datetime.now(timezone.utc)

        audit.record(
            verification.id,
            AuditEventType.DOCUMENT_EXTRACTION_COMPLETED,
            f"Extraction completed for {document.label} ({mode})",
            stage="Extraction",
            metadata={"doc_type": document.doc_type, "fields": len(fields), "mode": mode},
        )

    audit.record(
        verification.id,
        AuditEventType.DOCUMENTS_PROCESSED,
        f"Processed {len(pending)} document(s), extracted {field_count} field(s).",
        stage="Extraction",
        metadata={"documents": len(pending), "fields": field_count},
    )
    return len(pending), field_count
