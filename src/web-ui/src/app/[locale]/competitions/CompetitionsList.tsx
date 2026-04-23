"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { api, type CompetitionOverview } from "@/lib/api";
import { GradientPlaceholder } from "@/components/GradientPlaceholder";
import { Translatable } from "@/components/Translatable";
import { CompetitionStatusBadge } from "@/components/CompetitionStatusBadge";

function formatDateRange(startDate: string, endDate: string): string {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const options: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
    year: "numeric",
  };
  return `${start.toLocaleDateString("en-US", options)} – ${end.toLocaleDateString("en-US", options)}`;
}

function formatPrize(amount: string): string {
  const num = parseInt(amount, 10);
  if (isNaN(num)) return amount;
  return `${num.toLocaleString("de-DE")} kr.`;
}

interface CompetitionsListProps {
  initialCompetitions?: CompetitionOverview[] | null;
  initialPendingCount?: number;
}

export function CompetitionsList({
  initialCompetitions,
  initialPendingCount = 0,
}: CompetitionsListProps) {
  const t = useTranslations();
  const hasInitialData = initialCompetitions != null;
  const [competitions, setCompetitions] = useState<CompetitionOverview[]>(
    initialCompetitions ?? []
  );
  const [pendingProjectsCount, setPendingProjectsCount] =
    useState(initialPendingCount);
  const [isLoading, setIsLoading] = useState(!hasInitialData);
  const [error, setError] = useState("");

  useEffect(() => {
    if (hasInitialData) return;

    const fetchCompetitions = async () => {
      setIsLoading(true);
      setError("");
      try {
        const data = await api.competitions.list();
        const sorted = [...data.competitions].sort(
          (a, b) =>
            new Date(b.start_date).getTime() - new Date(a.start_date).getTime()
        );
        setCompetitions(sorted);
        setPendingProjectsCount(data.pending_projects_count);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to fetch competitions"
        );
      }
      setIsLoading(false);
    };

    fetchCompetitions();
  }, [hasInitialData]);

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
        {error}
      </div>
    );
  }

  const visible = competitions.filter((c) => c.status !== "pending");

  if (visible.length === 0) {
    return (
      <p className="text-muted-foreground text-sm text-center py-12">
        {pendingProjectsCount > 0
          ? t("competitions.pendingProjects", { count: pendingProjectsCount })
          : t("competitions.empty")}
      </p>
    );
  }

  const activeCompetitions = visible.filter(
    (c) => c.status === "accepting_applications"
  );
  const featured =
    activeCompetitions.length > 0
      ? activeCompetitions.reduce((latest, c) =>
          new Date(c.start_date) > new Date(latest.start_date) ? c : latest
        )
      : null;
  const grid = visible.filter((c) => c.id !== featured?.id);

  return (
    <div>
      {featured && <HeroBanner competition={featured} />}

      {grid.length > 0 && (
        <div>
          {featured && (
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mt-6 mb-3">
              <Translatable tKey="competitions.pastCompetitions">{t("competitions.pastCompetitions")}</Translatable>
            </h2>
          )}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4">
            {grid.map((competition) => (
              <GridCard key={competition.id} competition={competition} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function HeroBanner({ competition }: { competition: CompetitionOverview }) {
  const t = useTranslations();
  return (
    <Link
      href={`/competitions/${competition.slug}`}
      className="group block"
    >
      <div className="card card-interactive overflow-hidden">
        <div className="relative aspect-[16/7]">
          {(competition.image_wide_url ?? competition.image_url) ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={(competition.image_wide_url ?? competition.image_url)!}
              alt={competition.name}
              className="absolute inset-0 w-full h-full object-cover"
            />
          ) : (
            <GradientPlaceholder
              id={competition.id}
              className="absolute inset-0 w-full h-full"
            />
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-[rgba(15,23,42,0.9)] via-[rgba(15,23,42,0.3)] to-transparent" />
          <div className="absolute bottom-0 left-0 right-0 p-5 sm:p-6">
            <CompetitionStatusBadge status={competition.status} className="text-xs mb-2" />
            <h2 className="text-xl sm:text-2xl font-bold text-white group-hover:text-indigo-200 transition-colors">
              {competition.name}
            </h2>
            <p className="text-slate-300 text-sm mt-1">
              {formatDateRange(competition.start_date, competition.submission_deadline)}
              {" · "}
              {t("competitions.projectCount", { count: competition.project_count })}
              {competition.prize_amount &&
                ` · ${formatPrize(competition.prize_amount)}`}
            </p>
          </div>
        </div>
      </div>
    </Link>
  );
}

function GridCard({ competition }: { competition: CompetitionOverview }) {
  const t = useTranslations();
  return (
    <Link
      href={`/competitions/${competition.slug}`}
      className="group block"
    >
      <div className="card card-interactive overflow-hidden">
        <div className="relative aspect-square">
          {competition.image_url ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={competition.image_url}
              alt={competition.name}
              className="absolute inset-0 w-full h-full object-cover"
            />
          ) : (
            <GradientPlaceholder
              id={competition.id}
              className="absolute inset-0 w-full h-full"
            />
          )}
        </div>
        <div className="bg-[#0f172a] p-3 sm:p-4">
          <div className="flex items-center gap-2">
            <h3 className="text-sm sm:text-base font-semibold text-white group-hover:text-indigo-200 transition-colors truncate">
              {competition.name}
            </h3>
            {competition.status !== "closed" && competition.status !== "pending" && (
              <CompetitionStatusBadge status={competition.status} className="text-xs flex-shrink-0" />
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {t("competitions.projectCount", { count: competition.project_count })}
          </p>
        </div>
      </div>
    </Link>
  );
}

function LoadingSkeleton() {
  return (
    <div>
      {/* Hero skeleton */}
      <div className="rounded-xl overflow-hidden border border-border">
        <div className="skeleton aspect-[16/7]" />
        <div className="bg-[#0f172a] p-5">
          <div className="skeleton h-4 w-24 mb-3" style={{ opacity: 0.3 }} />
          <div className="skeleton h-6 w-48 mb-2" style={{ opacity: 0.3 }} />
          <div className="skeleton h-4 w-64" style={{ opacity: 0.3 }} />
        </div>
      </div>
      {/* Grid skeleton */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4 mt-6">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="rounded-xl overflow-hidden border border-border"
          >
            <div className="skeleton aspect-square" />
            <div className="bg-[#0f172a] p-3 sm:p-4">
              <div
                className="skeleton h-4 w-2/3 mb-2"
                style={{ opacity: 0.3 }}
              />
              <div
                className="skeleton h-3 w-1/3"
                style={{ opacity: 0.3 }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
