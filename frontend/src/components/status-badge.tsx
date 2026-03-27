type StatusBadgeProps = {
  label: string;
  tone?: "neutral" | "success" | "danger" | "warning";
};

const toneClasses: Record<NonNullable<StatusBadgeProps["tone"]>, string> = {
  neutral: "border border-slate-200/80 bg-white/70 text-slate-600",
  success: "border border-emerald-200/80 bg-emerald-50/90 text-emerald-700",
  danger: "border border-rose-200/80 bg-rose-50/90 text-rose-700",
  warning: "border border-amber-200/80 bg-amber-50/90 text-amber-700",
};

export function StatusBadge({
  label,
  tone = "neutral",
}: StatusBadgeProps) {
  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-[11px] font-semibold tracking-[0.01em] ${toneClasses[tone]}`}>
      {label}
    </span>
  );
}
