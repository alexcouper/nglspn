"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { Dialog } from "@/components/Dialog";
import { ChoiceList, type Choice } from "@/components/ChoiceList";
import { api, type Project } from "@/lib/api";
import { describeApiError } from "@/lib/api/errors";
import { formatDate, pickVariant } from "@/lib/utils";

interface EnterProjectDialogProps {
  competition: { id: string; name: string; submission_deadline: string };
  isOpen: boolean;
  onClose: () => void;
  onEntered: () => void;
}

function isEligibleFor(project: Project, competitionId: string): boolean {
  return (project.competition_standing?.opportunities ?? []).some(
    (opportunity) =>
      opportunity.eligible && opportunity.competition.id === competitionId,
  );
}

function isEnteredIn(project: Project, competitionId: string): boolean {
  return (project.competition_standing?.entries ?? []).some(
    (entry) => entry.competition.id === competitionId,
  );
}

// What the contributor is waiting on. A pending project is *in* the round —
// it appears in the round's list once approved, because that list filters to
// approved. Saying nothing about it read as a refusal.
const STATE_LABELS: Record<string, string> = {
  approved: "Live in the round",
  pending: "Awaiting review",
  rejected: "Not approved",
  ice_box: "On ice",
  draft: "Draft",
};

function stateLabel(project: Project): string {
  return STATE_LABELS[project.status] ?? project.status;
}

function thumbnailFor(project: Project): string | null {
  const images = project.images ?? [];
  const icon = images.find((image) => image.is_icon);
  const main = images.find((image) => image.is_main) ?? images[0];
  const chosen = icon ?? main;
  return chosen ? (pickVariant(chosen.variants, "thumb") ?? chosen.url) : null;
}

function toChoice(project: Project): Choice {
  return {
    id: project.id,
    title: project.title || "Untitled Project",
    subtitle: project.tagline,
    imageUrl: thumbnailFor(project),
  };
}

/**
 * Entering an existing project from the competition itself. The user is already
 * on the round they want; sending them elsewhere to pick a project and back
 * again is two navigations for one POST.
 *
 * Reads the standing `GET /api/my/projects` already carries — no endpoint of
 * its own — and fetches when opened rather than when the page loads, so the
 * many visitors who never press the button pay nothing.
 */
export function EnterProjectDialog({
  competition,
  isOpen,
  onClose,
  onEntered,
}: EnterProjectDialogProps) {
  const [candidates, setCandidates] = useState<Project[] | null>(null);
  const [alreadyIn, setAlreadyIn] = useState<Project[]>([]);
  const [hasAnyProject, setHasAnyProject] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isEntering, setIsEntering] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isOpen) return;

    let cancelled = false;
    setCandidates(null);
    setError("");

    api.myProjects.list().then(
      (all) => {
        if (cancelled) return;
        const eligible = all.filter((project) =>
          isEligibleFor(project, competition.id),
        );
        setHasAnyProject(all.length > 0);
        setAlreadyIn(all.filter((p) => isEnteredIn(p, competition.id)));
        setCandidates(eligible);
        setSelectedId(eligible[0]?.id ?? null);
      },
      (err) => {
        if (cancelled) return;
        setHasAnyProject(false);
        setAlreadyIn([]);
        setCandidates([]);
        setError(describeApiError(err, "Couldn't load your projects."));
      },
    );

    return () => {
      cancelled = true;
    };
  }, [isOpen, competition.id]);

  const handleEnter = async () => {
    if (!selectedId) return;
    setIsEntering(true);
    setError("");
    try {
      await api.myProjects.enterCompetition(selectedId, competition.id);
      onEntered();
    } catch (err) {
      setError(describeApiError(err, "Couldn't enter this project."));
    } finally {
      setIsEntering(false);
    }
  };

  const isLoading = candidates === null;
  const hasCandidates = (candidates?.length ?? 0) > 0;

  return (
    <Dialog isOpen={isOpen} onClose={onClose} labelledBy="enter-project-title">
      <h2
        id="enter-project-title"
        className="text-base font-semibold text-foreground"
      >
        Enter a project in {competition.name}
      </h2>
      <p className="text-sm text-muted-foreground mt-1 mb-4">
        Deadline {formatDate(competition.submission_deadline)}
      </p>

      {error && (
        <p role="alert" className="text-red-600 text-sm mb-3">
          {error}
        </p>
      )}

      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading your projects...</p>
      )}

      {/* Where they already stand, before what they can do about it. Without
          this, a user whose projects are all in the round was told only that
          none of them could enter — true, and read as a rejection. */}
      {!isLoading && alreadyIn.length > 0 && (
        <div className="mb-5">
          <h3 className="text-muted-foreground text-xs font-medium uppercase tracking-wide mb-2">
            Already in this round
          </h3>
          <ul className="divide-y divide-border">
            {alreadyIn.map((project) => (
              <li
                key={project.id}
                className="py-2 flex items-center justify-between gap-3"
              >
                <span className="text-sm text-foreground truncate">
                  {project.title || "Untitled Project"}
                </span>
                <span className="text-xs text-muted-foreground flex-shrink-0">
                  {stateLabel(project)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!isLoading && hasCandidates && (
        <>
          <ChoiceList
            name="enter-project"
            choices={(candidates ?? []).map(toChoice)}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          <p className="text-xs text-muted-foreground mt-4 mb-5">
            Or{" "}
            <Link
              href="/create"
              className="text-accent hover:text-accent-hover transition-colors"
            >
              create a project
            </Link>{" "}
            — you&apos;ll be offered this round when you publish it.
          </p>
        </>
      )}

      {!isLoading && !hasCandidates && (
        <p className="text-sm text-muted-foreground mb-5">
          {alreadyIn.length > 0
            ? "Nothing else of yours can enter this round."
            : hasAnyProject
              ? "None of your projects can enter this round. Anything already in this run of competitions can't enter again."
              : "You haven't added a project yet."}{" "}
          Create a project and you&apos;ll be offered this round when you
          submit it.
        </p>
      )}

      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={onClose}
          disabled={isEntering}
          className="btn-secondary"
        >
          Close
        </button>
        {!isLoading && hasCandidates ? (
          <button
            type="button"
            onClick={handleEnter}
            disabled={isEntering || selectedId === null}
            className="btn-primary"
          >
            {isEntering ? "Entering..." : "Enter"}
          </button>
        ) : (
          !isLoading && (
            <Link href="/create" className="btn-primary">
              Create a project
            </Link>
          )
        )}
      </div>
    </Dialog>
  );
}
