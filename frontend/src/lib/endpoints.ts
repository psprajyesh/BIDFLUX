import { apiGet, apiPost, apiUpload } from "./api";
import type {
  AuditEventOut,
  ComplianceResponse,
  DashboardResponse,
  DemoLoadResponse,
  DemoResetResponse,
  DocumentsResponse,
  DocumentOut,
  EvidenceResponse,
  Health,
  OfficerDecisionOut,
  ProcessResponse,
  RecommendationResponse,
  ReportRow,
  ReportsResponse,
  RiskResponse,
  RunVerificationResponse,
  VerificationDetail,
  VerificationResultOut,
  VerificationSummary,
  WorkflowStateResponse,
} from "./types";

/* ---------------------------------------------------------------- system -- */

export const getHealth = () => apiGet<Health>("/health");
export const getDashboard = () => apiGet<DashboardResponse>("/dashboard");
export const getReports = () => apiGet<ReportsResponse>("/reports/summary");

/* --------------------------------------------------------- verifications -- */

export const listVerifications = (limit = 25) =>
  apiGet<VerificationSummary[]>("/verifications", { limit });

export const createVerification = (body: {
  title: string;
  tender_reference?: string;
  tenderer?: string;
}) => apiPost<VerificationDetail>("/verifications", body);

export const getVerification = (id: string) =>
  apiGet<VerificationDetail>(`/verifications/${id}`);

export const uploadTender = (id: string, form: FormData) =>
  apiUpload<{ message: string; verification_id: string | null }>(
    `/verifications/${id}/tender`,
    form,
  );

export const analyseTender = (id: string) =>
  apiPost<{ message: string; verification_id: string | null }>(
    `/verifications/${id}/tender/analyse`,
  );

export const getDocuments = (id: string) =>
  apiGet<DocumentsResponse>(`/verifications/${id}/documents`);

export const uploadDocument = (id: string, form: FormData): Promise<DocumentOut> =>
  apiUpload(`/verifications/${id}/documents`, form);

export const processDocuments = (id: string) =>
  apiPost<ProcessResponse>(`/verifications/${id}/documents/process`);

export const runVerification = (id: string) =>
  apiPost<RunVerificationResponse>(`/verifications/${id}/verification/run`);

export const getVerificationResults = (id: string) =>
  apiGet<VerificationResultOut[]>(`/verifications/${id}/verification`);

/* ------------------------------------------------------------- workflow -- */

export const getWorkflow = (id: string) =>
  apiGet<WorkflowStateResponse>(`/verifications/${id}/workflow`);

export const getCompliance = (id: string) =>
  apiGet<ComplianceResponse>(`/verifications/${id}/compliance`);

export const getRisk = (id: string) =>
  apiGet<RiskResponse>(`/verifications/${id}/risk`);

export const getRecommendation = (id: string) =>
  apiGet<RecommendationResponse>(`/verifications/${id}/recommendation`);

export const getDecision = (id: string) =>
  apiGet<OfficerDecisionOut | null>(`/verifications/${id}/decision`);

export const submitDecision = (
  id: string,
  body: {
    decision: "APPROVED" | "REJECTED" | "CLARIFICATION_REQUESTED";
    comment: string;
    officer_name: string;
    officer_id: string;
  },
) => apiPost<OfficerDecisionOut>(`/verifications/${id}/decision`, body);

/* ------------------------------------------------- evidence and audit -- */

export const getEvidence = (id: string) =>
  apiGet<EvidenceResponse>(`/verifications/${id}/evidence`);

export const getAuditTrail = (id: string) =>
  apiGet<AuditEventOut[]>(`/verifications/${id}/audit`);

/* ----------------------------------------------------------------- demo -- */

export const loadDemo = () => apiPost<DemoLoadResponse>("/demo/load");

export const resetDemo = () => apiPost<DemoResetResponse>("/demo/reset");

export type { DocumentOut, ReportRow };
