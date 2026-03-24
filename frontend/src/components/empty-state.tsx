export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-[28px] border border-dashed border-slate-300 bg-white/70 px-6 py-16 text-center shadow-[0_10px_30px_rgba(15,23,42,0.04)]">
      <h3 className="text-xl font-semibold text-slate-900">{title}</h3>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-slate-600">
        {description}
      </p>
    </div>
  );
}
