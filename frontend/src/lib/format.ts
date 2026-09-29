import type {
  ComplianceStatus,
  DecisionType,
  RiskLevel,
  VerificationStatus,
} from "./types";

/**
 * Parse an API timestamp. SQLite drops the timezone flag, so a value written
 * as UTC can come back with no "Z"; treat anything without a zone as UTC to
 * keep every badge on the same clock after a reload.
 */
function parseApiDate(value: string): Date {
  if (/(?:Z|[+-]\d{2}:?\d{2})$/.test(value)) return new Date(value);
  return new Date(`${value}Z`);
}

/** ISO timestamp -> "29 Sep 2026, 11:42". Falls back to the raw value. */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

/** Large rupee amounts as Indian-format crores, e.g. 48500000 -> "₹4.85 Cr". */
export function formatInr(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  if (Math.abs(numeric) >= 10_000_000) return `₹${(numeric / 10_000_000).toFixed(2)} Cr`;
  if (Math.abs(numeric) >= 100_000) return `₹${(numeric / 100_000).toFixed(2)} L`;
  return `₹${numeric.toLocaleString("en-IN")}`;
}

export function titleCase(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

/** Human label for a verification status. */
export const STATUS_LABELS: Record<VerificationStatus, string> = {
  DRAFT: "Draft",
  TENDER_UPLOADED: "Tender uploaded",
  REQUIREMENTS_EXTRACTED: "Requirements extracted",
  DOCUMENTS_UPLOADED: "Documents uploaded",
  DOCUMENTS_PROCESSED: "Documents processed",
  VERIFICATION_COMPLETE: "Verification complete",
  COMPLIANCE_READY: "Compliance ready",
  REVIEW_REQUIRED: "Review required",
  FINAL_DECISION: "Final decision",
};

export function statusTone(status: string): "success" | "warning" | "danger" | "info" | "neutral" | "mock" {
  switch (status) {
    case "FINAL_DECISION":
    case "PASS":
    case "VERIFIED":
      return "success";
    case "REVIEW_REQUIRED":
    case "REVIEW":
    case "MISSING":
      return "warning";
    case "FAIL":
    case "INVALID":
    case "MISMATCH":
    case "REJECTED":
      return "danger";
    case "DRAFT":
    case "PENDING":
    case "NOT_VERIFIED":
      return "neutral";
    default:
      return "info";
  }
}

export function complianceTone(status: ComplianceStatus | string) {
  switch (status) {
    case "PASS":
      return "success" as const;
    case "FAIL":
      return "danger" as const;
    case "REVIEW":
      return "warning" as const;
    default:
      return "neutral" as const;
  }
}

export function riskTone(level: RiskLevel | string | null) {
  switch (level) {
    case "LOW":
      return "success" as const;
    case "MEDIUM":
      return "warning" as const;
    case "HIGH":
      return "danger" as const;
    case "CRITICAL":
      return "danger" as const;
    default:
      return "neutral" as const;
  }
}

export function decisionTone(decision: string | null) {
  switch (decision) {
    case "APPROVED":
      return "success" as const;
    case "REJECTED":
      return "danger" as const;
    case "CLARIFICATION_REQUESTED":
      return "warning" as const;
    default:
      return "neutral" as const;
  }
}

export const DECISION_LABELS: Record<DecisionType, string> = {
  APPROVED: "Approved",
  REJECTED: "Rejected",
  CLARIFICATION_REQUESTED: "Clarification requested",
};

export function decisionLabel(decision: DecisionType | string | null | undefined): string {
  if (!decision) return "Pending";
  return DECISION_LABELS[decision as DecisionType] ?? decision;
}

export const DOC_TYPE_LABELS: Record<string, string> = {
  GST_CERTIFICATE: "GST Certificate",
  PAN_DOCUMENT: "PAN Document",
  UDYAM_CERTIFICATE: "Udyam Certificate",
  OEM_AUTHORIZATION: "OEM Authorization Letter",
  EXPERIENCE: "Experience Certificate",
  TURNOVER: "Audited Financial Statements",
  TECHNICAL_SPECIFICATION: "Technical Specification",
  FINANCIAL_ELIGIBILITY: "Financial Eligibility",
  OTHER: "Other Document",
};
