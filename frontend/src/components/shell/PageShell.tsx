"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { AlertCircle } from "lucide-react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { useActiveCase } from "./CaseProvider";
import { listVerifications } from "@/lib/endpoints";
import type { VerificationSummary } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, EmptyState, LoadingBar, PageHeader } from "@/components/ui/Card";
import { ErrorBanner } from "@/components/ui/Callout";

/**
 * Chrome shared by every page.
 *
 * `requiresCase` renders a case picker when no verification is selected, so a
 * stage page opened directly still does something useful instead of an error.
 */
export function PageShell({
  title,
  subtitle,
  actions,
  children,
  requiresCase = false,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  requiresCase?: boolean;
}) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="flex-1 space-y-5 px-6 py-6">
          <PageHeader title={title} subtitle={subtitle} actions={actions} />
          {requiresCase ? <CaseGate>{children}</CaseGate> : children}
        </main>
        <footer className="border-t border-slate-200 px-6 py-3 text-[11px] text-slate-400">
          BIDFLUX · Smart India Hackathon 2026 · AI extraction and registry checks are simulated;
          compliance, risk, decision, audit and evidence logic are real.
        </footer>
      </div>
    </div>
  );
}

function CaseGate({ children }: { children: ReactNode }) {
  const { activeId, setActiveId } = useActiveCase();
  const [cases, setCases] = useState<VerificationSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    listVerifications()
      .then(setCases)
      .catch((err: Error) => setError(err.message));
  }, [reloadKey]);

  if (activeId) {
    return (
      <div className="space-y-5">
        {error ? <ErrorBanner message={error} onRetry={() => setReloadKey((n) => n + 1)} /> : null}
        {children}
      </div>
    );
  }

  return (
    <Card title="Select a verification">
      <p className="mb-4 text-[13px] text-slate-500">
        This stage works on one verification at a time. Choose a case to continue, or load the
        SIH demo scenario from the Dashboard.
      </p>

      {error ? (
        <ErrorBanner message={error} onRetry={() => setReloadKey((n) => n + 1)} />
      ) : cases === null ? (
        <LoadingBar label="Loading verifications" />
      ) : cases.length === 0 ? (
        <EmptyState
          title="No verifications yet"
          description="Load the demo scenario or start a new verification to begin."
          action={
            <Link href="/verification/new">
              <Button variant="primary">Start a verification</Button>
            </Link>
          }
        />
      ) : (
        <ul className="divide-y divide-slate-100">
          {cases.map((item) => (
            <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="truncate text-[13px] font-medium text-slate-900">{item.title}</p>
                <p className="truncate font-mono text-[11px] text-slate-500">
                  {item.id} · {item.tender_reference || "no reference"}
                </p>
              </div>
              <Button variant="secondary" size="sm" onClick={() => setActiveId(item.id)}>
                Use this case
              </Button>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-4 flex items-start gap-2 text-[11px] text-slate-400">
        <AlertCircle size={13} className="mt-0.5 shrink-0" aria-hidden />
        <span>Tip: open a verification and the ID is remembered across every stage automatically.</span>
      </p>
    </Card>
  );
}
