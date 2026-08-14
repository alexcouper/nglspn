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
        setCandidates(eligible);
        setSelectedId(eligible[0]?.id ?? null);
      },
      (err) => {
        if (cancelled) return;
        setHasAnyProject(false);
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
          {hasAnyProject
            ? "None of your projects can enter this round. Anything already in this run of competitions can't enter again."
            : "You haven't added a project yet."}{" "}
          Create a project and you&apos;ll be offered this round when you
          publish it.
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
