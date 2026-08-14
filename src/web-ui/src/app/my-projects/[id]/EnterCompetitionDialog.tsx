"use client";

import { useState } from "react";

import { formatDate } from "@/lib/utils";
import type { CompetitionOpportunity } from "@/lib/api/my-projects";

interface EnterCompetitionDialogProps {
  // Only the eligible ones — a round the project cannot enter has no place in
  // a prompt that exists to offer entry.
  opportunities: CompetitionOpportunity[];
  onEnter: (competitionId: string) => Promise<void>;
  onDismiss: () => void;
}

/**
 * Shown after a successful publish, never before it. Asking beforehand would
 * name rounds the project may turn out not to be able to enter; asking after
 * means the offer is real.
 */
export function EnterCompetitionDialog({
  opportunities,
  onEnter,
  onDismiss,
}: EnterCompetitionDialogProps) {
  const [enteringId, setEnteringId] = useState<string | null>(null);

  if (opportunities.length === 0) return null;

  const handleEnter = async (competitionId: string) => {
    setEnteringId(competitionId);
    try {
      await onEnter(competitionId);
    } finally {
      setEnteringId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="enter-competition-title"
        className="bg-white rounded-xl shadow-xl max-w-md w-full p-6"
      >
        <h2
          id="enter-competition-title"
          className="text-lg font-semibold text-foreground"
        >
          Published. Enter it in a competition?
        </h2>
        <p className="text-sm text-muted-foreground mt-2">
          {opportunities.length === 1
            ? "This round is open to your project right now."
            : "These rounds are open to your project right now."}
        </p>

        <ul className="mt-4 divide-y divide-border">
          {opportunities.map((opportunity) => (
            <li
              key={opportunity.competition.id}
              className="py-3 flex items-center justify-between gap-3"
            >
              <div>
                <p className="text-sm font-medium text-foreground">
                  {opportunity.competition.name}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Deadline{" "}
                  {formatDate(opportunity.competition.submission_deadline)}
                </p>
              </div>
              <button
                onClick={() => handleEnter(opportunity.competition.id)}
                disabled={enteringId !== null}
                className="btn-primary text-sm py-1.5 px-3 flex-shrink-0"
              >
                {enteringId === opportunity.competition.id
                  ? "Entering..."
                  : "Enter"}
              </button>
            </li>
          ))}
        </ul>

        <div className="mt-6 flex justify-end">
          <button
            onClick={onDismiss}
            disabled={enteringId !== null}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Not now
          </button>
        </div>
        <p className="text-xs text-muted-foreground mt-3">
          You can enter from the project&apos;s page at any time while a round
          is open.
        </p>
      </div>
    </div>
  );
}
