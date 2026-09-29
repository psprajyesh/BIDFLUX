"""Status and mode constants for the BIDFLUX workflow.

Every enum here is persisted by *value*, so renaming a member's label is safe but
renaming the value itself would break existing rows.
"""

from __future__ import annotations

from enum import StrEnum


class VerificationStatus(StrEnum):
    DRAFT = "DRAFT"
    TENDER_UPLOADED = "TENDER_UPLOADED"
    REQUIREMENTS_EXTRACTED = "REQUIREMENTS_EXTRACTED"
    DOCUMENTS_UPLOADED = "DOCUMENTS_UPLOADED"
    DOCUMENTS_PROCESSED = "DOCUMENTS_PROCESSED"
    VERIFICATION_COMPLETE = "VERIFICATION_COMPLETE"
    COMPLIANCE_READY = "COMPLIANCE_READY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FINAL_DECISION = "FINAL_DECISION"


class RequirementSource(StrEnum):
    AI_EXTRACTED = "AI_EXTRACTED"
    MANUAL = "MANUAL"


class RequirementCategory(StrEnum):
    STATUTORY = "STATUTORY"
    EXPERIENCE = "EXPERIENCE"
    FINANCIAL = "FINANCIAL"
    TECHNICAL = "TECHNICAL"


class DocumentType(StrEnum):
    GST_CERTIFICATE = "GST_CERTIFICATE"
    PAN_DOCUMENT = "PAN_DOCUMENT"
    UDYAM_CERTIFICATE = "UDYAM_CERTIFICATE"
    OEM_AUTHORIZATION = "OEM_AUTHORIZATION"
    EXPERIENCE = "EXPERIENCE"
    TURNOVER = "TURNOVER"
    TECHNICAL_SPECIFICATION = "TECHNICAL_SPECIFICATION"
    FINANCIAL_ELIGIBILITY = "FINANCIAL_ELIGIBILITY"
    OTHER = "OTHER"


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSED = "PROCESSED"
    REJECTED = "REJECTED"


class ProcessingMode(StrEnum):
    """How a document's fields were produced.

    MOCK  -> simulated OCR / LLM extraction, not a real model
    RULE  -> deterministic local rule (format + checksum), no network call
    """

    MOCK = "MOCK"
    RULE = "RULE"


class VerificationOutcome(StrEnum):
    VERIFIED = "VERIFIED"
    MISSING = "MISSING"
    INVALID = "INVALID"
    MISMATCH = "MISMATCH"
    NOT_VERIFIED = "NOT_VERIFIED"


class VerificationMethod(StrEnum):
    FORMAT_CHECK = "FORMAT_CHECK"
    PRESENCE = "PRESENCE"
    THRESHOLD = "THRESHOLD"


class ComplianceStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DecisionType(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLARIFICATION_REQUESTED = "CLARIFICATION_REQUESTED"


class ActorType(StrEnum):
    SYSTEM = "SYSTEM"
    OFFICER = "OFFICER"


class AuditEventType(StrEnum):
    VERIFICATION_CREATED = "VERIFICATION_CREATED"
    TENDER_UPLOADED = "TENDER_UPLOADED"
    REQUIREMENTS_EXTRACTED = "REQUIREMENTS_EXTRACTED"
    DOCUMENTS_UPLOADED = "DOCUMENTS_UPLOADED"
    DOCUMENTS_PROCESSED = "DOCUMENTS_PROCESSED"
    DOCUMENT_EXTRACTION_COMPLETED = "DOCUMENT_EXTRACTION_COMPLETED"
    FIELD_VERIFIED = "FIELD_VERIFIED"
    DOCUMENT_MISSING = "DOCUMENT_MISSING"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    COMPLIANCE_CALCULATED = "COMPLIANCE_CALCULATED"
    RISK_CALCULATED = "RISK_CALCULATED"
    RECOMMENDATION_GENERATED = "RECOMMENDATION_GENERATED"
    OFFICER_REVIEW_OPENED = "OFFICER_REVIEW_OPENED"
    OFFICER_DECISION_RECORDED = "OFFICER_DECISION_RECORDED"
    DEMO_DATA_LOADED = "DEMO_DATA_LOADED"
    DEMO_DATA_RESET = "DEMO_DATA_RESET"


#: Human-facing labels for the workflow stepper. Index == step order.
WORKFLOW_STEPS: tuple[str, ...] = (
    "Tender",
    "Requirements",
    "Documents",
    "Extraction",
    "Verification",
    "Compliance",
    "Risk",
    "Review",
    "Decision",
)

#: Source string shown next to every verification result. Deliberately states that
#: no government registry was contacted.
LOCAL_RULE_SOURCE = "LOCAL_RULE (no government API)"

#: Default officer identity recorded when the demo runs unattended.
DEMO_OFFICER_NAME = "R. Venkateswara Rao"
DEMO_OFFICER_ID = "OFF-2026-0417"
