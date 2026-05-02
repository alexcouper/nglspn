"use client";

import { Tooltip } from "@/components/Tooltip";
import { TipoffExplainer } from "@/components/TipoffExplainer";

interface TipoffBadgeProps {
  size?: "sm" | "md";
  label?: string;
  withTooltip?: boolean;
}

export function TipoffBadge({
  size = "md",
  label = "Community Tipoff",
  withTooltip = false,
}: TipoffBadgeProps) {
  const sizeClasses =
    size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-0.5 text-xs";

  const badge = (
    <span
      className={`inline-flex items-center rounded-full font-medium bg-amber-100 text-amber-900 border border-amber-200 ${sizeClasses}`}
      data-testid="tipoff-badge"
    >
      {label}
    </span>
  );

  if (!withTooltip) return badge;

  return (
    <Tooltip content={<TipoffExplainer />}>
      <button
        type="button"
        aria-label={label}
        className="inline-flex cursor-help focus:outline-none focus:ring-2 focus:ring-amber-300 rounded-full"
      >
        {badge}
      </button>
    </Tooltip>
  );
}
