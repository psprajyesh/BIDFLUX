import type { ReactNode } from "react";

export function Card({
  title,
  actions,
  children,
  footer,
  padded = true,
  className = "",
}: {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  padded?: boolean;
  className?: string;
}) {
  return (
    <section className={`bg-white border border-slate-200 rounded-lg ${className}`}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 px-5 py-3.5 border-b border-slate-200">
          <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
          {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
        </header>
      )}
      <div className={padded ? "p-5" : ""}>{children}</div>
      {footer ? (
        <footer className="px-5 py-3 border-t border-slate-200 bg-slate-50 rounded-b-lg text-xs text-slate-500">
          {footer}
        </footer>
      ) : null}
    </section>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-[22px] font-semibold leading-7 tracking-tight text-slate-900">
          {title}
        </h1>
        {subtitle ? <p className="mt-1 text-[13px] text-slate-500">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="border border-dashed border-slate-300 rounded-lg bg-slate-50 px-6 py-12 text-center">
      <p className="text-sm font-semibold text-slate-900">{title}</p>
      {description ? (
        <p className="mx-auto mt-1 max-w-md text-[13px] text-slate-500">{description}</p>
      ) : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}

export function LoadingBar({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-8" role="status" aria-live="polite">
      <span className="h-1 w-32 rounded-full bg-slate-200 animate-pulse" />
      <span className="text-[13px] text-slate-500">{label}…</span>
    </div>
  );
}
