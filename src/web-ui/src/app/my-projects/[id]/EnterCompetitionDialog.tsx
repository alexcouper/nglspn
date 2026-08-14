"use client";

import { useState } from "react";

import { Dialog } from "@/components/Dialog";
import { ChoiceList, type Choice } from "@/components/ChoiceList";
import { formatDate } from "@/lib/utils";
import type { CompetitionOpportunity } from "@/lib/api/my-projects";

interface EnterCompetitionDialogProps {
  // Only the eligible ones — a round the project cannot enter has no place in
  // a prompt that exists to offer entry.
  opportunities: CompetitionOpportunity[];
  onEnter: (competitionId: string) => Promise<void>;
  onDismiss: () => void;
}

function toChoice(opportunity: CompetitionOpportunity): Choice {
  return {
    id: opportunity.competition.id,
    title: opportunity.competition.name,
    subtitle: `Deadline ${formatDate(opportunity.competition.submission_deadline)}`,
    imageUrl: opportunity.competition.image_url,
  };
}

/**
 * Shown after a successful publish, never before it. Asking beforehand would
 * name rounds the project may turn out not to be able to enter; asking after
 * means the offer is real.
 *
 * One primary action in the footer rather than a button per row: with a single
 * round open — the common case — a row-level button can never line up with the
 * dismissal, because the dismissal cannot join the list.
 */
export function EnterCompetitionDialog({
  opportunities,
  onEnter,
  onDismiss,
}: EnterCompetitionDialogProps) {
  const [selectedId, setSelectedId] = useState<string | null>(
    opportunities[0]?.competition.id ?? null,
  );
  const [isEntering, setIsEntering] = useState(false);

  if (opportunities.length === 0) return null;

  const handleEnter = async () => {
    if (!selectedId) return;
    setIsEntering(true);
    try {
      await onEnter(selectedId);
    } finally {
      setIsEntering(false);
    }
  };

  return (
    <Dialog
      isOpen
      onClose={onDismiss}
      labelledBy="enter-competition-title"
    >
      <h2
        id="enter-competition-title"
        className="text-base font-semibold text-foreground"
      >
        Published. Enter it in a competition?
      </h2>
      <p className="text-sm text-muted-foreground mt-2 mb-4">
        {opportunities.length === 1
          ? "This round is open to your project right now."
          : "These rounds are open to your project right now."}
      </p>

      <ChoiceList
        name="enter-competition"
        choices={opportunities.map(toChoice)}
        selectedId={selectedId}
        onSelect={setSelectedId}
      />

      <p className="text-xs text-muted-foreground mt-4 mb-5">
        You can enter from the project&apos;s page at any time while a round is
        open.
      </p>

      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={onDismiss}
          disabled={isEntering}
          className="btn-secondary"
        >
          Not now
        </button>
        <button
          type="button"
          onClick={handleEnter}
          disabled={isEntering || selectedId === null}
          className="btn-primary"
        >
          {isEntering ? "Entering..." : "Enter"}
        </button>
      </div>
    </Dialog>
  );
}
