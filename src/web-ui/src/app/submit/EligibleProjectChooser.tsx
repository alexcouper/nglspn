"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { api, type Project } from "@/lib/api";
import { describeApiError } from "@/lib/api/errors";
import { formatDate } from "@/lib/utils";
import type { CompetitionOpportunity } from "@/lib/api/my-projects";

function eligibleOpportunities(
  project: Project,
  competitionId: string | null
): CompetitionOpportunity[] {
  return (project.competition_standing?.opportunities ?? []).filter(
    (opportunity) =>
      opportunity.eligible &&
      (competitionId === null || opportunity.competition.id === competitionId)
  );
}

/**
 * Entering an existing project, above the form for starting a new one. Reads
 * `GET /api/my/projects`, which already carries the standing — no endpoint of
 * its own.
 *
 * `?competition=<id>` narrows the list to that round; absent means "anything
 * the user could enter". Wrapped in Suspense because useSearchParams opts the
 * subtree out of prerendering, and the create form below must still be static.
 */
export function EligibleProjectChooser() {
  return (
    <Suspense fallback={null}>
      <Chooser />
    </Suspense>
  );
}

function Chooser() {
  const competitionId = useSearchParams().get("competition");
  const [projects, setProjects] = useState<Project[]>([]);
  const [entered, setEntered] = useState<Record<string, string>>({});
  const [enteringId, setEnteringId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.myProjects.list().then(
      (all) => {
        if (!cancelled) setProjects(all);
      },
      () => {
        // A chooser that cannot load is simply absent; the create form below
        // is still the whole point of the page.
        if (!cancelled) setProjects([]);
      }
    );
    return () => {
      cancelled = true;
    };
  }, []);

  const candidates = projects
    .map((project) => ({
      project,
      opportunities: eligibleOpportunities(project, competitionId),
    }))
    .filter(({ opportunities }) => opportunities.length > 0);

  if (candidates.length === 0) return null;

  const namedCompetition =
    competitionId !== null
      ? (candidates[0].opportunities[0]?.competition ?? null)
      : null;

  const handleEnter = async (projectId: string, competition: string) => {
    setEnteringId(projectId);
    setError("");
    try {
      await api.myProjects.enterCompetition(projectId, competition);
      setEntered((current) => ({ ...current, [projectId]: competition }));
    } catch (err) {
      setError(describeApiError(err, "Couldn't enter this project."));
    } finally {
      setEnteringId(null);
    }
  };

  return (
    <div className="bg-white border border-border rounded-xl p-6 mb-6">
      <h2 className="text-foreground font-semibold">
        {namedCompetition
          ? `Enter a project in ${namedCompetition.name}`
          : "Enter a project you've already added"}
      </h2>
      {namedCompetition && (
        <p className="text-muted-foreground text-sm mt-1">
          Deadline {formatDate(namedCompetition.submission_deadline)}
        </p>
      )}

      {error && (
        <p role="alert" className="text-red-600 text-sm mt-3">
          {error}
        </p>
      )}

      <ul className="mt-4 divide-y divide-border">
        {candidates.map(({ project, opportunities }) => (
          <li
            key={project.id}
            className="py-3 flex items-center justify-between gap-3"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                {project.title || "Untitled Project"}
              </p>
              <p className="text-xs text-muted-foreground truncate mt-0.5">
                {opportunities
                  .map((opportunity) => opportunity.competition.name)
                  .join(", ")}
              </p>
            </div>
            {entered[project.id] ? (
              <span className="text-emerald-600 text-sm flex-shrink-0">
                Entered
              </span>
            ) : (
              <button
                onClick={() =>
                  handleEnter(project.id, opportunities[0].competition.id)
                }
                disabled={enteringId !== null}
                className="btn-primary text-sm py-1.5 px-3 flex-shrink-0"
              >
                {enteringId === project.id ? "Entering..." : "Enter"}
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
