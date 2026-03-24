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
    <div className="mb-6 flex flex-col gap-4 rounded-[28px] border border-slate-200/70 bg-white/80 p-6 shadow-[0_18px_50px_rgba(15,23,42,0.08)] backdrop-blur sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow ? (
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-sky-600">
            {eyebrow}
          </p>
        ) : null}
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
          {title}
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">
          {description}
        </p>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
