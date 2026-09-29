"""The 11 SQLAlchemy entities that make up a BIDFLUX verification case."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..enums import (
    ActorType,
    AuditEventType,
    ComplianceStatus,
    DecisionType,
    DocumentStatus,
    DocumentType,
    ProcessingMode,
    RequirementCategory,
    RequirementSource,
    RiskLevel,
    VerificationMethod,
    VerificationOutcome,
    VerificationStatus,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Verification(Base):
    """One tender-compliance verification case. The ID is the spine of the UI."""

    __tablename__ = "verifications"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    tender_reference: Mapped[str] = mapped_column(String(64), default="")
    tenderer: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(
        String(32), default=VerificationStatus.DRAFT.value, index=True
    )
    current_step: Mapped[str] = mapped_column(String(32), default="Tender")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    tenders: Mapped[list["Tender"]] = relationship(
        back_populates="verification",
        cascade="all, delete-orphan",
        order_by="Tender.id",
    )
    bidders: Mapped[list["Bidder"]] = relationship(
        back_populates="verification",
        cascade="all, delete-orphan",
        order_by="Bidder.id",
    )
    requirements: Mapped[list["Requirement"]] = relationship(
        back_populates="verification", cascade="all, delete-orphan", order_by="Requirement.sort_order"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="verification", cascade="all, delete-orphan", order_by="Document.id"
    )
    extracted_fields: Mapped[list["ExtractedField"]] = relationship(
        back_populates="verification", cascade="all, delete-orphan"
    )
    verification_results: Mapped[list["VerificationResult"]] = relationship(
        back_populates="verification", cascade="all, delete-orphan", order_by="VerificationResult.id"
    )
    compliance_results: Mapped[list["ComplianceResult"]] = relationship(
        back_populates="verification", cascade="all, delete-orphan", order_by="ComplianceResult.id"
    )
    risk_assessment: Mapped["RiskAssessment | None"] = relationship(
        back_populates="verification", cascade="all, delete-orphan", uselist=False
    )
    officer_decisions: Mapped[list["OfficerDecision"]] = relationship(
        back_populates="verification", cascade="all, delete-orphan", order_by="OfficerDecision.id"
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="verification", cascade="all, delete-orphan", order_by="AuditEvent.id"
    )

    @property
    def tender(self) -> "Tender | None":
        """Latest tender attached to this case."""
        return self.tenders[-1] if self.tenders else None

    @property
    def bidder(self) -> "Bidder | None":
        """A verification case carries exactly one bidder."""
        return self.bidders[0] if self.bidders else None


class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verifications.id", ondelete="CASCADE"), index=True
    )
    reference_no: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    file_name: Mapped[str] = mapped_column(String(255), default="")
    stored_name: Mapped[str] = mapped_column(String(255), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    content_type: Mapped[str] = mapped_column(String(128), default="")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    analysis_mode: Mapped[str] = mapped_column(String(16), default="MOCK")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    verification: Mapped[Verification] = relationship(back_populates="tenders")
    requirements: Mapped[list["Requirement"]] = relationship(
        back_populates="tender", cascade="all, delete-orphan", order_by="Requirement.sort_order"
    )


class Bidder(Base):
    __tablename__ = "bidders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verifications.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    verification: Mapped[Verification] = relationship(back_populates="bidders")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="bidder", cascade="all, delete-orphan", order_by="Document.id"
    )


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verifications.id", ondelete="CASCADE"), index=True
    )
    tender_id: Mapped[int] = mapped_column(
        ForeignKey("tenders.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(32), default=RequirementCategory.STATUTORY.value)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(32), default=RequirementSource.AI_EXTRACTED.value)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    validated_by_officer: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    verification: Mapped[Verification] = relationship(back_populates="requirements")
    tender: Mapped[Tender] = relationship(back_populates="requirements")
    verification_results: Mapped[list["VerificationResult"]] = relationship(
        back_populates="requirement", cascade="all, delete-orphan", order_by="VerificationResult.id"
    )
    compliance_results: Mapped[list["ComplianceResult"]] = relationship(
        back_populates="requirement", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verifications.id", ondelete="CASCADE"), index=True
    )
    bidder_id: Mapped[int] = mapped_column(
        ForeignKey("bidders.id", ondelete="CASCADE"), index=True
    )
    doc_type: Mapped[str] = mapped_column(String(48), default=DocumentType.OTHER.value)
    label: Mapped[str] = mapped_column(String(255), default="")
    file_name: Mapped[str] = mapped_column(String(255), default="")
    stored_name: Mapped[str] = mapped_column(String(255), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    content_type: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(24), default=DocumentStatus.UPLOADED.value)
    processing_mode: Mapped[str] = mapped_column(String(16), default=ProcessingMode.MOCK.value)
    checksum: Mapped[str] = mapped_column(String(64), default="")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    verification: Mapped[Verification] = relationship(back_populates="documents")
    bidder: Mapped[Bidder] = relationship(back_populates="documents")
    extracted_fields: Mapped[list["ExtractedField"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="ExtractedField.id"
    )


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verifications.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    field_name: Mapped[str] = mapped_column(String(64))
    field_value: Mapped[str] = mapped_column(String(255), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source_label: Mapped[str] = mapped_column(String(128), default="")
    page_no: Mapped[int] = mapped_column(Integer, default=1)
    extraction_mode: Mapped[str] = mapped_column(String(16), default=ProcessingMode.MOCK.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    verification: Mapped[Verification] = relationship(back_populates="extracted_fields")
    document: Mapped[Document] = relationship(back_populates="extracted_fields")
    verification_results: Mapped[list["VerificationResult"]] = relationship(
        back_populates="extracted_field"
    )


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verifications.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), index=True
    )
    extracted_field_id: Mapped[int | None] = mapped_column(
        ForeignKey("extracted_fields.id", ondelete="SET NULL"), nullable=True
    )
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(24), default=VerificationOutcome.NOT_VERIFIED.value)
    method: Mapped[str] = mapped_column(String(24), default=VerificationMethod.PRESENCE.value)
    detail: Mapped[str] = mapped_column(Text, default="")
    observed_value: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(128), default="")
    verified_by: Mapped[str] = mapped_column(String(64), default="SYSTEM")
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    verification: Mapped[Verification] = relationship(back_populates="verification_results")
    requirement: Mapped[Requirement] = relationship(back_populates="verification_results")
    extracted_field: Mapped[ExtractedField | None] = relationship(back_populates="verification_results")


class ComplianceResult(Base):
    __tablename__ = "compliance_results"
    __table_args__ = (
        UniqueConstraint("verification_id", "requirement_id", name="uq_compliance_ver_req"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verifications.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(24), default=ComplianceStatus.REVIEW.value)
    reason: Mapped[str] = mapped_column(Text, default="")
    evidence_ref: Mapped[str] = mapped_column(String(255), default="")
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    verification: Mapped[Verification] = relationship(back_populates="compliance_results")
    requirement: Mapped[Requirement] = relationship(back_populates="compliance_results")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (UniqueConstraint("verification_id", name="uq_risk_verification"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verifications.id", ondelete="CASCADE"), index=True
    )
    level: Mapped[str] = mapped_column(String(16), default=RiskLevel.LOW.value)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    verified_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    verification: Mapped[Verification] = relationship(back_populates="risk_assessment")


class OfficerDecision(Base):
    __tablename__ = "officer_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verifications.id", ondelete="CASCADE"), index=True
    )
    decision: Mapped[str] = mapped_column(String(40), default=DecisionType.APPROVED.value)
    comment: Mapped[str] = mapped_column(Text, default="")
    officer_name: Mapped[str] = mapped_column(String(128))
    officer_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    verification: Mapped[Verification] = relationship(back_populates="officer_decisions")


class AuditEvent(Base):
    """Append-only. No update path exists in the service layer."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verifications.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(48), default=AuditEventType.VERIFICATION_CREATED.value)
    actor: Mapped[str] = mapped_column(String(16), default=ActorType.SYSTEM.value)
    stage: Mapped[str] = mapped_column(String(32), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    verification: Mapped[Verification] = relationship(back_populates="audit_events")
