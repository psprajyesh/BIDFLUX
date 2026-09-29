"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Gavel, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, LoadingBar } from "@/components/ui/Card";
import { Callout, ErrorBanner } from "@/components/ui/Callout";
import { StatusPill } from "@/components/ui/Badge";
import { KeyValue } from "@/components/ui/Table";
import { getDecision, submitDecision } from "@/lib/endpoints";
import { formatDateTime } from "@/lib/format";
import type { OfficerDecisionOut } from "@/lib/types";

const OPTIONS = [
  { value: "APPROVED", label: "Approve", variant: "success" as const },
  { value: "CLARIFICATION_REQUESTED", label: "Request clarification", variant: "warning" as const },
  { value: "REJECTED", label: "Reject", variant: "danger" as const },
];

const MIN = { comment: 10, name: 3, id: 3 };

/**
 * The officer decision. All four fields are mandatory and the officer is the
 * only decision authority — there is no login in this demo build, so identity
 * is captured explicitly here.
 */
export function DecisionPanel({
  verificationId,
  lockedReason,
  onRecorded,
}: {
  verificationId: string;
  lockedReason?: string | null;
  onRecorded?: () => void;
}) {
  const [existing, setExisting] = useState<OfficerDecisionOut | null | undefined>(undefined);
  const [pending, setPending] = useState(true);
  const [decision, setDecision] = useState<string>("");
  const [comment, setComment] = useState("");
  const [officerName, setOfficerName] = useState("");
  const [officerId, setOfficerId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  // Load any decision already recorded. `pending` stays true until a load
  // (and the reload after a record) resolves, so an empty form never flashes
  // while a decision is read back from the API.
  useEffect(() => {
    let cancelled = false;
    getDecision(verificationId)
      .then((value) => {
        if (cancelled) return;
        setExisting(value);
        setPending(false);
      })
      .catch(() => {
        if (!cancelled) {
          setExisting(null);
          setPending(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [verificationId, done]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (!decision) return setError("Choose a decision.");
    if (comment.trim().length < MIN.comment)
      return setError(`Comment must be at least ${MIN.comment} characters.`);
    if (officerName.trim().length < MIN.name)
      return setError("Officer name must be at least 3 characters.");
    if (officerId.trim().length < MIN.id)
      return setError("Officer ID must be at least 3 characters.");

    setBusy(true);
    try {
      await submitDecision(verificationId, {
        decision: decision as "APPROVED" | "REJECTED" | "CLARIFICATION_REQUESTED",
        comment: comment.trim(),
        officer_name: officerName.trim(),
        officer_id: officerId.trim(),
      });
      setDone(true);
      setPending(true);
      setDecision("");
      setComment("");
      onRecorded?.();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (pending) {
    return (
      <Card title="Officer decision">
        <LoadingBar label="Loading decision" />
      </Card>
    );
  }

  if (existing) {
    return (
      <Card title="Officer decision">
        <div className="flex flex-wrap items-center gap-3">
          <CheckCircle2 size={18} className="text-emerald-600" aria-hidden />
          <StatusPill status={existing.decision} label={existing.decision} />
        </div>
        <p className="mt-3 whitespace-pre-wrap text-[13px] text-slate-700">{existing.comment}</p>
        <div className="mt-4 border-t border-slate-100 pt-4">
          <KeyValue
            items={[
              { label: "Officer", value: existing.officer_name },
              { label: "Officer ID", value: <span className="font-mono">{existing.officer_id}</span> },
              { label: "Recorded", value: formatDateTime(existing.created_at) },
              { label: "Verification", value: <span className="font-mono">{existing.verification_id}</span> },
            ]}
          />
        </div>
      </Card>
    );
  }

  if (lockedReason) {
    return (
      <Card title="Officer decision">
        <Callout tone="warning" title="Not ready for a decision">
          {lockedReason}
        </Callout>
      </Card>
    );
  }

  return (
    <Card title="Officer decision">
      <form onSubmit={onSubmit} className="space-y-4">
        {error ? <ErrorBanner message={error} /> : null}
        {done ? (
          <Callout tone="success">
            Decision recorded and written to the audit trail.
          </Callout>
        ) : null}

        <fieldset>
          <legend className="label">Decision *</legend>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Decision">
            {OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                role="radio"
                aria-checked={decision === option.value}
                onClick={() => setDecision(option.value)}
                className={`btn btn-${decision === option.value ? option.variant : "secondary"} btn-sm`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </fieldset>

        <div>
          <label className="label" htmlFor="officer-comment">
            Officer comment * (min 10 characters)
          </label>
          <textarea
            id="officer-comment"
            className="field"
            rows={3}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Basis for the decision, referencing the failed or missing requirements."
            maxLength={2000}
            required
          />
          <p className="mt-1 text-[11px] text-slate-400 numeric">{comment.trim().length} / 2000</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="officer-name">
              Officer name *
            </label>
            <input
              id="officer-name"
              className="field"
              value={officerName}
              onChange={(e) => setOfficerName(e.target.value)}
              placeholder="e.g. R. Iyer"
              minLength={MIN.name}
              maxLength={128}
              required
            />
          </div>
          <div>
            <label className="label" htmlFor="officer-id">
              Officer ID *
            </label>
            <input
              id="officer-id"
              className="field font-mono"
              value={officerId}
              onChange={(e) => setOfficerId(e.target.value)}
              placeholder="e.g. OFF-2026-014"
              minLength={MIN.id}
              maxLength={64}
              required
            />
          </div>
        </div>

        <Button type="submit" variant="primary" loading={busy} disabled={!decision} title={decision ? undefined : "Choose a decision first"}>
          <Gavel size={15} aria-hidden />
          Record decision
        </Button>
      </form>
    </Card>
  );
}
