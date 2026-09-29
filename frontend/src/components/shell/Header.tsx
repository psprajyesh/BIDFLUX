"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Menu } from "lucide-react";
import { getHealth } from "@/lib/endpoints";
import { hasApiConfigured } from "@/lib/api";
import { isActiveNav, NAV } from "@/lib/nav";
import { StatusBadge } from "@/components/ui/Badge";
import { useActiveCase } from "./CaseProvider";

/**
 * Header. Beyond the health indicator it surfaces the active verification ID,
 * because every stage operates on the same one. On small screens the sidebar is
 * hidden, so the same NAV data is surfaced through a menu here.
 */
export function Header() {
  const { activeId, clearActiveId } = useActiveCase();
  const pathname = usePathname();
  const [health, setHealth] = useState<"checking" | "up" | "down">(() =>
    hasApiConfigured() ? "checking" : "down",
  );

  useEffect(() => {
    if (!hasApiConfigured()) return;
    let cancelled = false;
    getHealth()
      .then(() => {
        if (!cancelled) setHealth("up");
      })
      .catch(() => {
        if (!cancelled) setHealth("down");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-6 py-3">
      <div className="flex items-center gap-2 text-[13px] text-slate-500">
        <Activity size={15} strokeWidth={2} aria-hidden className="text-slate-400" />
        <span>
          Active verification:{" "}
          {activeId ? (
            <span className="font-mono text-[12px] font-medium text-slate-900">{activeId}</span>
          ) : (
            <span className="text-slate-400">none selected</span>
          )}
        </span>
        {activeId ? (
          <button
            type="button"
            onClick={clearActiveId}
            aria-label="Clear active verification"
            className="btn btn-ghost btn-sm -ml-1 h-7 px-2 text-[11px]"
          >
            Clear
          </button>
        ) : null}
      </div>

      <div className="flex items-center gap-2">
        {health === "up" ? (
          <StatusBadge tone="success">API ONLINE</StatusBadge>
        ) : health === "down" ? (
          <StatusBadge tone="danger">API OFFLINE</StatusBadge>
        ) : (
          <StatusBadge tone="neutral">CHECKING</StatusBadge>
        )}
        <span className="badge tone-neutral hidden sm:inline-flex" title="No authentication in this demo build">
          DEMO MODE
        </span>
        <details className="relative md:hidden">
          <summary className="btn btn-secondary btn-sm flex items-center gap-1.5">
            <Menu size={15} aria-hidden />
            Menu
          </summary>
          <nav
            aria-label="Pages"
            className="absolute right-0 z-20 mt-2 w-60 rounded-lg border border-slate-200 bg-white p-1.5 shadow-lg"
          >
            {NAV.map((item) => {
              const active = isActiveNav(pathname, item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-2.5 rounded-md px-3 py-2 text-[13px] ${
                    active
                      ? "bg-brand-50 font-medium text-brand-800"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  }`}
                >
                  <Icon size={15} strokeWidth={1.9} aria-hidden />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </details>
      </div>
    </header>
  );
}
