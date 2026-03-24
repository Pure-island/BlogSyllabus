type StatusBadgeProps = {
  label: string;
  tone?: "neutral" | "success" | "danger" | "warning";
};

const toneClasses: Record<NonNullable<StatusBadgeProps["tone"]>, string> = {
  neutral: "bg-slate-100 text-slate-700",
  success: "bg-emerald-100 text-emerald-700",
  danger: "bg-rose-100 text-rose-700",
  warning: "bg-amber-100 text-amber-700",
};

export function StatusBadge({
  label,
  tone = "neutral",
}: StatusBadgeProps) {
  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${toneClasses[tone]}`}>
      {label}
    </span>
  );
}
