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
        description={dictionary.placeholderDescription}
      />
      <EmptyState
        title={dictionary.placeholderTitle}
        description={dictionary.placeholderDescription}
      />
    </section>
  );
}
