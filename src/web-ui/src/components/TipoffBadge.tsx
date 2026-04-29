interface TipoffBadgeProps {
  size?: "sm" | "md";
  label?: string;
}

export function TipoffBadge({ size = "md", label = "Community Tipoff" }: TipoffBadgeProps) {
  const sizeClasses =
    size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-0.5 text-xs";
  return (
    <span
      className={`inline-flex items-center rounded-full font-medium bg-amber-100 text-amber-900 border border-amber-200 ${sizeClasses}`}
      data-testid="tipoff-badge"
    >
      {label}
    </span>
  );
}
