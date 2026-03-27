export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="surface-soft rounded-[32px] px-6 py-16 text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-white/90 shadow-[0_10px_24px_rgba(15,23,42,0.06)]">
        <div className="h-3 w-3 rounded-full bg-slate-300" />
      </div>
      <h3 className="mt-5 text-[22px] font-semibold tracking-[-0.03em] text-slate-900">{title}</h3>
      <p className="mx-auto mt-3 max-w-xl text-[15px] leading-7 text-slate-500">
        {description}
      </p>
    </div>
  );
}
