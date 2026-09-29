"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { FilePlus2 } from "lucide-react";
import { PageShell } from "@/components/shell/PageShell";
import { useActiveCase } from "@/components/shell/CaseProvider";
import { Button } from "@/components/ui/Button";
import { Card, LoadingBar } from "@/components/ui/Card";
import { ErrorBanner } from "@/components/ui/Callout";
import { RiskBadge, StatusPill } from "@/components/ui/Badge";
import { DataTable, type Column } from "@/components/ui/Table";
import { listVerifications } from "@/lib/endpoints";
import { decisionLabel, STATUS_LABELS, formatDateTime } from "@/lib/format";
import { useApiData } from "@/lib/useApiData";
import type { VerificationSummary } from "@/lib/types";

export default function VerificationsPage() {
  const router = useRouter();
  const { setActiveId } = useActiveCase();
  const { data: rows, error, refresh } = useApiData<VerificationSummary[]>(
    "verification-list",
    () => listVerifications(),
  );

  const open = useCallback(
    (id: string) => {
      setActiveId(id);
      router.push(`/verification/${id}`);
    },
    [router, setActiveId],
  );

  return (
    <PageShell
      title="Verifications"
      subtitle="Every tender verification in this workspace"
      actions={
        <Link href="/verification/new">
          <Button variant="primary">
            <FilePlus2 size={15} aria-hidden />
            New Verification
          </Button>
        </Link>
      }
    >
      <Card padded={false}>
        {error ? (
          <div className="p-5">
            <ErrorBanner message={error.message} onRetry={refresh} />
          </div>
        ) : rows === null ? (
          <div className="px-5">
            <LoadingBar label="Loading verifications" />
          </div>
        ) : (
          <DataTable<VerificationSummary>
            columns={columns()}
            rows={rows}
            rowKey={(row) => row.id}
            rowClassName={() => "cursor-pointer"}
            onRowClick={(row) => open(row.id)}
            tableLabel="Verifications"
            emptyMessage="No verifications yet. Load the demo scenario from the Dashboard to see the full pipeline."
          />
        )}
      </Card>
    </PageShell>
  );
}

function columns(): Column<VerificationSummary>[] {
  return [
    {
      key: "id",
      header: "ID",
      width: "170px",
      render: (row) => <span className="font-mono text-[12px]">{row.id}</span>,
    },
    {
      key: "title",
      header: "Verification",
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-slate-900">{row.title}</p>
          <p className="truncate text-[11px] text-slate-500">
            {row.tender_reference || "no reference"} · {row.bidder_name ?? "no bidder"} ·{" "}
            {row.current_step}
          </p>
        </div>
      ),
    },
    {
      key: "progress",
      header: "Compliance",
      align: "center",
      width: "120px",
      render: (row) =>
        row.compliance_total ? (
          <span className="numeric text-[12px]">
            {row.compliance_pass ?? 0}/{row.compliance_total}
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
      width: "180px",
      render: (row) => (
        <StatusPill status={row.status} label={STATUS_LABELS[row.status] ?? row.status} />
      ),
    },
    {
      key: "decision",
      header: "Decision",
      width: "150px",
      render: (row) =>
        row.decision ? (
          <StatusPill status={row.decision} label={decisionLabel(row.decision)} />
        ) : (
          "—"
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
