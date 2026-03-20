"use client";

import { getPlaceholderColor } from "@/lib/utils";

export function GradientPlaceholder({
  id,
  className = "",
}: {
  id: string;
  className?: string;
}) {
  const colorClass = getPlaceholderColor(id);
  return <div className={`${colorClass} ${className}`} />;
}
