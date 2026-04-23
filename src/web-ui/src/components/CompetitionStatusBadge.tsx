"use client";

import { useTranslations } from "next-intl";
import { Translatable } from "@/components/Translatable";

type CompetitionStatus = "pending" | "accepting_applications" | "voting" | "closed";

interface CompetitionStatusBadgeProps {
  status: CompetitionStatus;
  className?: string;
}

export function CompetitionStatusBadge({ status, className = "" }: CompetitionStatusBadgeProps) {
  const t = useTranslations();
  switch (status) {
    case "accepting_applications":
      return (
        <span className={`badge badge-success ${className}`}>
          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-1.5 pulse-dot inline-block" />
          <Translatable tKey="competitions.status.open">{t("competitions.status.open")}</Translatable>
        </span>
      );
    case "voting":
      return (
        <span className={`badge bg-violet-500 text-white ${className}`}>
          <span className="w-1.5 h-1.5 bg-white rounded-full mr-1.5 pulse-dot inline-block" />
          <Translatable tKey="competitions.status.voting">{t("competitions.status.voting")}</Translatable>
        </span>
      );
    case "closed":
      return (
        <span className={`badge bg-slate-800/80 backdrop-blur-sm text-white ${className}`}>
          <Translatable tKey="competitions.status.completed">{t("competitions.status.completed")}</Translatable>
        </span>
      );
    default:
      return null;
  }
}
