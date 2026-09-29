"use client";

import { Check } from "lucide-react";
import type { StepState, WorkflowStateResponse } from "@/lib/types";

/**
 * Nine-stage progress rail. Stage names and ordering come from the backend
 * (`GET /verifications/{id}/workflow`) so the UI never invents its own order.
 */
export function WorkflowStepper({ workflow }: { workflow: WorkflowStateResponse }) {
  return (
    <nav aria-label="Verification workflow" className="overflow-x-auto">
      <ol className="flex min-w-max items-center gap-1">
        {workflow.steps.map((step: StepState, index: number) => (
          <li key={step.key} className="flex items-center gap-1">
            <StepBadge step={step} />
            {index < workflow.steps.length - 1 ? <Connector active={step.complete} /> : null}
          </li>
        ))}
      </ol>
    </nav>
  );
}

function StepBadge({ step }: { step: StepState }) {
  const tone =
    step.state === "complete"
      ? "bg-brand-700 text-white border-brand-700"
      : step.state === "active"
        ? "bg-white text-brand-800 border-brand-600 ring-2 ring-brand-600/25"
        : "bg-white text-slate-400 border-slate-300";

  return (
    <span
      className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${tone}`}
      aria-current={step.active ? "step" : undefined}
      title={`${step.label} — ${step.state}`}
    >
      {step.complete ? (
        <Check size={11} strokeWidth={3} aria-hidden />
      ) : (
        <span className="numeric w-3 text-center">{step.index}</span>
      )}
      <span className="whitespace-nowrap">{step.label}</span>
    </span>
  );
}

function Connector({ active }: { active: boolean }) {
  return (
    <span
      aria-hidden
      className={`h-px w-5 ${active ? "bg-brand-600" : "bg-slate-300"}`}
    />
  );
}
