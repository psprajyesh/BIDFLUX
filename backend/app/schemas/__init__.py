"""Pydantic request/response contracts mirroring the ORM models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..enums import DecisionType, DocumentType, RequirementCategory


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #


class VerificationCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    tender_reference: str = Field(default="", max_length=64)
    tenderer: str = Field(default="", max_length=255)

    @field_validator("title", "tenderer")
    @classmethod
    def _strip(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned and v:
            raise ValueError("must not be blank")
        return cleaned


class RequirementCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(default="", max_length=2000)
    category: RequirementCategory = RequirementCategory.STATUTORY
    is_mandatory: bool = True
    threshold_value: float | None = None


class DocumentUploadMeta(BaseModel):
    doc_type: DocumentType = DocumentType.OTHER
    label: str = Field(default="", max_length=255)


class OfficerDecisionCreate(BaseModel):
    """All four fields are mandatory. The officer is the only decision authority."""

    decision: DecisionType
    comment: str = Field(min_length=10, max_length=2000)
    officer_name: str = Field(min_length=3, max_length=128)
    officer_id: str = Field(min_length=3, max_length=64)

    @field_validator("comment", "officer_name", "officer_id")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 3:
            raise ValueError("must not be blank")
        return cleaned


# --------------------------------------------------------------------------- #
# Responses
# --------------------------------------------------------------------------- #


class HealthResponse(BaseModel):
    status: str
    app_name: str
    api_version: str
    app_env: str
    ai_mode: str
    capabilities: dict[str, str]


class VerificationSummary(ORMModel):
    id: str
    title: str
    tender_reference: str
    tenderer: str
    status: str
    current_step: str
    is_demo: bool
    bidder_name: str | None = None
    tender_title: str | None = None
    risk_level: str | None = None
    risk_score: float | None = None
    compliance_pass: int | None = None
    compliance_total: int | None = None
    decision: str | None = None
    created_at: datetime
    updated_at: datetime


class VerificationDetail(VerificationSummary):
    tender: "TenderOut | None" = None
    bidder: "BidderOut | None" = None
    requirements: list["RequirementOut"] = Field(default_factory=list)
    document_count: int = 0
    processed_document_count: int = 0
    verified_count: int = 0
    total_requirements: int = 0
    exception_count: int = 0
    audit_event_count: int = 0
    has_verification: bool = False
    has_compliance: bool = False
    has_risk: bool = False
    has_recommendation: bool = False
    has_decision: bool = False


class TenderOut(ORMModel):
    id: int
    reference_no: str
    title: str
    file_name: str
    file_size: int
    content_type: str
    analysis_mode: str
    requirement_count: int = 0
    created_at: datetime


class BidderOut(ORMModel):
    id: int
    name: str
    code: str
    document_count: int = 0


class RequirementOut(ORMModel):
    id: int
    code: str
    title: str
    description: str
    category: str
    is_mandatory: bool
    source: str
    confidence: float
    threshold_value: float | None
    sort_order: int
    validated_by_officer: bool


class DocumentOut(ORMModel):
    id: int
    doc_type: str
    label: str
    file_name: str
    file_size: int
    content_type: str
    status: str
    processing_mode: str
    checksum: str
    processed_at: datetime | None
    created_at: datetime
    extracted_fields: list["ExtractedFieldOut"] = Field(default_factory=list)


class ExtractedFieldOut(ORMModel):
    id: int
    field_name: str
    field_value: str
    confidence: float
    source_label: str
    page_no: int
    extraction_mode: str
    document_id: int
    document_label: str = ""


class VerificationResultOut(ORMModel):
    id: int
    requirement_id: int
    status: str
    method: str
    detail: str
    observed_value: str
    source: str
    verified_by: str
    verified_at: datetime
    document_id: int | None = None
    extracted_field_id: int | None = None
    #: Resolved from the related Requirement by the router (not an ORM column).
    requirement_code: str = ""
    requirement_title: str = ""
    category: str = ""
    is_mandatory: bool = True


class ComplianceRow(ORMModel):
    requirement_id: int
    requirement_code: str
    requirement_title: str
    category: str
    is_mandatory: bool
    status: str
    reason: str
    evidence_ref: str
    verification_status: str
    observed_value: str
    computed_at: datetime


class ComplianceResponse(BaseModel):
    verification_id: str
    rows: list[ComplianceRow]
    pass_count: int
    fail_count: int
    review_count: int
    not_applicable_count: int
    total: int
    computed_at: datetime


class RiskReason(BaseModel):
    code: str
    message: str
    weight: float


class RiskResponse(BaseModel):
    verification_id: str
    level: str
    score: float
    reasons: list[str]
    signals: list[RiskReason]
    verified_count: int
    total_count: int
    computed_at: datetime


class RecommendationResponse(BaseModel):
    verification_id: str
    code: str
    headline: str
    rationale: list[str]
    mode: str
    risk_level: str
    verified_count: int
    total_count: int
    generated_at: datetime


class OfficerDecisionOut(ORMModel):
    id: int
    verification_id: str
    decision: str
    comment: str
    officer_name: str
    officer_id: str
    created_at: datetime


class AuditEventOut(ORMModel):
    id: int
    event_type: str
    actor: str
    stage: str
    message: str
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_json")
    created_at: datetime


class EvidenceLevel(BaseModel):
    level: int
    entity: str
    label: str
    title: str
    detail: str
    status: str | None = None
    ref_id: int | None = None


class EvidenceResponse(BaseModel):
    verification_id: str
    bidder: BidderOut | None = None
    levels: list[EvidenceLevel]
    chains: list["EvidenceChainOut"]
    compliance_status: str | None = None
    generated_at: datetime


class EvidenceChainOut(BaseModel):
    document_id: int
    document_label: str
    doc_type: str
    field_name: str
    field_value: str
    confidence: float
    requirement_code: str
    requirement_title: str
    verification_status: str
    verification_detail: str
    compliance_status: str
    compliance_reason: str


class DashboardResponse(BaseModel):
    total_verifications: int
    pending_review: int
    high_risk_cases: int
    completed_decisions: int
    compliance_rate: float
    demo_cases: int
    recent: list[VerificationSummary]
    capability_notice: str


class ReportRow(BaseModel):
    verification_id: str
    title: str
    tender_reference: str
    bidder: str | None
    status: str
    risk_level: str | None
    risk_score: float | None
    verified_count: int
    total_requirements: int
    decision: str | None
    updated_at: datetime


class ReportsResponse(BaseModel):
    rows: list[ReportRow]
    total: int
    generated_at: datetime


class DemoLoadResponse(BaseModel):
    verification_id: str
    tender_reference: str
    tender_title: str
    bidder_name: str
    requirements: int
    documents: int
    reset_performed: bool
    message: str


class DemoResetResponse(BaseModel):
    deleted_verifications: int
    message: str


class StepState(BaseModel):
    key: str
    label: str
    index: int
    state: str
    complete: bool
    active: bool


class WorkflowStateResponse(BaseModel):
    verification_id: str
    current_step: str
    step_index: int
    status: str
    steps: list[StepState]
    has_tender: bool
    has_requirements: bool
    has_documents: bool
    documents_processed: bool
    has_verification: bool
    has_compliance: bool
    has_risk: bool
    has_recommendation: bool
    has_decision: bool


class MessageResponse(BaseModel):
    message: str
    verification_id: str | None = None


class ProcessResponse(BaseModel):
    message: str
    verification_id: str
    documents_processed: int
    fields_extracted: int
    mode: str


class RunVerificationResponse(BaseModel):
    message: str
    verification_id: str
    results: int
    verified: int
    missing: int
    mode: str


VerificationDetail.model_rebuild()
DocumentOut.model_rebuild()
EvidenceResponse.model_rebuild()
