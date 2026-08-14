"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowPathIcon, TrophyIcon } from "@heroicons/react/24/outline";

import { CompetitionStatusBadge } from "@/components/CompetitionStatusBadge";
import { formatDate } from "@/lib/utils";
import type {
  CompetitionOpportunity,
  CompetitionStanding,
} from "@/lib/api/my-projects";

// Reasons that describe the project rather than any one competition. Repeating
// them per row is noise, so the section states them once.
//
// `community_project` is absent on purpose: a tipoff hides the section
// outright rather than listing rounds it can never enter.
const PROJECT_WIDE_REASONS: Record<string, string> = {
  project_status: "This project can't enter competitions while it's not live.",
  project_draft: "Publish this project before it can enter a competition.",
};

function projectWideReason(
  opportunities: CompetitionOpportunity[]
): string | null {
  if (opportunities.length === 0) return null;
  const reasons = new Set(
    opportunities.map((opportunity) =>
      opportunity.eligible ? "" : (opportunity.reason ?? "")
    )
  );
  if (reasons.size !== 1) return null;
  return PROJECT_WIDE_REASONS[[...reasons][0]] ?? null;
}

interface ProjectCompetitionsProps {
  standing: CompetitionStanding;
  wonCompetitionSlugs?: string[];
  isCommunityTipoff?: boolean;
  onEnter: (competitionId: string) => Promise<void>;
  error?: string;
}

export function ProjectCompetitions({
  standing,
  wonCompetitionSlugs = [],
  isCommunityTipoff = false,
  onEnter,
  error,
}: ProjectCompetitionsProps) {
  const [enteringId, setEnteringId] = useState<string | null>(null);
  // The parent reports what it knows through `error`. This covers the case it
  // can't: `onEnter` rejecting outright, which would otherwise leave the row
  // looking untouched and the failure only in the console.
  const [unreportedError, setUnreportedError] = useState("");
  const { entries, opportunities } = standing;
  const collapsedReason = projectWideReason(opportunities);

  const handleEnter = async (competitionId: string) => {
    setEnteringId(competitionId);
    setUnreportedError("");
    try {
      await onEnter(competitionId);
    } catch {
      setUnreportedError("Couldn't enter this competition. Please try again.");
    } finally {
      setEnteringId(null);
    }
  };

  const shownError = error || unreportedError;

  // Tipoffs never enter competitions, so listing rounds and explaining why
  // they're out of reach is noise on a page about somebody else's project.
  if (isCommunityTipoff) return null;

  // No card chrome: this renders inside the Settings tab panel, which is
  // already a card. Nesting one in the other reads as an afterthought bolted
  // on, which is what it used to be.
  return (
    <section>
      <h3 className="text-foreground font-medium">Competitions</h3>

      {shownError && (
        <p role="alert" className="text-red-600 text-sm mt-3">
          {shownError}
        </p>
      )}

      {entries.length > 0 && (
        <ul className="mt-4 divide-y divide-border">
          {entries.map((entry) => (
            <li
              key={entry.competition.id}
              className="py-3 flex flex-wrap items-center gap-x-3 gap-y-1"
            >
              <Link
                href={`/competitions/${entry.competition.slug}`}
                className="text-accent hover:text-accent-hover font-medium text-sm transition-colors"
              >
                {entry.competition.name}
              </Link>
              {wonCompetitionSlugs.includes(entry.competition.slug) && (
                <span className="inline-flex items-center gap-1 text-amber-600 text-xs font-medium">
                  <TrophyIcon className="w-3.5 h-3.5" />
                  Won
                </span>
              )}
              <span className="text-muted-foreground text-xs">
                Entered {formatDate(entry.entered_at)}
              </span>
              <CompetitionStatusBadge
                status={entry.competition.status}
                className="text-xs"
              />
            </li>
          ))}
        </ul>
      )}

      {opportunities.length > 0 && (
        <>
          {/* "Other": the server no longer reports a round the project is
              already in as an opportunity, so everything here is a round it
              isn't in. */}
          <h4 className="text-muted-foreground text-xs font-medium uppercase tracking-wide mt-5">
            Other rounds open now
          </h4>
          {collapsedReason && (
            <p className="text-muted-foreground text-sm mt-2">
              {collapsedReason}
            </p>
          )}
          <ul className="mt-2 divide-y divide-border">
            {opportunities.map((opportunity) => (
              <li
                key={opportunity.competition.id}
                className="py-3 flex flex-wrap items-center justify-between gap-3"
              >
                <div>
                  <Link
                    href={`/competitions/${opportunity.competition.slug}`}
                    className="text-accent hover:text-accent-hover font-medium text-sm transition-colors"
                  >
                    {opportunity.competition.name}
                  </Link>
                  <p className="text-muted-foreground text-xs mt-0.5">
                    Deadline{" "}
                    {formatDate(opportunity.competition.submission_deadline)}
                  </p>
                  {!opportunity.eligible &&
                    !collapsedReason &&
                    opportunity.reason === "already_in_series" && (
                      <p className="text-muted-foreground text-xs mt-1">
                        Already in this run of competitions with{" "}
                        {opportunity.blocking_entry?.name ??
                          "an earlier round"}
                        .
                      </p>
                    )}
                </div>
                {opportunity.eligible && (
                  <button
                    onClick={() => handleEnter(opportunity.competition.id)}
                    disabled={enteringId !== null}
                    className="btn-primary text-sm py-1.5 px-3 flex-shrink-0"
                  >
                    {enteringId === opportunity.competition.id ? (
                      <ArrowPathIcon className="w-4 h-4 animate-spin" />
                    ) : (
                      `Enter in ${opportunity.competition.name}`
                    )}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </>
      )}

      {/* With entered rounds excluded from opportunities, an empty list means
          "nothing else on offer" for a project already in a round — telling it
          no round is open would be false while it sits in three of them. */}
      {opportunities.length === 0 && (
        <p className="text-muted-foreground text-sm mt-3">
          {entries.length > 0
            ? "No other round is open right now."
            : "No round is currently open. This project can enter the next one."}
        </p>
      )}
    </section>
  );
}
