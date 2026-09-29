import type { ReactNode } from "react";
import { AlertTriangle, FlaskConical, Info, CheckCircle2, XCircle } from "lucide-react";

type CalloutTone = "info" | "mock" | "warning" | "danger" | "success";

const ICONS: Record<CalloutTone, typeof Info> = {
  info: Info,
  mock: FlaskConical,
  warning: AlertTriangle,
  danger: XCircle,
  success: CheckCircle2,
};

export function Callout({
  tone = "info",
  title,
  children,
}: {
  tone?: CalloutTone;
  title?: string;
  children: ReactNode;
}) {
  const Icon = ICONS[tone];
  return (
    <div
      className={`callout callout-${tone}`}
      role={tone === "danger" ? "alert" : tone === "success" ? "status" : undefined}
      aria-live={tone === "success" ? "polite" : undefined}
    >
      <Icon aria-hidden size={16} strokeWidth={2} className="mt-0.5 shrink-0" />
      <div className="min-w-0">
        {title ? <p className="font-semibold">{title}</p> : null}
        <div className={title ? "mt-1" : ""}>{children}</div>
      </div>
    </div>
  );
}

/**
 * States plainly what is simulated and what a production system would do instead.
 */
export function MockNotice({ what, production }: { what: string; production?: string }) {
  return (
    <Callout tone="mock" title="Simulated processing">
      <p>{what}</p>
      {production ? <p className="mt-1 opacity-80">{production}</p> : null}
    </Callout>
  );
}

export function ErrorBanner({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="callout callout-danger" role="alert">
      <XCircle aria-hidden size={16} strokeWidth={2} className="mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="font-semibold">Something went wrong</p>
        <p className="mt-1 break-words">{message}</p>
      </div>
      {onRetry ? (
        <button type="button" onClick={onRetry} className="btn btn-secondary btn-sm shrink-0">
          Retry
        </button>
      ) : null}
    </div>
  );
}
