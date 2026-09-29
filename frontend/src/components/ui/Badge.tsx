import { CheckCircle2, AlertTriangle, XCircle, Clock, Minus, FlaskConical, Info } from "lucide-react";
import type { ReactNode } from "react";

export type Tone = "success" | "warning" | "danger" | "info" | "neutral" | "mock";

const ICONS: Record<Tone, typeof CheckCircle2> = {
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
  info: Info,
  neutral: Minus,
  mock: FlaskConical,
};

/**
 * The single status primitive. Status is always colour + icon + text, never
 * colour alone.
 */
export function StatusBadge({
  tone,
  children,
  icon = true,
  className = "",
}: {
  tone: Tone;
  children: ReactNode;
  icon?: boolean;
  className?: string;
}) {
  const Icon = ICONS[tone];
  return (
    <span className={`badge tone-${tone} ${className}`}>
      {icon ? <Icon aria-hidden size={12} strokeWidth={2.5} /> : null}
      {children}
    </span>
  );
}

/** Explicitly labels a simulated value so it is never mistaken for a live result. */
export function MockBadge({ label = "MOCK" }: { label?: string }) {
  return <StatusBadge tone="mock">{label}</StatusBadge>;
}

export function StatusPill({ status, label }: { status: string; label: string }) {
  const tone: Tone =
    status === "PASS" || status === "VERIFIED" || status === "APPROVED"
      ? "success"
      : status === "FAIL" || status === "INVALID" || status === "MISMATCH" || status === "REJECTED"
        ? "danger"
        : status === "REVIEW" || status === "MISSING" || status === "CLARIFICATION_REQUESTED"
          ? "warning"
          : status === "PENDING" || status === "PROCESSED"
            ? "info"
            : "neutral";
  return <StatusBadge tone={tone}>{label}</StatusBadge>;
}

export function RiskBadge({ level }: { level: string | null }) {
  if (!level) return <StatusBadge tone="neutral">NOT ASSESSED</StatusBadge>;
  const tone: Tone =
    level === "LOW" ? "success" : level === "MEDIUM" ? "warning" : "danger";
  return (
    <StatusBadge tone={tone} className="tracking-[0.03em]">
      {level}
    </StatusBadge>
  );
}

export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const colour = pct >= 95 ? "bg-emerald-600" : pct >= 90 ? "bg-amber-500" : "bg-red-600";
  return (
    <span className="inline-flex items-center gap-2">
      <span className="h-1.5 w-20 rounded-full bg-slate-200 overflow-hidden" aria-hidden>
        <span className={`block h-full ${colour}`} style={{ width: `${pct}%` }} />
      </span>
      <span className="text-[11px] font-medium text-slate-600 numeric">{pct}%</span>
    </span>
  );
}

export function ProcessingBadge({ mode }: { mode: string }) {
  const isMock = mode === "MOCK";
  return (
    <StatusBadge tone={isMock ? "mock" : "neutral"}>
      {isMock ? <FlaskConical aria-hidden size={12} strokeWidth={2.5} /> : <Clock aria-hidden size={12} strokeWidth={2.5} />}
      {mode}
    </StatusBadge>
  );
}
