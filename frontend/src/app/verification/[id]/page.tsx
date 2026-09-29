"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Play, Scale, FolderOpen, Link2, ScrollText } from "lucide-react";
import { PageShell } from "@/components/shell/PageShell";
import { useActiveCase } from "@/components/shell/CaseProvider";
import { Button } from "@/components/ui/Button";
import { Card, LoadingBar } from "@/components/ui/Card";
import { Callout, ErrorBanner, MockNotice } from "@/components/ui/Callout";
import { ConfidenceBar, RiskBadge, StatusPill } from "@/components/ui/Badge";
import { DataTable, KeyValue, type Column } from "@/components/ui/Table";
import { WorkflowStepper } from "@/components/workflow/WorkflowStepper";
import { DecisionPanel } from "@/components/workflow/DecisionPanel";
import {
  getVerification,
  getVerificationResults,
  getWorkflow,
  runVerification,
} from "@/lib/endpoints";
import { STATUS_LABELS, decisionLabel, formatBytes, formatDateTime, formatInr, titleCase } from "@/lib/format";
import { useApiData } from "@/lib/useApiData";
import type {
  RequirementOut,
  VerificationDetail,
  VerificationResultOut,
  WorkflowStateResponse,
} from "@/lib/types";

export default function VerificationDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const search = useSearchParams();
  const created = search.get("created");
  const { setActiveId } = useActiveCase();

  const { data: detail, error: detailError, refresh } = useApiData<VerificationDetail | null>(
    id,
    () => getVerification(id),
  );
  const { data: workflow } = useApiData<WorkflowStateResponse | null>(id, () => getWorkflow(id));
  const { data: resultsData } = useApiData<VerificationResultOut[]>(`${id}-results`, () =>
    getVerificationResults(id),
  );
  const results = resultsData && resultsData.length > 0 ? resultsData : null;

  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    setActiveId(id);
  }, [id, setActiveId]);

  async function onRunVerification() {
    setBusy("verify");
    setActionError(null);
    try {
      const result = await runVerification(id);
      setNotice(result.message);
      refresh();
    } catch (err) {
      setActionError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <PageShell
      title={detail?.title ?? "Verification"}
      subtitle={detail ? `${detail.tender_reference || detail.id} · ${detail.bidder_name ?? "no bidder"}` : id}
      actions={
        <>
          <Button variant="secondary" onClick={refresh}>
            Refresh
          </Button>
          <Link href="/documents">
            <Button variant="primary">
              <FolderOpen size={15} aria-hidden />
              Documents
            </Button>
          </Link>
        </>
      }
    >
      <div className="space-y-5">
        {detailError ? <ErrorBanner message={detailError.message} onRetry={refresh} /> : null}
        {actionError ? <ErrorBanner message={actionError} /> : null}
        {created ? <Callout tone="success">{created}</Callout> : null}
        {notice ? <Callout tone="info">{notice}</Callout> : null}

        {workflow ? (
          <Card title={`Workflow — ${workflow.current_step}`}>
            <WorkflowStepper workflow={workflow} />
          </Card>
        ) : null}

        {detail === null && !detailError ? (
          <LoadingBar label="Loading verification" />
        ) : detail === null ? null : (
          <>
            <div className="grid gap-5 lg:grid-cols-3">
              <Card title="Tender" className="lg:col-span-2">
                {detail.tender ? (
                  <KeyValue
                    items={[
                      { label: "Reference", value: detail.tender.reference_no },
                      { label: "Title", value: detail.tender.title },
                      { label: "File", value: detail.tender.file_name },
                      { label: "Size", value: formatBytes(detail.tender.file_size) },
                      {
                        label: "Requirements",
                        value: String(detail.tender.requirement_count),
                      },
                      { label: "Uploaded", value: formatDateTime(detail.tender.created_at) },
                    ]}
                  />
                ) : (
                  <p className="text-[13px] text-slate-500">No tender attached yet.</p>
                )}

                <div className="mt-5 border-t border-slate-100 pt-4">
                  <KeyValue
                    items={[
                      { label: "Status", value: <StatusPill status={detail.status} label={STATUS_LABELS[detail.status] ?? detail.status} /> },
                      { label: "Risk", value: <RiskBadge level={detail.risk_level} /> },
                      {
                        label: "Verified",
                        value: `${detail.verified_count} / ${detail.total_requirements}`,
                      },
                      { label: "Documents", value: `${detail.processed_document_count} / ${detail.document_count}` },
                      { label: "Decision", value: decisionLabel(detail.decision) },
                      { label: "Updated", value: formatDateTime(detail.updated_at) },
                    ]}
                  />
                </div>
              </Card>

              <Card title="Run verification" className="flex flex-col">
                <p className="text-[13px] text-slate-600">
                  Checks every requirement against the extracted document fields and records one
                  audit event per result.
                </p>
                <div className="mt-4 space-y-2">
                  <Button
                    variant="primary"
                    onClick={onRunVerification}
                    loading={busy === "verify"}
                    disabled={detail.document_count === 0}
                    title={detail.document_count === 0 ? "Upload and process bidder documents first" : undefined}
                    className="w-full"
                  >
                    <Play size={15} aria-hidden />
                    Run verification
                  </Button>
                  <Link href="/compliance">
                    <Button variant="secondary" className="w-full">
                      <Scale size={15} aria-hidden />
                      Compliance &amp; risk
                    </Button>
                  </Link>
                </div>
                <div className="mt-auto space-y-2 pt-4">
                  <Link
                    href="/evidence"
                    className="flex items-center gap-2 text-[12px] text-slate-500 hover:text-brand-700"
                  >
                    <Link2 size={13} aria-hidden />
                    Evidence chain
                  </Link>
                  <Link
                    href="/audit"
                    className="flex items-center gap-2 text-[12px] text-slate-500 hover:text-brand-700"
                  >
                    <ScrollText size={13} aria-hidden />
                    Audit trail ({detail.audit_event_count} events)
                  </Link>
                </div>
              </Card>
            </div>

            <Card
              title={`Eligibility requirements (${detail.requirements.length})`}
              actions={
                <span className="text-[11px] text-slate-500">
                  {detail.total_requirements - detail.verified_count} not yet verified
                </span>
              }
              padded={false}
            >
              <DataTable<RequirementOut>
                columns={requirementColumns}
                rows={detail.requirements}
                rowKey={(row) => String(row.id)}
                emptyMessage="No requirements extracted. Upload and analyse a tender first."
              />
            </Card>

            {results ? (
              <Card
                title={`Verification results (${results.length})`}
                actions={
                  <span className="text-[11px] text-slate-500">
                    {results.filter((r) => r.status === "VERIFIED").length} verified ·{" "}
                    {results.filter((r) => r.status !== "VERIFIED").length} exception
                  </span>
                }
                padded={false}
              >
                <DataTable<VerificationResultOut>
                  columns={resultColumns}
                  rows={results}
                  rowKey={(row) => String(row.id)}
                />
              </Card>
            ) : null}

            <DecisionPanel
              verificationId={id}
              lockedReason={
                detail.has_risk
                  ? null
                  : "Assess the risk on the Compliance page first — the pipeline reads compliance, then risk, then recommendation before an officer can record a decision."
              }
              onRecorded={refresh}
            />

            <MockNotice
              what="Extracted field values and confidences come from seeded fixtures so the demo is reproducible. GST, PAN and Udyam results are structural checks against a local pattern, not registry lookups."
              production="Production would verify each value against the issuing registry and store the reference number, response hash and retrieval time as evidence."
            />
          </>
        )}
      </div>
    </PageShell>
  );
}

const requirementColumns: Column<RequirementOut>[] = [
  {
    key: "code",
    header: "Code",
    width: "190px",
    render: (row) => <span className="font-mono text-[12px] text-slate-600">{row.code}</span>,
  },
  {
    key: "title",
    header: "Requirement",
    render: (row) => (
      <div className="min-w-0">
        <p className="font-medium text-slate-900">{row.title}</p>
        {row.description ? (
          <p className="text-[11px] text-slate-500">{row.description}</p>
        ) : null}
      </div>
    ),
  },
  {
    key: "category",
    header: "Category",
    width: "150px",
    render: (row) => <span className="text-[12px] text-slate-600">{row.category}</span>,
  },
  {
    key: "threshold",
    header: "Threshold",
    align: "right",
    width: "120px",
    render: (row) =>
      row.threshold_value === null ? (
        <span className="text-slate-400">—</span>
      ) : row.threshold_value >= 100000 ? (
        <span className="numeric text-[12px]">{formatInr(row.threshold_value)}</span>
      ) : (
        <span className="numeric text-[12px]">{row.threshold_value}</span>
      ),
  },
  {
    key: "mandatory",
    header: "Mandatory",
    align: "center",
    width: "100px",
    render: (row) => (
      <StatusPill
        status={row.is_mandatory ? "PASS" : "NOT_APPLICABLE"}
        label={row.is_mandatory ? "Yes" : "No"}
      />
    ),
  },
    {
      key: "confidence",
      header: "Confidence",
      align: "right",
      width: "130px",
      render: (row) => <ConfidenceBar value={row.confidence} />,
    },
];

const resultColumns: Column<VerificationResultOut>[] = [
  {
    key: "code",
    header: "Code",
    width: "190px",
    render: (row) => (
      <div className="min-w-0">
        <span className="font-mono text-[12px] text-slate-600">{row.requirement_code}</span>
        <p className="truncate text-[11px] text-slate-500">{row.requirement_title}</p>
      </div>
    ),
  },
  {
    key: "status",
    header: "Result",
    align: "center",
    width: "120px",
    render: (row) => <StatusPill status={row.status} label={row.status} />,
  },
  {
    key: "method",
    header: "Method",
    width: "140px",
    render: (row) => <span className="text-[12px] text-slate-600">{titleCase(row.method)}</span>,
  },
  {
    key: "observed",
    header: "Observed",
    width: "150px",
    render: (row) =>
      row.observed_value ? (
        <span className="font-mono text-[12px] text-slate-700">{row.observed_value}</span>
      ) : (
        <span className="text-slate-400">—</span>
      ),
  },
  {
    key: "detail",
    header: "Detail",
    render: (row) => <span className="text-[12px] text-slate-600">{row.detail}</span>,
  },
  {
    key: "source",
    header: "Source",
    width: "200px",
    render: (row) => (
      <span
        className="text-[11px] text-slate-500"
        title={/local_rule/i.test(row.source) ? "Structural check against a local rule — not a registry lookup." : row.source}
      >
        {row.source}
      </span>
    ),
  },
];

