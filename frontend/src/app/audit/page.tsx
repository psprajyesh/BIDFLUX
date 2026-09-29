"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { PageShell } from "@/components/shell/PageShell";
import { useActiveCase } from "@/components/shell/CaseProvider";
import { Button } from "@/components/ui/Button";
import { Card, LoadingBar } from "@/components/ui/Card";
import { ErrorBanner } from "@/components/ui/Callout";
import { StatusBadge } from "@/components/ui/Badge";
import { getAuditTrail } from "@/lib/endpoints";
import { formatDateTime, titleCase } from "@/lib/format";
import { useApiData } from "@/lib/useApiData";
import type { AuditEventOut } from "@/lib/types";

const STAGES = [
  "All",
  "Tender",
  "Requirements",
  "Documents",
  "Extraction",
  "Verification",
  "Compliance",
  "Risk",
  "Recommendation",
  "Decision",
  "System",
];

function stageOf(eventType: string): string {
  if (eventType.includes("TENDER")) return "Tender";
  if (eventType.includes("REQUIREMENT")) return "Requirements";
  if (eventType.includes("DOCUMENT_MISSING")) return "Documents";
  if (eventType.includes("DOCUMENT")) return "Documents";
  if (eventType.includes("FIELD") || eventType.includes("PROCESSED")) return "Extraction";
  if (eventType.includes("VERIFICATION")) return "Verification";
  if (eventType.includes("COMPLIANCE")) return "Compliance";
  if (eventType.includes("RISK")) return "Risk";
  if (eventType.includes("RECOMMENDATION")) return "Recommendation";
  if (eventType.includes("DECISION")) return "Decision";
  return "System";
}

export default function AuditPage() {
  const { activeId } = useActiveCase();
  const { data: events, error, refresh } = useApiData<AuditEventOut[]>(
    activeId,
    () => getAuditTrail(activeId!),
  );
  const [stage, setStage] = useState("All");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    if (!events) return [];
    const needle = query.trim().toLowerCase();
    return events.filter((event) => {
      if (stage !== "All" && stageOf(event.event_type) !== stage) return false;
      if (!needle) return true;
      return (
        event.event_type.toLowerCase().includes(needle) ||
        event.message.toLowerCase().includes(needle) ||
        event.actor.toLowerCase().includes(needle)
      );
    });
  }, [events, stage, query]);

  return (
    <PageShell
      title="Audit Trail"
      subtitle="Append-only record of everything that happened"
      requiresCase
      actions={
        <Button variant="secondary" onClick={refresh}>
          Refresh
        </Button>
      }
    >
      <div className="space-y-5">
        {error ? <ErrorBanner message={error.message} onRetry={refresh} /> : null}

        <Card title="Filters">
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-56 flex-1">
              <label className="label" htmlFor="audit-search">
                Search
              </label>
              <div className="relative">
                <Search
                  size={14}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                  aria-hidden
                />
                <input
                  id="audit-search"
                  className="field pl-8"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Event, message or actor"
                />
              </div>
            </div>
            <div>
              <label className="label" htmlFor="audit-stage">
                Stage
              </label>
              <select
                id="audit-stage"
                className="field w-48"
                value={stage}
                onChange={(e) => setStage(e.target.value)}
              >
                {STAGES.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </Card>

        {events === null ? (
          <LoadingBar label="Loading audit trail" />
        ) : (
          <Card
            title={`Events (${filtered.length} of ${events.length})`}
            padded={false}
            footer="Events are written by the services as they happen and are never edited or deleted by the API."
          >
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] border-collapse">
                <thead>
                  <tr>
                    <th scope="col" className="th w-40">
                      Time
                    </th>
                    <th scope="col" className="th w-52">
                      Event
                    </th>
                    <th scope="col" className="th w-28">
                      Stage
                    </th>
                    <th scope="col" className="th">
                      Message
                    </th>
                    <th scope="col" className="th w-32">
                      Actor
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-500">
                        No audit events match the current filters.
                      </td>
                    </tr>
                  ) : (
                    [...filtered].reverse().map((event) => (
                      <tr key={event.id} className="tr align-top">
                        <td className="td whitespace-nowrap text-[12px] text-slate-500">
                          {formatDateTime(event.created_at)}
                        </td>
                        <td className="td">
                          <StatusBadge tone={event.event_type === "DEMO_DATA_LOADED" ? "mock" : "neutral"}>
                            {event.event_type}
                          </StatusBadge>
                        </td>
                        <td className="td text-[12px] text-slate-600">
                          {event.stage || stageOf(event.event_type)}
                        </td>
                        <td className="td text-[12px] text-slate-700">{event.message}</td>
                        <td className="td text-[12px] text-slate-600">{titleCase(event.actor)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </PageShell>
  );
}
