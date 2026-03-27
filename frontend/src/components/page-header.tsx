import type { ReactNode } from "react";

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
};

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: PageHeaderProps) {
  return (
    <div className="surface-panel relative mb-6 overflow-hidden rounded-[32px] p-7 sm:flex sm:items-end sm:justify-between">
      <div className="absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,rgba(255,255,255,0),rgba(255,255,255,0.95),rgba(255,255,255,0))]" />
      <div className="absolute -right-16 top-0 h-40 w-40 rounded-full bg-[radial-gradient(circle,rgba(191,219,254,0.5),rgba(191,219,254,0))]" />
      <div className="relative">
        {eyebrow ? (
          <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
            {eyebrow}
          </p>
        ) : null}
        <h2 className="mt-3 max-w-4xl text-4xl font-semibold tracking-[-0.05em] text-slate-950 sm:text-5xl">
          {title}
        </h2>
        <p className="mt-4 max-w-3xl text-[15px] leading-7 text-slate-500">
          {description}
        </p>
      </div>
      {action ? <div className="relative mt-5 shrink-0 sm:mt-0">{action}</div> : null}
    </div>
  );
}
