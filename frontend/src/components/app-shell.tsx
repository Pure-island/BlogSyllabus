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
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(140,180,255,0.18),_transparent_35%),linear-gradient(180deg,_#f4f7fb_0%,_#eef2f7_100%)] text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 px-4 py-5 lg:flex-row lg:px-6">
        <aside className="w-full rounded-[28px] border border-white/70 bg-white/85 p-5 shadow-[0_20px_50px_rgba(15,23,42,0.08)] backdrop-blur lg:sticky lg:top-5 lg:h-[calc(100vh-2.5rem)] lg:w-72">
          <div className="mb-8">
            <p className="text-sm font-medium uppercase tracking-[0.24em] text-sky-600">
              MVP
            </p>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">
              {dictionary.appName}
            </h1>
          </div>

          <nav className="space-y-1.5">
            {navItems.map((item) => {
              const active = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center justify-between rounded-2xl px-4 py-3 text-sm transition ${
                    active
                      ? "bg-slate-950 text-white shadow-lg"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                  }`}
                >
                  <span>{dictionary[item.key]}</span>
                  {active ? <span className="text-xs">●</span> : null}
                </Link>
              );
            })}
          </nav>
        </aside>

        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
