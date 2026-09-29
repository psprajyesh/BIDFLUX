/**
 * Response types mirroring the FastAPI schemas in `backend/app/schemas`.
 * Keep these in step with the Pydantic models.
 */

export type VerificationStatus =
  | "DRAFT"
  | "TENDER_UPLOADED"
  | "REQUIREMENTS_EXTRACTED"
  | "DOCUMENTS_UPLOADED"
  | "DOCUMENTS_PROCESSED"
  | "VERIFICATION_COMPLETE"
  | "COMPLIANCE_READY"
  | "REVIEW_REQUIRED"
  | "FINAL_DECISION";

export type ComplianceStatus = "PASS" | "FAIL" | "REVIEW" | "NOT_APPLICABLE";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type VerificationOutcome = "VERIFIED" | "MISSING" | "INVALID" | "MISMATCH" | "NOT_VERIFIED";
export type DecisionType = "APPROVED" | "REJECTED" | "CLARIFICATION_REQUESTED";
export type DocumentType =
  | "GST_CERTIFICATE"
  | "PAN_DOCUMENT"
  | "UDYAM_CERTIFICATE"
  | "OEM_AUTHORIZATION"
  | "EXPERIENCE"
  | "TURNOVER"
  | "TECHNICAL_SPECIFICATION"
  | "FINANCIAL_ELIGIBILITY"
  | "OTHER";

export interface Health {
  status: string;
  app_name: string;
  api_version: string;
  app_env: string;
  ai_mode: string;
  capabilities: Record<string, string>;
}

export interface TenderOut {
  id: number;
  reference_no: string;
  title: string;
  file_name: string;
  file_size: number;
  content_type: string;
  analysis_mode: string;
  requirement_count: number;
  created_at: string;
}

export interface BidderOut {
  id: number;
  name: string;
  code: string;
  document_count: number;
}

export interface RequirementOut {
  id: number;
  code: string;
  title: string;
  description: string;
  category: string;
  is_mandatory: boolean;
  source: string;
  confidence: number;
  threshold_value: number | null;
  sort_order: number;
  validated_by_officer: boolean;
}

export interface ExtractedFieldOut {
  id: number;
  field_name: string;
  field_value: string;
  confidence: number;
  source_label: string;
  page_no: number;
  extraction_mode: string;
  document_id: number;
  document_label: string;
}

export interface DocumentOut {
  id: number;
  doc_type: DocumentType;
  label: string;
  file_name: string;
  file_size: number;
  content_type: string;
  status: string;
  processing_mode: string;
  checksum: string;
  processed_at: string | null;
  created_at: string;
  extracted_fields: ExtractedFieldOut[];
}

export interface VerificationSummary {
  id: string;
  title: string;
  tender_reference: string;
  tenderer: string;
  status: VerificationStatus;
  current_step: string;
  is_demo: boolean;
  bidder_name: string | null;
  tender_title: string | null;
  risk_level: RiskLevel | null;
  risk_score: number | null;
  compliance_pass: number | null;
  compliance_total: number | null;
  decision: DecisionType | null;
  created_at: string;
  updated_at: string;
}

export interface VerificationDetail extends VerificationSummary {
  tender: TenderOut | null;
  bidder: BidderOut | null;
  requirements: RequirementOut[];
  document_count: number;
  processed_document_count: number;
  verified_count: number;
  total_requirements: number;
  exception_count: number;
  audit_event_count: number;
  has_verification: boolean;
  has_compliance: boolean;
  has_risk: boolean;
  has_recommendation: boolean;
  has_decision: boolean;
}

export interface VerificationResultOut {
  id: number;
  requirement_id: number;
  requirement_code: string;
  requirement_title: string;
  category: string;
  is_mandatory: boolean;
  status: VerificationOutcome;
  method: string;
  detail: string;
  observed_value: string;
  source: string;
  verified_by: string;
  verified_at: string;
}

export interface ComplianceRow {
  requirement_id: number;
  requirement_code: string;
  requirement_title: string;
  category: string;
  is_mandatory: boolean;
  status: ComplianceStatus;
  reason: string;
  evidence_ref: string;
  verification_status: string;
  observed_value: string;
  computed_at: string;
}

export interface ComplianceResponse {
  verification_id: string;
  rows: ComplianceRow[];
  pass_count: number;
  fail_count: number;
  review_count: number;
  not_applicable_count: number;
  total: number;
  computed_at: string;
}

export interface RiskSignal {
  code: string;
  message: string;
  weight: number;
}

export interface RiskResponse {
  verification_id: string;
  level: RiskLevel;
  score: number;
  reasons: string[];
  signals: RiskSignal[];
  verified_count: number;
  total_count: number;
  computed_at: string;
}

export interface RecommendationResponse {
  verification_id: string;
  code: string;
  headline: string;
  rationale: string[];
  mode: string;
  risk_level: RiskLevel;
  verified_count: number;
  total_count: number;
  generated_at: string;
}

export interface OfficerDecisionOut {
  id: number;
  verification_id: string;
  decision: DecisionType;
  comment: string;
  officer_name: string;
  officer_id: string;
  created_at: string;
}

export interface AuditEventOut {
  id: number;
  event_type: string;
  actor: string;
  stage: string;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface EvidenceLevel {
  level: number;
  entity: string;
  label: string;
  title: string;
  detail: string;
  status: string | null;
  ref_id: number | null;
}

export interface EvidenceChainOut {
  document_id: number;
  document_label: string;
  doc_type: string;
  field_name: string;
  field_value: string;
  confidence: number;
  requirement_code: string;
  requirement_title: string;
  verification_status: string;
  verification_detail: string;
  compliance_status: ComplianceStatus;
  compliance_reason: string;
}

export interface EvidenceResponse {
  verification_id: string;
  bidder: BidderOut | null;
  levels: EvidenceLevel[];
  chains: EvidenceChainOut[];
  compliance_status: string | null;
  generated_at: string;
}

export interface StepState {
  key: string;
  label: string;
  index: number;
  state: "complete" | "active" | "pending";
  complete: boolean;
  active: boolean;
}

export interface WorkflowStateResponse {
  verification_id: string;
  current_step: string;
  step_index: number;
  status: VerificationStatus;
  steps: StepState[];
  has_tender: boolean;
  has_requirements: boolean;
  has_documents: boolean;
  documents_processed: boolean;
  has_verification: boolean;
  has_compliance: boolean;
  has_risk: boolean;
  has_recommendation: boolean;
  has_decision: boolean;
}

export interface DashboardResponse {
  total_verifications: number;
  pending_review: number;
  high_risk_cases: number;
  completed_decisions: number;
  compliance_rate: number;
  demo_cases: number;
  recent: VerificationSummary[];
  capability_notice: string;
}

export interface ReportRow {
  verification_id: string;
  title: string;
  tender_reference: string;
  bidder: string | null;
  status: VerificationStatus;
  risk_level: RiskLevel | null;
  risk_score: number | null;
  verified_count: number;
  total_requirements: number;
  decision: DecisionType | null;
  updated_at: string;
}

export interface ReportsResponse {
  rows: ReportRow[];
  total: number;
  generated_at: string;
}

export interface DemoLoadResponse {
  verification_id: string;
  tender_reference: string;
  tender_title: string;
  bidder_name: string;
  requirements: number;
  documents: number;
  reset_performed: boolean;
  message: string;
}

export interface DocumentsResponse {
  verification_id: string;
  documents: DocumentOut[];
  missing_expected: string[];
}

export interface ProcessResponse {
  message: string;
  verification_id: string;
  documents_processed: number;
  fields_extracted: number;
  mode: string;
}

export interface RunVerificationResponse {
  message: string;
  verification_id: string;
  results: number;
  verified: number;
  missing: number;
  mode: string;
}

export interface DemoResetResponse {
  deleted_verifications: number;
  message: string;
}

export interface TenderResponse {
  tender: TenderOut;
  requirements: RequirementOut[];
  notice: string;
}

export interface ApiErrorBody {
  error: { code: string; message: string; detail: unknown };
}
