"use client";

import { ChevronRight } from "lucide-react";
import { PageShell } from "@/components/shell/PageShell";
import { useActiveCase } from "@/components/shell/CaseProvider";
import { Button } from "@/components/ui/Button";
import { Card, LoadingBar } from "@/components/ui/Card";
import { Callout, ErrorBanner } from "@/components/ui/Callout";
import { ConfidenceBar, StatusBadge, StatusPill } from "@/components/ui/Badge";
import { DataTable, type Column } from "@/components/ui/Table";
import { getEvidence } from "@/lib/endpoints";
import { complianceTone, formatDateTime } from "@/lib/format";
import { useApiData } from "@/lib/useApiData";
import type { EvidenceChainOut, EvidenceLevel, EvidenceResponse } from "@/lib/types";

export default function EvidencePage() {
  const { activeId } = useActiveCase();
  const { data, error, refresh } = useApiData<EvidenceResponse>(
    activeId,
    () => getEvidence(activeId!),
  );

  return (
    <PageShell
      title="Evidence Chain"
      subtitle="Every conclusion traced back to the source document"
      requiresCase
      actions={
        <Button variant="secondary" onClick={refresh}>
          Refresh
        </Button>
      }
    >
      <div className="space-y-5">
        {error ? <ErrorBanner message={error.message} onRetry={refresh} /> : null}

        {data === null ? (
          <LoadingBar label="Building evidence chain" />
        ) : data!.chains.length === 0 ? (
          <Callout tone="warning" title="No evidence yet">
            Upload and process documents, then run the verification, to build the evidence chain.
          </Callout>
        ) : (
          <>
            <Card title="Chain levels" padded>
              <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {data.levels.map((level: EvidenceLevel) => (
                  <li
                    key={level.level}
                    className="flex items-start gap-2.5 rounded-md border border-slate-200 px-3 py-2.5"
                  >
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand-50 text-[11px] font-semibold text-brand-800 numeric">
                      {level.level}
                    </span>
                    <div className="min-w-0">
                      <p className="text-[12px] font-semibold uppercase tracking-[0.03em] text-slate-500">
                        {level.entity}
                      </p>
                      <p className="truncate text-[13px] font-medium text-slate-900">
                        {level.title}
                      </p>
                      <p className="text-[11px] text-slate-500">{level.detail}</p>
                    </div>
                  </li>
                ))}
              </ol>
              {data.compliance_status ? (
                <p className="mt-4 flex items-center gap-2 border-t border-slate-100 pt-3 text-[12px] text-slate-500">
                  Overall compliance outcome:{" "}
                  <StatusPill
                    status={data.compliance_status}
                    label={data.compliance_status}
                  />
                </p>
              ) : null}
            </Card>

            <Card
              title={`Traced evidence (${data.chains.length})`}
              actions={
                <span className="text-[11px] text-slate-500">
                  {formatDateTime(data.generated_at)}
                </span>
              }
              padded={false}
            >
              <DataTable<EvidenceChainOut>
                columns={columns}
                rows={data.chains}
                rowKey={(row) => `${row.document_id}-${row.requirement_code}-${row.field_name}`}
              />
            </Card>

            <Callout tone="info" title="How to read this">
              <p>
                Each row walks the same six levels: bidder → document → extracted data →
                verification → requirement → compliance result. Following one row from the final
                status back to the file shows exactly why a requirement passed, failed or needs
                review.
              </p>
            </Callout>
          </>
        )}
      </div>
    </PageShell>
  );
}

const columns: Column<EvidenceChainOut>[] = [
  {
    key: "document",
    header: "Document",
    width: "210px",
    render: (row) => (
      <div className="min-w-0">
        <p className="truncate text-[13px] font-medium text-slate-900">{row.document_label}</p>
        <p className="truncate font-mono text-[11px] text-slate-400">
          {row.doc_type} · doc #{row.document_id}
        </p>
      </div>
    ),
  },
  {
    key: "field",
    header: "Extracted field",
    width: "190px",
    render: (row) => (
      <div className="min-w-0">
        <p className="truncate text-[12px] font-medium text-slate-700">{row.field_name}</p>
        <p className="truncate font-mono text-[11px] text-slate-500">{row.field_value}</p>
      </div>
    ),
  },
  {
    key: "confidence",
    header: "Confidence",
    align: "right",
    width: "120px",
    render: (row) => <ConfidenceBar value={row.confidence} />,
  },
  {
    key: "verification",
    header: "Verification",
    width: "160px",
    render: (row) => (
      <div className="min-w-0">
        <StatusPill status={row.verification_status} label={row.verification_status} />
        <p className="mt-0.5 truncate text-[11px] text-slate-500">{row.verification_detail}</p>
      </div>
    ),
  },
  {
    key: "requirement",
    header: "Requirement",
    width: "190px",
    render: (row) => (
      <div className="min-w-0">
        <p className="truncate text-[12px] text-slate-700">{row.requirement_title}</p>
        <p className="truncate font-mono text-[11px] text-slate-400">{row.requirement_code}</p>
      </div>
    ),
  },
  {
    key: "compliance",
    header: "Outcome",
    width: "150px",
    render: (row) => (
      <div className="min-w-0">
        <StatusBadge tone={complianceTone(row.compliance_status)}>
          {row.compliance_status}
        </StatusBadge>
        <p className="mt-0.5 flex items-center gap-1 truncate text-[11px] text-slate-500">
          <ChevronRight size={10} aria-hidden />
          {row.compliance_reason}
        </p>
      </div>
    ),
  },
];
