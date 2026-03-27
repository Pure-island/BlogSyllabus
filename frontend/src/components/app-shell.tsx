"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useI18n } from "@/components/language-provider";

const navItems = [
  { href: "/", key: "navDashboard" },
  { href: "/sources", key: "navSources" },
  { href: "/inbox", key: "navInbox" },
  { href: "/curriculum", key: "navCurriculum" },
  { href: "/today", key: "navToday" },
  { href: "/log", key: "navLog" },
  { href: "/progress", key: "navProgress" },
  { href: "/weekly", key: "navWeekly" },
  { href: "/settings", key: "navSettings" },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { dictionary } = useI18n();

  return (
    <div className="min-h-screen text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 px-4 py-5 lg:flex-row lg:px-6">
        <aside className="surface-panel w-full rounded-[32px] p-5 lg:sticky lg:top-5 lg:h-[calc(100vh-2.5rem)] lg:w-72">
          <div className="mb-8 overflow-hidden rounded-[28px] border border-white/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(255,255,255,0.7))] px-5 py-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[linear-gradient(180deg,#ffffff,#eef2ff)] shadow-[0_8px_24px_rgba(15,23,42,0.08)]">
              <div className="h-5 w-5 rounded-full bg-[linear-gradient(180deg,#4f46e5,#111827)]" />
            </div>
            <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
              Guided Reading
            </p>
            <h1 className="mt-2 text-[28px] font-semibold tracking-[-0.04em] text-slate-950">
              {dictionary.appName}
            </h1>
            <p className="mt-3 text-sm leading-6 text-slate-500">
              RSS-driven curriculum, daily momentum, and thoughtful review.
            </p>
          </div>

          <div className="rounded-[28px] border border-white/70 bg-white/45 p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.65)]">
            <nav className="space-y-1.5">
              {navItems.map((item) => {
                const active = pathname === item.href;

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center justify-between rounded-2xl px-4 py-3 text-sm transition ${
                      active
                        ? "bg-white text-slate-950 shadow-[0_10px_28px_rgba(15,23,42,0.08)]"
                        : "text-slate-500 hover:bg-white/70 hover:text-slate-950"
                    }`}
                  >
                    <span className={active ? "font-semibold" : "font-medium"}>{dictionary[item.key]}</span>
                    {active ? <span className="h-2.5 w-2.5 rounded-full bg-slate-950" /> : null}
                  </Link>
                );
              })}
            </nav>
          </div>
        </aside>

        <main className="min-w-0 flex-1 lg:pl-2">{children}</main>
      </div>
    </div>
  );
}
