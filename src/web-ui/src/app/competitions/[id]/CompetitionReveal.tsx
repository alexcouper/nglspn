"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { TrophyIcon, RocketLaunchIcon } from "@heroicons/react/24/solid";
import { api, type Competition, type CompetitionProject } from "@/lib/api";
import { ApiRequestError } from "@/lib/api/base";
import { useAuth } from "@/contexts/auth";
import { formatDateRange, pickVariant } from "@/lib/utils";
import { GradientPlaceholder } from "@/components/GradientPlaceholder";
import { CompetitionStatusBadge } from "@/components/CompetitionStatusBadge";
import { MyRanking } from "./MyRanking";
import type { ReviewState } from "./types";

function formatPrize(amount: string): string {
  const num = parseInt(amount, 10);
  if (isNaN(num)) return amount;
  return `${num.toLocaleString("de-DE")} kr.`;
}

interface CompetitionRevealProps {
  initialCompetition: Competition;
}

export function CompetitionReveal({ initialCompetition }: CompetitionRevealProps) {
  const [competition] = useState<Competition>(initialCompetition);
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [fetchedState, setFetchedState] = useState<ReviewState>({ kind: "loading" });

  const isOpen = competition.status === "accepting_applications";
  const isVoting = competition.status === "voting";
  const returnPath = `/competitions/${competition.slug ?? competition.id}`;

  useEffect(() => {
    if (!isVoting || authLoading || !isAuthenticated) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await api.myReview.getCompetition(competition.id);
        if (cancelled) return;
        setFetchedState({
          kind: "ready",
          data,
          ranked: data.ranked_projects,
          pool: data.pool_projects,
        });
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiRequestError && err.status === 404) {
          setFetchedState({ kind: "not-assigned" });
          return;
        }
        setFetchedState({
          kind: "error",
          message: err instanceof Error ? err.message : "Failed to load ranking",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [competition.id, isVoting, authLoading, isAuthenticated]);

  const reviewState: ReviewState = !isVoting
    ? { kind: "not-assigned" }
    : authLoading
      ? { kind: "loading" }
      : !isAuthenticated
        ? { kind: "logged-out" }
        : fetchedState;

  const isRankingSurfaceActive =
    reviewState.kind === "ready" || reviewState.kind === "loading";

  return (
    <div className="space-y-8">
      {/* Hero Banner */}
      <div className="rounded-xl overflow-hidden">
        <div className="relative aspect-[16/7]">
          {(() => {
            const heroImage = competition.winner
              ? (competition.image_wide_winner_url ?? competition.image_wide_url ?? competition.image_url)
              : (competition.image_wide_url ?? competition.image_url);
            return heroImage ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={heroImage}
                alt={competition.name}
                className="absolute inset-0 w-full h-full object-cover"
              />
            ) : (
              <GradientPlaceholder
                id={competition.id}
                className="absolute inset-0 w-full h-full"
              />
            );
          })()}
          <div className="absolute inset-0 bg-gradient-to-t from-[rgba(15,23,42,0.9)] via-[rgba(15,23,42,0.4)] to-[rgba(15,23,42,0.15)]" />
          <div className="absolute bottom-0 left-0 right-0 p-5 sm:p-8">
            {(isOpen || isVoting) && (
              <div className="mb-3">
                <CompetitionStatusBadge status={competition.status} className="text-xs" />
              </div>
            )}
            <h1 className="text-2xl sm:text-4xl font-bold text-white tracking-tight">
              {competition.name}
            </h1>
            <p className="text-slate-300 text-sm sm:text-base mt-2">
              {formatDateRange(
                competition.start_date,
                competition.submission_deadline,
                { year: "numeric", month: "long", day: "numeric" },
              )}
              {competition.prize_amount &&
                ` · ${formatPrize(competition.prize_amount)} prize`}
              {" · "}
              {competition.project_count} project
              {competition.project_count !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
      </div>

      {/* CTA Banner - only when accepting submissions */}
      {isOpen && (
        <div className="bg-white rounded-xl border border-border p-5 sm:p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-foreground font-semibold text-lg">
              Got a project you&apos;re working on?
            </h2>
            <p className="text-muted-foreground text-sm mt-1">
              {isAuthenticated
                ? `Enter one you've already added, or start a new one, and compete in ${competition.name}`
                : `Share your project with the community and compete in ${competition.name}`}
            </p>
          </div>
          <Link
            /* Signed in, the chooser is the useful landing: it lists projects
               eligible for this round above the new-project form. */
            href={
              isAuthenticated
                ? `/submit?competition=${competition.id}`
                : "/submit"
            }
            className="btn-primary flex-shrink-0 inline-flex items-center gap-2"
          >
            <RocketLaunchIcon className="w-4 h-4" />
            Submit a Project
          </Link>
        </div>
      )}

      {/* Voting banner */}
      {isVoting && (
        <div className="bg-violet-50 rounded-xl border border-violet-200 p-5 sm:p-6 flex items-center gap-3">
          <span className="w-2 h-2 bg-violet-500 rounded-full pulse-dot flex-shrink-0" />
          <p className="text-violet-800 font-medium text-sm">
            {isRankingSurfaceActive
              ? "Voting is in progress. Rank the projects below to help pick the winner."
              : "Voting is in progress. Selected members are ranking the projects."}
          </p>
        </div>
      )}

      {/* My Ranking — embedded voting flow during voting period */}
      {isVoting && (
        <MyRanking
          competitionId={competition.id}
          competitionName={competition.name}
          returnPath={returnPath}
          reviewState={reviewState}
        />
      )}

      {/* Quote */}
      {competition.quote && (
        <blockquote className="bg-white rounded-xl border border-border p-5 border-l-3 border-l-accent">
          <p className="text-sm text-muted-foreground italic leading-relaxed">
            &ldquo;{competition.quote}&rdquo;
          </p>
        </blockquote>
      )}

      {/* Winner */}
      {competition.winner && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <TrophyIcon className="w-5 h-5 text-amber-500" />
            <h2 className="text-lg font-semibold text-foreground">Winner</h2>
          </div>
          <WinnerCard project={competition.winner} />
        </div>
      )}

      {/* Projects — suppressed when the ranked-cards surface is rendering. */}
      {!isRankingSurfaceActive && (
        <div>
          <div className="flex items-baseline gap-2 mb-4">
            <h2 className="text-lg font-semibold text-foreground">
              All Projects
            </h2>
            <span className="text-sm text-muted-foreground">
              ({competition.projects.length})
            </span>
          </div>
          {competition.projects.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4">
              {competition.projects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  isWinner={project.id === competition.winner?.id}
                />
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-sm text-center py-8">
              No projects yet — be the first to submit!
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function WinnerCard({ project }: { project: CompetitionProject }) {
  const imageUrl =
    pickVariant(project.main_image_variants, "medium") ??
    project.main_image_url;

  return (
    <Link
      href={`/projects/${project.slug ?? project.id}`}
      className="group block"
    >
      <div className="card card-interactive overflow-hidden border-amber-200 hover:shadow-[0_0_20px_rgba(251,191,36,0.15)]">
        <div className="flex flex-col sm:flex-row">
          <div className="relative aspect-[4/3] sm:w-72 sm:aspect-auto sm:h-44">
            {imageUrl ? (
              <>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={imageUrl}
                  alt={project.title}
                  className="absolute inset-0 w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[rgba(0,0,0,0.15)] to-transparent" />
              </>
            ) : (
              <GradientPlaceholder
                id={project.id}
                className="absolute inset-0 w-full h-full"
              />
            )}
            <span className="absolute top-2 right-2 bg-amber-400 text-amber-900 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full">
              Winner
            </span>
          </div>
          <div className="p-4 sm:p-5 flex-1 flex flex-col justify-center">
            <h3 className="font-semibold text-lg text-foreground group-hover:text-accent transition-colors">
              {project.title || "Untitled"}
            </h3>
          </div>
        </div>
      </div>
    </Link>
  );
}

function ProjectCard({
  project,
  isWinner,
}: {
  project: CompetitionProject;
  isWinner: boolean;
}) {
  const imageUrl =
    pickVariant(project.main_image_variants, "thumb") ??
    project.main_image_url;

  return (
    <Link
      href={`/projects/${project.slug ?? project.id}`}
      className="group block"
    >
      <div
        className={`card card-interactive overflow-hidden ${
          isWinner ? "border-amber-300 ring-1 ring-amber-200" : ""
        }`}
      >
        <div className="relative aspect-[4/3]">
          {imageUrl ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={imageUrl}
                alt={project.title}
                className="absolute inset-0 w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[rgba(0,0,0,0.15)] to-transparent" />
            </>
          ) : (
            <GradientPlaceholder
              id={project.id}
              className="absolute inset-0 w-full h-full"
            />
          )}
          {isWinner && (
            <div className="absolute top-2 right-2 bg-amber-500 text-white p-1 rounded-full shadow-sm">
              <TrophyIcon className="w-3.5 h-3.5" />
            </div>
          )}
        </div>
        <div className="p-3 sm:p-3.5">
          <h3 className="font-medium text-sm text-foreground truncate group-hover:text-accent transition-colors">
            {project.title || "Untitled"}
          </h3>
        </div>
      </div>
    </Link>
  );
}
