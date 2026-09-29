"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FilePlus2, RotateCcw, ArrowRight, Sparkles } from "lucide-react";
import { PageShell } from "@/components/shell/PageShell";
import { useActiveCase } from "@/components/shell/CaseProvider";
import { Button } from "@/components/ui/Button";
import { Card, EmptyState, LoadingBar } from "@/components/ui/Card";
import { Callout, ErrorBanner, MockNotice } from "@/components/ui/Callout";
import { RiskBadge, StatusPill } from "@/components/ui/Badge";
import { DataTable, type Column } from "@/components/ui/Table";
import { getDashboard, loadDemo, resetDemo } from "@/lib/endpoints";
import { STATUS_LABELS, formatDateTime } from "@/lib/format";
import { useApiData } from "@/lib/useApiData";
import type { DashboardResponse, VerificationSummary } from "@/lib/types";

export default function DashboardPage() {
  const router = useRouter();
  const { setActiveId } = useActiveCase();
  const { data, error, refresh } = useApiData<DashboardResponse>("dashboard", getDashboard);
  const [loadingDemo, setLoadingDemo] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const openCase = useCallback(
    (id: string) => {
      setActiveId(id);
      router.push(`/verification/${id}`);
    },
    [router, setActiveId],
  );

  async function onLoadDemo() {
    setLoadingDemo(true);
    setActionError(null);
    try {
      const result = await loadDemo();
      setActiveId(result.verification_id);
      setNotice(
        `${result.message} — ${result.requirements} requirements, ${result.documents} documents.`,
      );
      refresh();
    } catch (err) {
      setNotice(null);
      setActionError((err as Error).message);
    } finally {
      setLoadingDemo(false);
    }
  }

  async function onReset() {
    if (
      !window.confirm(
        "Reset all demo data? Any documents uploaded for this demo will be deleted.",
      )
    ) {
      return;
    }
    setLoadingDemo(true);
    setActionError(null);
    try {
      const result = await resetDemo();
      setActiveId(null);
      setNotice(result.message);
      refresh();
    } catch (err) {
      setNotice(null);
      setActionError((err as Error).message);
    } finally {
      setLoadingDemo(false);
    }
  }

  return (
    <PageShell
      title="Dashboard"
      subtitle="Procurement verification overview and demo controls"
      actions={
        <>
          <Button onClick={onLoadDemo} loading={loadingDemo} variant="primary">
            <Sparkles size={15} aria-hidden />
            Load SIH Demo Scenario
          </Button>
          <Link href="/verification/new">
            <Button variant="secondary">
              <FilePlus2 size={15} aria-hidden />
              New Verification
            </Button>
          </Link>
        </>
      }
    >
      <div className="space-y-5">
        {error ? <ErrorBanner message={error.message} onRetry={refresh} /> : null}
        {actionError ? <ErrorBanner message={actionError} /> : null}
        {notice ? <Callout tone="success">{notice}</Callout> : null}

        <MockNotice
          what="Tender text extraction, OCR confidences and GST / PAN / Udyam registry lookups run against seeded local rules. Values are deterministic, so the demo always lands on the same 7-of-8 result."
          production="Production would call the tender parsing service, an OCR provider and the GST/PAN/Udyam public registries over HTTPS, with the response cached against the document checksum."
        />

        {data === null && !error ? (
          <LoadingBar label="Loading dashboard" />
        ) : data === null ? null : (
          <>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
              <Metric label="Verifications" value={data.total_verifications} />
              <Metric label="Pending review" value={data.pending_review} tone="warning" />
              <Metric label="High risk" value={data.high_risk_cases} tone="danger" />
              <Metric label="Decisions" value={data.completed_decisions} tone="success" />
              <Metric
                label="Compliance rate"
                value={`${Math.round(data.compliance_rate)}%`}
                tone="success"
              />
            </div>

            <Card
              title="Recent verifications"
              actions={
                data.recent.length > 0 ? (
                  <Link href="/verification" className="text-[12px] text-brand-700 hover:underline">
                    View all
                  </Link>
                ) : null
              }
              padded={false}
            >
              {data.recent.length === 0 ? (
                <div className="p-5">
                  <EmptyState
                    title="No verifications yet"
                    description="Load the SIH demo scenario to see the full pipeline, or create a new verification for your own tender."
                    action={
                      <Button variant="primary" onClick={onLoadDemo} loading={loadingDemo}>
                        Load SIH Demo Scenario
                      </Button>
                    }
                  />
                </div>
              ) : (
                <DataTable<VerificationSummary>
                  columns={recentColumns(openCase)}
                  rows={data.recent}
                  rowKey={(row) => row.id}
                  rowClassName={() => "cursor-pointer"}
                  onRowClick={(row) => openCase(row.id)}
                  tableLabel="Recent verifications"
                />
              )}
            </Card>

            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={onReset} loading={loadingDemo} variant="ghost">
                <RotateCcw size={15} aria-hidden />
                Reset demo data
              </Button>
              <p className="text-[11px] text-slate-400">
                Resets all demo cases so the scenario can be replayed from a clean state.
              </p>
            </div>
          </>
        )}
      </div>
    </PageShell>
  );
}

function recentColumns(onOpen: (id: string) => void): Column<VerificationSummary>[] {
  return [
    {
      key: "id",
      header: "ID",
      width: "180px",
      render: (row) => (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onOpen(row.id);
          }}
          className="inline-flex items-center gap-1 font-mono text-[12px] text-brand-700 hover:underline"
        >
          {row.id}
          <ArrowRight size={12} aria-hidden />
        </button>
      ),
    },
    {
      key: "title",
      header: "Verification",
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-slate-900">{row.title}</p>
          <p className="truncate text-[11px] text-slate-500">
            {row.tender_reference || "no reference"} · {row.bidder_name ?? "no bidder"}
          </p>
        </div>
      ),
    },
    {
      key: "compliance",
      header: "Compliance",
      align: "center",
      width: "120px",
      render: (row) =>
        row.compliance_total ? (
          <span className="numeric text-[12px]">
            {row.compliance_pass}/{row.compliance_total}
          </span>
        ) : (
          <span className="text-slate-400">—</span>
        ),
    },
    {
      key: "risk",
      header: "Risk",
      align: "center",
      width: "100px",
      render: (row) => <RiskBadge level={row.risk_level} />,
    },
    {
      key: "status",
      header: "Status",
      width: "170px",
      render: (row) => (
        <StatusPill status={row.status} label={STATUS_LABELS[row.status] ?? row.status} />
      ),
    },
    {
      key: "updated",
      header: "Updated",
      width: "150px",
      render: (row) => (
        <span className="text-[12px] text-slate-500">{formatDateTime(row.updated_at)}</span>
      ),
    },
  ];
}

function Metric({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number | string;
  tone?: "neutral" | "success" | "warning" | "danger";
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
