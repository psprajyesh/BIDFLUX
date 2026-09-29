"use client";

import { ShieldAlert, Lightbulb } from "lucide-react";
import { PageShell } from "@/components/shell/PageShell";
import { useActiveCase } from "@/components/shell/CaseProvider";
import { Button } from "@/components/ui/Button";
import { Card, LoadingBar } from "@/components/ui/Card";
import { Callout, ErrorBanner } from "@/components/ui/Callout";
import { RiskBadge, StatusPill } from "@/components/ui/Badge";
import { DataTable, type Column } from "@/components/ui/Table";
import { DecisionPanel } from "@/components/workflow/DecisionPanel";
import { getCompliance, getRecommendation, getRisk, getVerification } from "@/lib/endpoints";
import { formatDateTime } from "@/lib/format";
import { useApiData } from "@/lib/useApiData";
import type {
  ComplianceResponse,
  ComplianceRow,
  RecommendationResponse,
  RiskResponse,
  VerificationDetail,
} from "@/lib/types";

function isNotReady(error: { status?: number } | null): boolean {
  return error?.status === 409 || error?.status === 404;
}

export default function CompliancePage() {
  const { activeId } = useActiveCase();
  const compliance = useApiData<ComplianceResponse>(activeId, () => getCompliance(activeId!));
  const risk = useApiData<RiskResponse>(activeId, () => getRisk(activeId!));
  const recommendation = useApiData<RecommendationResponse>(activeId, () =>
    getRecommendation(activeId!),
  );
  const detail = useApiData<VerificationDetail>(activeId, () => getVerification(activeId!));

  const refreshAll = () => {
    compliance.refresh();
    risk.refresh();
    recommendation.refresh();
    detail.refresh();
  };

  const complianceNotReady = isNotReady(compliance.error);

  return (
    <PageShell
      title="Compliance &amp; Risk"
      subtitle="Computed from stored verification results — not hard-coded"
      requiresCase
      actions={
        <Button variant="secondary" onClick={refreshAll}>
          Recalculate
        </Button>
      }
    >
      <div className="space-y-5">
        {compliance.error && !complianceNotReady ? (
          <ErrorBanner message={compliance.error.message} onRetry={compliance.refresh} />
        ) : null}
        {risk.error && !isNotReady(risk.error) ? (
          <ErrorBanner message={risk.error.message} onRetry={risk.refresh} />
        ) : null}
        {recommendation.error && !isNotReady(recommendation.error) ? (
          <ErrorBanner message={recommendation.error.message} onRetry={recommendation.refresh} />
        ) : null}

        {compliance.data === null ? (
          complianceNotReady ? (
            <Callout tone="warning" title="Verification data is not ready yet">
              <p>
                Compliance needs extracted requirements and recorded verification results. Run the
                verification first, then come back and Recalculate.
              </p>
            </Callout>
          ) : (
            <LoadingBar label="Computing compliance" />
          )
        ) : (
          <ComplianceView
            compliance={compliance.data}
            risk={risk.data}
            recommendation={recommendation.data}
            detail={detail.data}
            verificationId={activeId!}
            onRecorded={refreshAll}
          />
        )}
      </div>
    </PageShell>
  );
}

function ComplianceView({
  compliance,
  risk,
  recommendation,
  detail,
  verificationId,
  onRecorded,
}: {
  compliance: ComplianceResponse;
  risk: RiskResponse | null;
  recommendation: RecommendationResponse | null;
  detail: VerificationDetail | null;
  verificationId: string;
  onRecorded: () => void;
}) {
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-4">
              <Metric label="Pass" value={compliance.pass_count} tone="success" />
              <Metric label="Fail" value={compliance.fail_count} tone="danger" />
              <Metric label="Review" value={compliance.review_count} tone="warning" />
              <Metric
                label="Risk"
                value={risk ? risk.level : "—"}
                tone={
                  risk?.level === "LOW"
                    ? "success"
                    : risk?.level === "MEDIUM"
                      ? "warning"
                      : risk?.level === "HIGH" || risk?.level === "CRITICAL"
                        ? "danger"
                        : "neutral"
                }
              />
            </div>

            {risk ? (
              <div className="grid gap-5 lg:grid-cols-3">
                <Card title="Risk assessment" className="lg:col-span-2">
                  <div className="flex flex-wrap items-center gap-3">
                    <RiskBadge level={risk.level} />
                    <span className="numeric text-[13px] text-slate-600">
                      Score {risk.score} · {risk.verified_count}/{risk.total_count} requirements
                      verified
                    </span>
                    <span className="ml-auto text-[11px] text-slate-400">
                      {formatDateTime(risk.computed_at)}
                    </span>
                  </div>

                  <div className="mt-4">
                    <div className="h-1.5 w-full rounded-full bg-slate-200 overflow-hidden">
                      <div
                        className={
                          risk.level === "LOW"
                            ? "h-full bg-emerald-600"
                            : risk.level === "MEDIUM"
                              ? "h-full bg-amber-500"
                              : "h-full bg-red-600"
                        }
                        style={{ width: `${Math.min(100, Math.max(0, risk.score))}%` }}
                      />
                    </div>
                  </div>

                  <p className="mt-4 text-[11px] font-medium uppercase tracking-[0.04em] text-slate-500">
                    Reasons
                  </p>
                  <ul className="mt-2 space-y-1.5">
                    {risk.reasons.map((reason) => (
                      <li key={reason} className="flex gap-2 text-[13px] text-slate-700">
                        <ShieldAlert size={14} className="mt-1 shrink-0 text-amber-600" aria-hidden />
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>

                  {risk.signals.length > 0 ? (
                    <div className="mt-4 border-t border-slate-100 pt-3">
                      <p className="text-[11px] font-medium uppercase tracking-[0.04em] text-slate-500">
                        Risk drivers
                      </p>
                      <ul className="mt-2 space-y-1.5">
                        {risk.signals.map((signal) => (
                          <li
                            key={signal.code}
                            className="flex items-center gap-2 text-[12px] text-slate-600"
                          >
                            <span className="badge tone-warning">
                              {signal.weight > 0 ? `+${signal.weight}` : String(signal.weight)}
                            </span>
                            <span>{signal.message}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </Card>

                {recommendation ? (
                  <Card title="Recommendation">
                    <div className="flex items-start gap-2">
                      <Lightbulb size={16} className="mt-0.5 shrink-0 text-amber-500" aria-hidden />
                      <div className="min-w-0">
                        <p className="font-semibold text-slate-900">{recommendation.headline}</p>
                        <p className="mt-1 font-mono text-[11px] text-slate-500">
                          {recommendation.code} · mode {recommendation.mode}
                        </p>
                      </div>
                    </div>
                    <ul className="mt-4 space-y-1.5">
                      {recommendation.rationale.map((line) => (
                        <li key={line} className="flex gap-2 text-[13px] text-slate-600">
                          <span aria-hidden className="text-slate-300">
                            –
                          </span>
                          <span>{line}</span>
                        </li>
                      ))}
                    </ul>
                    <p className="mt-4 border-t border-slate-100 pt-3 text-[11px] text-slate-400">
                      The recommendation is advisory. The officer decision is the only binding
                      outcome.
                    </p>
                  </Card>
                ) : null}
              </div>
            ) : null}

            {compliance.rows.length === 0 ? (
              <Callout tone="warning" title="No compliance results yet">
                Run the verification on the verification page first.
              </Callout>
            ) : (
              <Card
                title={`Requirement compliance (${compliance.total})`}
                actions={
                  <span className="text-[11px] text-slate-500">
                    {formatDateTime(compliance.computed_at)}
                  </span>
                }
                padded={false}
              >
                <DataTable<ComplianceRow>
                  columns={columns}
                  rows={compliance.rows}
                  rowKey={(row) => String(row.requirement_id)}
                />
              </Card>
            )}

            {detail ? (
              <DecisionPanel
                verificationId={verificationId}
                lockedReason={
                  detail.has_risk
                    ? null
                    : "Assess the risk on this page first — the pipeline reads compliance, then risk, then recommendation before an officer can record a decision."
                }
                onRecorded={onRecorded}
              />
            ) : null}
    </>
  );
}

const columns: Column<ComplianceRow>[] = [
  {
    key: "code",
    header: "Code",
    width: "190px",
    render: (row) => <span className="font-mono text-[12px] text-slate-600">{row.requirement_code}</span>,
  },
  {
    key: "title",
    header: "Requirement",
    render: (row) => (
      <div className="min-w-0">
        <p className="font-medium text-slate-900">{row.requirement_title}</p>
        <p className="text-[11px] text-slate-500">{row.category}</p>
      </div>
    ),
  },
  {
    key: "status",
    header: "Status",
    align: "center",
    width: "110px",
    render: (row) => <StatusPill status={row.status} label={row.status} />,
  },
  {
    key: "observed",
    header: "Observed",
    width: "140px",
    render: (row) =>
      row.observed_value ? (
        <span className="font-mono text-[12px] text-slate-700">{row.observed_value}</span>
      ) : (
        <span className="text-slate-400">—</span>
      ),
  },
  {
    key: "reason",
    header: "Reason",
    render: (row) => <span className="text-[12px] text-slate-600">{row.reason}</span>,
  },
];

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | string;
  tone: "success" | "warning" | "danger" | "neutral";
}) {
  const accent = {
    neutral: "text-slate-900",
    success: "text-emerald-700",
    warning: "text-amber-700",
    danger: "text-red-700",
  }[tone];

  return (
    <div className="bg-white border border-slate-200 rounded-lg px-4 py-3.5">
      <p className="text-[11px] font-medium uppercase tracking-[0.04em] text-slate-500">{label}</p>
      <p className={`mt-1 text-[26px] font-semibold leading-8 numeric ${accent}`}>{value}</p>
    </div>
  );
}
