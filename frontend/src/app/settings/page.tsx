"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, XCircle, FlaskConical, ShieldCheck } from "lucide-react";
import { PageShell } from "@/components/shell/PageShell";
import { Card, LoadingBar } from "@/components/ui/Card";
import { Callout, ErrorBanner } from "@/components/ui/Callout";
import { StatusBadge } from "@/components/ui/Badge";
import { apiBaseUrl, hasApiConfigured } from "@/lib/api";
import { getHealth } from "@/lib/endpoints";
import type { Health } from "@/lib/types";

export default function SettingsPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(() =>
    hasApiConfigured() ? null : "NEXT_PUBLIC_API_URL is not set for this build.",
  );

  useEffect(() => {
    if (!hasApiConfigured()) return;
    let cancelled = false;
    getHealth()
      .then((value) => {
        if (!cancelled) setHealth(value);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <PageShell
      title="Settings"
      subtitle="Runtime configuration and what this build does and does not do"
    >
      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Connection">
          {error ? <ErrorBanner message={error} /> : null}
          <dl className="space-y-3 text-[13px]">
            <Row label="API base URL">
              {hasApiConfigured() ? (
                <span className="font-mono text-[12px]">{apiBaseUrl()}</span>
              ) : (
                <span className="text-[12px] text-slate-400">not set</span>
              )}
            </Row>
            <Row label="Source">
              <span className="font-mono text-[12px]">NEXT_PUBLIC_API_URL</span>
            </Row>
            <Row label="Status">
              {health ? (
                <StatusBadge tone="success">{health.status}</StatusBadge>
              ) : (
                <StatusBadge tone="neutral">CHECKING</StatusBadge>
              )}
            </Row>
            <Row label="Version">
              <span className="font-mono text-[12px]">
                {health ? `${health.app_name} ${health.api_version}` : "—"}
              </span>
            </Row>
            <Row label="Environment">{health?.app_env ?? "—"}</Row>
            <Row label="AI mode">
              {health ? <StatusBadge tone="mock">{health.ai_mode}</StatusBadge> : "—"}
            </Row>
          </dl>
          <p className="mt-4 border-t border-slate-100 pt-3 text-[11px] text-slate-500">
            There is no production fallback: a build without NEXT_PUBLIC_API_URL fails loudly
            rather than quietly pointing at a local machine.
          </p>
        </Card>

        <Card title="Capabilities">
          {health === null ? (
            <LoadingBar label="Reading capabilities" />
          ) : (
            <ul className="space-y-2.5">
              {Object.entries(health.capabilities ?? {}).map(([name, value]) => {
                const simulated = /mock|simulat/i.test(value);
                return (
                  <li key={name} className="flex items-start gap-2.5">
                    {simulated ? (
                      <FlaskConical size={15} className="mt-0.5 shrink-0 text-purple-600" aria-hidden />
                    ) : (
                      <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-emerald-600" aria-hidden />
                    )}
                    <div className="min-w-0">
                      <p className="text-[13px] font-medium text-slate-900">
                        {name.replace(/_/g, " ")}
                      </p>
                      <p className="text-[12px] text-slate-500">{value}</p>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <Card title="Real vs simulated" className="lg:col-span-2">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="flex items-center gap-2 text-[13px] font-semibold text-emerald-700">
                <ShieldCheck size={15} aria-hidden />
                Real
              </p>
              <ul className="mt-2 space-y-1.5 text-[12px] text-slate-600">
                {[
                  "SQLite persistence across all stages",
                  "File storage, validation and size limits",
                  "Requirement-to-document verification",
                  "Compliance, risk and recommendation rules",
                  "Officer decision recording",
                  "Audit trail and evidence chain",
                ].map((item) => (
                  <li key={item} className="flex gap-2">
                    <CheckCircle2 size={13} className="mt-0.5 shrink-0 text-emerald-600" aria-hidden />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="flex items-center gap-2 text-[13px] font-semibold text-purple-700">
                <FlaskConical size={15} aria-hidden />
                Simulated
              </p>
              <ul className="mt-2 space-y-1.5 text-[12px] text-slate-600">
                {[
                  "Tender text extraction (seeded rules)",
                  "OCR field extraction and confidences",
                  "GST, PAN and Udyam format checks",
                  "Recommendation wording",
                ].map((item) => (
                  <li key={item} className="flex gap-2">
                    <XCircle size={13} className="mt-0.5 shrink-0 text-purple-600" aria-hidden />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mt-4">
            <Callout tone="warning" title="No government API is called">
              GSTIN, PAN and Udyam results are structural checks against a local pattern. They do
              not confirm that a registration exists. A production system would call the issuing
              registry and record the response as evidence.
            </Callout>
          </div>
        </Card>

        <Card title="Authentication" className="lg:col-span-2">
          <Callout tone="warning" title="No login in this build">
            The dashboard opens directly and every endpoint is unauthenticated, which is
            intentional for the SIH demo. Officer identity is captured explicitly on the decision
            form. Before any real deployment, add authentication, per-officer authorisation and
            server-side role checks.
          </Callout>
        </Card>
      </div>
    </PageShell>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-slate-500">{label}</dt>
      <dd className="min-w-0 text-right text-slate-900">{children}</dd>
    </div>
  );
}
