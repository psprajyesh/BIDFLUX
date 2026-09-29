"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import { isActiveNav, NAV } from "@/lib/nav";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 flex-col bg-chrome text-slate-300 md:flex">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <span className="grid h-8 w-8 place-items-center rounded-md bg-brand-700">
          <ShieldCheck size={18} className="text-white" aria-hidden />
        </span>
        <span className="text-[15px] font-semibold tracking-tight text-white">BIDFLUX</span>
      </div>

      <nav className="flex-1 space-y-0.5 px-3" aria-label="Main">
        {NAV.map((item) => {
          const active = isActiveNav(pathname, item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-2.5 rounded-md px-3 py-2 text-[13px] transition-colors ${
                active
                  ? "bg-brand-700 font-medium text-white"
                  : "text-slate-400 hover:bg-slate-800/70 hover:text-slate-100"
              }`}
            >
              <Icon size={16} strokeWidth={1.9} aria-hidden />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-slate-800 px-5 py-4">
        <p className="text-[11px] leading-4 text-slate-500">
          Smart India Hackathon 2026
          <br />
          AI-assisted tender verification
        </p>
      </div>
    </aside>
  );
}
