"use client";

import Link from "next/link";
import type { CompetitionSummary } from "@/lib/api";

function formatPrizeAmount(amount: string | null): string {
  if (!amount) return "";
  const num = parseFloat(amount);
  return new Intl.NumberFormat("is-IS").format(num) + " ISK";
}

function CompetitionCard({ competition }: { competition: CompetitionSummary }) {
  const isOpen = competition.status === "accepting_applications";

  const end = new Date(competition.end_date);
  const now = new Date();
  const diffTime = end.getTime() - now.getTime();
  const daysRemaining = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  const daysSinceClosed = Math.floor(-diffTime / (1000 * 60 * 60 * 24));
  const prizeText = formatPrizeAmount(competition.prize_amount ?? null);
  const projectCount = competition.project_count;

  return (
    <Link
      href={`/competitions/${competition.slug}`}
      className="group card card-interactive flex flex-col w-full max-w-sm"
    >
      {/* Image */}
      <div className={`aspect-[16/10] relative ${!competition.image_url ? "bg-gradient-to-br from-slate-100 to-slate-200" : ""}`}>
        {competition.image_url ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={competition.image_url}
            alt={competition.name}
            className="w-full h-full object-contain"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <svg className="w-10 h-10 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M17.25 4.236c.982.143 1.954.317 2.916.52A6.003 6.003 0 0014.77 9.728M17.25 4.236V4.5c0 2.108-.966 3.99-2.48 5.228m2.48-5.492a46.32 46.32 0 012.916.52 6.003 6.003 0 01-5.395 4.972m0 0a48.667 48.667 0 01-4.59 0m4.59 0a7.454 7.454 0 01-.982 3.172M9.497 14.25a7.454 7.454 0 01.981-3.172" />
            </svg>
          </div>
        )}
        {/* Status badge */}
        <div className="absolute top-3 left-3">
          {isOpen ? (
            <span className="badge bg-emerald-500 text-white text-xs font-medium px-2.5 py-1">
              <span className="w-1.5 h-1.5 bg-white rounded-full mr-1.5 pulse-dot inline-block" />
              Open
            </span>
          ) : (
            <span className="badge bg-slate-800/80 backdrop-blur-sm text-white text-xs font-medium px-2.5 py-1">
              Completed
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-4 flex-1 flex flex-col">
        <h3 className="font-semibold text-foreground text-sm group-hover:text-accent transition-colors">
          {competition.name}
        </h3>
        <div className="mt-auto pt-3 flex items-center justify-between text-xs text-muted-foreground">
          {isOpen ? (
            <>
              <span>{daysRemaining} {daysRemaining === 1 ? "day" : "days"} remaining</span>
              {prizeText && <span className="font-medium text-emerald-600">{prizeText}</span>}
            </>
          ) : (
            <>
              <span>{daysSinceClosed}d ago</span>
              <span>{projectCount} {projectCount === 1 ? "project" : "projects"}</span>
            </>
          )}
        </div>
      </div>
    </Link>
  );
}

interface CompetitionHighlightProps {
  active: CompetitionSummary | null;
  recent: CompetitionSummary | null;
}

export function CompetitionHighlight({ active, recent }: CompetitionHighlightProps) {
  if (!active && !recent) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground text-sm">More competitions coming soon</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col sm:flex-row items-stretch justify-center gap-6">
      {recent && <CompetitionCard competition={recent} />}
      {active && <CompetitionCard competition={active} />}
    </div>
  );
}
