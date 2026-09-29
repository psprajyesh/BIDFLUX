"""Deterministic constants for the SIH demo and the simulated service layer.

Everything here is fixed on purpose: the same tender, bidder, extracted values and
confidence scores must come back on every run so the live demo cannot drift.

The requirement catalogue is *matched against tender text by keyword*. It is not a
hard-coded result: a tender that omits a clause genuinely produces fewer
requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..enums import (
    DocumentType,
    ProcessingMode,
    RequirementCategory,
    VerificationMethod,
)

# --------------------------------------------------------------------------- #
# Demo identity
# --------------------------------------------------------------------------- #

DEMO_TENDER_REFERENCE = "TND/2026/001"
DEMO_TENDER_TITLE = "Supply of Medical Equipment"
DEMO_TENDERER = "Department of Health & Family Welfare"
DEMO_BIDDER_NAME = "ABC Technologies"
DEMO_BIDDER_CODE = "BID-ABC-001"
DEMO_CASE_TITLE = f"{DEMO_TENDER_REFERENCE} - {DEMO_TENDER_TITLE}"

DEMO_TENDER_TEXT = """TENDER NO. TND/2026/001
SUPPLY OF MEDICAL EQUIPMENT

Department of Health & Family Welfare invites sealed bids from eligible vendors
for the supply of medical equipment.

1. The bidder must be registered under GST and must furnish a valid GSTIN
   certificate issued by the competent authority.
2. A valid PAN (Permanent Account Number) card is mandatory.
3. Registration under the Udyam (MSME) portal is required and the Udyam
   registration certificate must be submitted.
4. The bidder must produce an OEM authorisation letter from the manufacturer
   evidencing dealership for the offered make.
5. Minimum experience: the bidder should have completed at least 3 similar
   assignments in the last 7 years. Experience certificates are mandatory.
6. Annual turnover of at least INR 2.5 crore is required during the last three
   financial years, supported by audited financial statements.
7. The equipment offered must conform to the technical specification annexed
   to this tender. Technical specification compliance must be demonstrated.
8. Financial eligibility: the bidder must have a net worth of at least INR 2
   crore as per the latest balance sheet, evidencing financial capacity.

Documents are to be uploaded through the BIDFLUX portal. Bidders must ensure
complete and legible evidence for every requirement.
"""


# --------------------------------------------------------------------------- #
# Requirement catalogue
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RequirementSpec:
    """A canonical tender requirement plus how it is matched and evaluated."""

    code: str
    title: str
    description: str
    category: RequirementCategory
    keywords: tuple[str, ...]
    #: Extracted-field name this requirement is verified against.
    field_name: str
    method: VerificationMethod
    #: Minimum acceptable numeric value (threshold rules only).
    threshold: float | None = None
    is_mandatory: bool = True
    #: Confidence assigned to an AI-extracted requirement.
    confidence: float = 0.94
    #: Field values in the catalogue used by deterministic (mock) extraction.
    demo_values: dict[str, str] = field(default_factory=dict)


REQUIREMENT_CATALOGUE: tuple[RequirementSpec, ...] = (
    RequirementSpec(
        code="GST_REGISTRATION",
        title="GST Registration",
        description="Valid GSTIN certificate issued by the competent authority must be provided.",
        category=RequirementCategory.STATUTORY,
        keywords=("gst", "gstin", "goods and services tax"),
        field_name="GSTIN",
        method=VerificationMethod.FORMAT_CHECK,
        demo_values={"GSTIN": "37XXXXXXXXXX1Z5"},
    ),
    RequirementSpec(
        code="PAN",
        title="PAN",
        description="Permanent Account Number card is mandatory for all bidders.",
        category=RequirementCategory.STATUTORY,
        keywords=("pan", "permanent account number"),
        field_name="PAN",
        method=VerificationMethod.FORMAT_CHECK,
        demo_values={"PAN": "ABCDE1234F"},
    ),
    RequirementSpec(
        code="UDYAM_REGISTRATION",
        title="Udyam Registration",
        description="Udyam (MSME) registration certificate must be submitted.",
        category=RequirementCategory.STATUTORY,
        keywords=("udyam", "msme", "udyog"),
        field_name="Udyam Number",
        method=VerificationMethod.FORMAT_CHECK,
        demo_values={"Udyam Number": "UDYAM-AP-XX-XXXXXXX"},
    ),
    RequirementSpec(
        code="OEM_AUTHORIZATION",
        title="OEM Authorization",
        description="Authorisation letter from the OEM evidencing dealership for the offered make.",
        category=RequirementCategory.TECHNICAL,
        keywords=("oem", "authorisation letter", "authorization letter", "manufacturer"),
        field_name="OEM Reference",
        method=VerificationMethod.PRESENCE,
        demo_values={"OEM Reference": "OEM-ABC-2026-001"},
    ),
    RequirementSpec(
        code="MINIMUM_EXPERIENCE",
        title="Minimum Experience",
        description="At least 3 years of experience in similar supply contracts.",
        category=RequirementCategory.EXPERIENCE,
        keywords=("minimum experience", "years of experience", "experience"),
        field_name="Years of Experience",
        method=VerificationMethod.THRESHOLD,
        threshold=3.0,
        demo_values={"Years of Experience": "8"},
    ),
    RequirementSpec(
        code="TURNOVER",
        title="Turnover",
        description="Annual turnover of at least INR 2.5 crore in the last three financial years.",
        category=RequirementCategory.FINANCIAL,
        keywords=("turnover", "annual turnover", "revenue"),
        field_name="Annual Turnover",
        method=VerificationMethod.THRESHOLD,
        threshold=25_000_000.0,
        demo_values={"Annual Turnover": "48500000"},
    ),
    RequirementSpec(
        code="TECHNICAL_SPECIFICATION",
        title="Technical Specification",
        description="Offered equipment must conform to the annexed technical specification.",
        category=RequirementCategory.TECHNICAL,
        keywords=("technical specification", "technical spec", "specification"),
        field_name="Technical Compliance",
        method=VerificationMethod.PRESENCE,
        demo_values={"Technical Compliance": "Compliant"},
    ),
    RequirementSpec(
        code="FINANCIAL_ELIGIBILITY",
        title="Financial Eligibility",
        description="Net worth of at least INR 2 crore evidenced by the latest balance sheet.",
        category=RequirementCategory.FINANCIAL,
        keywords=("financial eligibility", "net worth", "financial capacity"),
        field_name="Net Worth",
        method=VerificationMethod.THRESHOLD,
        threshold=20_000_000.0,
        demo_values={"Net Worth": "61200000"},
    ),
)

REQUIREMENTS_BY_CODE: dict[str, RequirementSpec] = {r.code: r for r in REQUIREMENT_CATALOGUE}


# --------------------------------------------------------------------------- #
# Simulated OCR / field extraction
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class FieldFixture:
    field_name: str
    field_value: str
    confidence: float
    source_label: str


@dataclass(frozen=True)
class DocumentSpec:
    doc_type: DocumentType
    label: str
    fields: tuple[FieldFixture, ...]
    #: Whether the demo bidder actually submitted this document.
    submitted_in_demo: bool
    filename: str


DOCUMENT_CATALOGUE: tuple[DocumentSpec, ...] = (
    DocumentSpec(
        doc_type=DocumentType.GST_CERTIFICATE,
        label="GST Certificate",
        fields=(
            FieldFixture("GSTIN", "37XXXXXXXXXX1Z5", 0.98, "GST Certificate"),
            FieldFixture("Company", DEMO_BIDDER_NAME, 0.99, "GST Certificate"),
        ),
        submitted_in_demo=True,
        filename="gst-certificate.pdf",
    ),
    DocumentSpec(
        doc_type=DocumentType.PAN_DOCUMENT,
        label="PAN Document",
        fields=(FieldFixture("PAN", "ABCDE1234F", 0.97, "PAN Document"),),
        submitted_in_demo=True,
        filename="pan-document.pdf",
    ),
    DocumentSpec(
        doc_type=DocumentType.UDYAM_CERTIFICATE,
        label="Udyam Certificate",
        fields=(FieldFixture("Udyam Number", "UDYAM-AP-XX-XXXXXXX", 0.96, "Udyam Certificate"),),
        submitted_in_demo=True,
        filename="udyam-certificate.pdf",
    ),
    DocumentSpec(
        doc_type=DocumentType.EXPERIENCE,
        label="Experience Certificate",
        fields=(
            FieldFixture("Years of Experience", "8", 0.95, "Experience Certificate"),
            FieldFixture("Technical Compliance", "Compliant", 0.92, "Experience Certificate"),
        ),
        submitted_in_demo=True,
        filename="experience-certificate.pdf",
    ),
    DocumentSpec(
        doc_type=DocumentType.TURNOVER,
        label="Audited Financial Statements",
        fields=(
            FieldFixture("Annual Turnover", "48500000", 0.95, "Audited Financials"),
            FieldFixture("Net Worth", "61200000", 0.93, "Audited Financials"),
        ),
        submitted_in_demo=True,
        filename="audited-financials.pdf",
    ),
    DocumentSpec(
        doc_type=DocumentType.OEM_AUTHORIZATION,
        label="OEM Authorization Letter",
        fields=(FieldFixture("OEM Reference", "OEM-ABC-2026-001", 0.98, "OEM Authorization Letter"),),
        submitted_in_demo=False,  # <- the single demo exception
        filename="oem-authorization.pdf",
    ),
)

#: Document types the demo bidder is expected to submit (the submission checklist).
EXPECTED_DOCUMENT_TYPES: tuple[DocumentType, ...] = tuple(d.doc_type for d in DOCUMENT_CATALOGUE)

#: What the extraction panel prints for the demo bidder, exactly as specified.
DEMO_EXTRACTION_TABLE: tuple[tuple[str, str, str, float], ...] = (
    ("GSTIN", "37XXXXXXXXXX1Z5", "GST Certificate", 0.98),
    ("PAN", "ABCDE1234F", "PAN Document", 0.97),
    ("Udyam Number", "UDYAM-AP-XX-XXXXXXX", "Udyam Certificate", 0.96),
    ("Company", "ABC Technologies", "GST Certificate", 0.99),
)


# --------------------------------------------------------------------------- #
# Risk weights
# --------------------------------------------------------------------------- #

#: Deterministic additive weights. Chosen so the demo case lands on HIGH.
RISK_WEIGHT_FAIL = 40.0
RISK_WEIGHT_REVIEW = 35.0
RISK_WEIGHT_MISSING_MANDATORY = 20.0
RISK_WEIGHT_LOW_VERIFIED_RATIO = 10.0
RISK_RATIO_THRESHOLD = 0.80

RISK_BANDS: tuple[tuple[float, str], ...] = (
    (75.0, "CRITICAL"),
    (50.0, "HIGH"),
    (25.0, "MEDIUM"),
    (0.0, "LOW"),
)

#: Banner shown on the requirements stage.
AI_VALIDATION_NOTICE = (
    "AI-extracted requirements require officer validation before final use."
)

MODE_LABELS: dict[str, str] = {
    ProcessingMode.MOCK.value: "Simulated extraction (deterministic demo data)",
    ProcessingMode.RULE.value: "Deterministic local rules on uploaded text",
}
