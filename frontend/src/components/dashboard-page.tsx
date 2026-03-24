"use client";

import Link from "next/link";

import { PageHeader } from "@/components/page-header";
import { useI18n } from "@/components/language-provider";

const quickLinks = [
  { href: "/sources", accent: "from-sky-500 to-cyan-400" },
  { href: "/inbox", accent: "from-emerald-500 to-lime-400" },
  { href: "/settings", accent: "from-amber-500 to-orange-400" },
] as const;

export function DashboardPage() {
  const { dictionary } = useI18n();
  const cards = [
    {
      title: dictionary.navSources,
      description: dictionary.sourcesDescription,
    },
    {
      title: dictionary.navInbox,
      description: dictionary.inboxDescription,
    },
    {
      title: dictionary.navSettings,
      description: dictionary.settingsDescription,
    },
  ];

  return (
    <section className="pb-8">
      <PageHeader
        eyebrow="Research Flow"
        title={dictionary.overviewTitle}
        description={dictionary.overviewDescription}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        {cards.map((card, index) => (
          <Link
            key={card.title}
            href={quickLinks[index].href}
            className="group overflow-hidden rounded-[28px] border border-slate-200/70 bg-white/90 p-6 shadow-[0_16px_50px_rgba(15,23,42,0.08)] transition hover:-translate-y-0.5 hover:shadow-[0_24px_70px_rgba(15,23,42,0.12)]"
          >
            <div
              className={`h-2 w-24 rounded-full bg-gradient-to-r ${quickLinks[index].accent}`}
            />
            <h3 className="mt-6 text-xl font-semibold text-slate-950">
              {card.title}
            </h3>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              {card.description}
            </p>
            <span className="mt-6 inline-flex text-sm font-semibold text-slate-950">
              Open
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
