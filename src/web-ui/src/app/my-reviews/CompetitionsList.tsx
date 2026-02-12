"use client";

import Image from "next/image";
import Link from "next/link";
import { CheckCircleIcon } from "@heroicons/react/24/solid";
import type { ReviewCompetition } from "@/lib/api";
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

interface CompetitionsListProps {
  competitions: ReviewCompetition[];
}

export function CompetitionsList({ competitions }: CompetitionsListProps) {
  if (competitions.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-border p-8 text-center">
        <p className="text-muted-foreground text-sm">
          No competitions assigned to you for review.
        </p>
      </div>
    );
  }

  const inProgress = competitions.filter(
    (c) => c.my_review_status === "in_progress"
  );
  const completed = competitions.filter(
    (c) => c.my_review_status === "completed"
  );

  return (
    <div className="space-y-6">
      {inProgress.length > 0 && (
        <div className="space-y-3">
          {inProgress.map((competition) => {
            const placeholderColor = getPlaceholderColor(competition.id);
            return (
              <Link
                key={competition.id}
                href={`/my-reviews/${competition.id}`}
                className="group flex items-start gap-4 w-full text-left bg-white rounded-xl border border-border p-5 hover:border-slate-300 hover:shadow-sm transition-all"
              >
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
                  <h2 className="font-medium text-foreground group-hover:text-accent transition-colors">
                    {competition.name}
                  </h2>
                  <p className="text-muted-foreground text-xs mt-1">
                    {formatDateRange(competition.start_date, competition.end_date)}
                  </p>
                  <p className="text-muted-foreground text-xs mt-1">
                    {competition.project_count} project
                    {competition.project_count !== 1 ? "s" : ""} to review
                  </p>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {completed.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Completed
          </h3>
          {completed.map((competition) => {
            const placeholderColor = getPlaceholderColor(competition.id);
            return (
              <Link
                key={competition.id}
                href={`/my-reviews/${competition.id}`}
                className="group flex items-start gap-4 w-full text-left bg-muted rounded-xl border border-border p-5 hover:border-slate-300 transition-all"
              >
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
                  <div className="flex items-center justify-between">
                    <h2 className="font-medium text-muted-foreground group-hover:text-foreground transition-colors">
                      {competition.name}
                    </h2>
                    <CheckCircleIcon className="w-4 h-4 text-emerald-500" />
                  </div>
                  <p className="text-muted-foreground text-xs mt-1">
                    {formatDateRange(competition.start_date, competition.end_date)}
                  </p>
                  <p className="text-muted-foreground text-xs mt-1">
                    {competition.project_count} project
                    {competition.project_count !== 1 ? "s" : ""} reviewed
                  </p>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
