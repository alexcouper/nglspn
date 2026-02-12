"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { CalendarIcon } from "@heroicons/react/24/outline";
import { api, type CompetitionOverview } from "@/lib/api";
import { getPlaceholderColor } from "@/lib/utils";

function formatDateRange(startDate: string, endDate: string): string {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const options: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
    year: "numeric",
  };
  return `${start.toLocaleDateString("en-US", options)} - ${end.toLocaleDateString("en-US", options)}`;
}

export function CompetitionsList() {
  const [competitions, setCompetitions] = useState<CompetitionOverview[]>([]);
  const [pendingProjectsCount, setPendingProjectsCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
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
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-border p-5">
            <div className="flex items-start gap-4">
              <div className="skeleton w-11 h-11 rounded-full" />
              <div className="flex-1">
                <div className="skeleton h-5 w-1/3 mb-2" />
                <div className="skeleton h-4 w-1/2 mb-2" />
                <div className="skeleton h-3 w-1/4" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
        {error}
      </div>
    );
  }

  if (competitions.length === 0) {
    return (
      <p className="text-muted-foreground text-sm text-center py-12">
        {pendingProjectsCount > 0
          ? `${pendingProjectsCount} pending project${pendingProjectsCount !== 1 ? "s" : ""}`
          : "No competitions found."}
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {competitions.map((competition) => (
        <CompetitionCard key={competition.id} competition={competition} />
      ))}
    </div>
  );
}

function CompetitionCard({ competition }: { competition: CompetitionOverview }) {
  const isAcceptingApplications =
    competition.status === "accepting_applications";
  const placeholderColor = getPlaceholderColor(competition.id);

  return (
    <Link
      href={`/competitions/${competition.slug}`}
      className="group block bg-white rounded-xl border border-border p-5 hover:border-slate-300 hover:shadow-sm transition-all"
    >
      <div className="flex items-start gap-4">
        <div
          className={`relative w-11 h-11 rounded-full overflow-hidden flex-shrink-0 ${!competition.image_url ? placeholderColor : ""}`}
        >
          {competition.image_url && (
            <Image
              src={competition.image_url}
              alt={competition.name}
              fill
              className="object-cover"
              sizes="44px"
            />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2.5">
            <h2 className="text-base font-semibold text-foreground group-hover:text-accent transition-colors">
              {competition.name}
            </h2>
            {isAcceptingApplications && (
              <span className="badge badge-success text-xs">
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-1 pulse-dot inline-block" />
                Open
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5 mt-1.5 text-muted-foreground">
            <CalendarIcon className="w-3.5 h-3.5" />
            <span className="text-xs">
              {formatDateRange(competition.start_date, competition.end_date)}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {competition.project_count} project
            {competition.project_count !== 1 ? "s" : ""}
            {competition.pending_projects_count > 0 &&
              ` (${competition.pending_projects_count} pending)`}
          </p>
        </div>
      </div>
    </Link>
  );
}
