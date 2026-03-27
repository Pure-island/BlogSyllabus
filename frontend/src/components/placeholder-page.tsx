"use client";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { useI18n } from "@/components/language-provider";

export function PlaceholderPage({ title }: { title: string }) {
  const { dictionary } = useI18n();

  return (
    <section className="pb-8">
      <PageHeader
        eyebrow="Scaffold"
        title={title}
        description={dictionary.overviewDescription}
      />
      <EmptyState
        title={dictionary.empty}
        description={dictionary.overviewDescription}
      />
    </section>
  );
}
