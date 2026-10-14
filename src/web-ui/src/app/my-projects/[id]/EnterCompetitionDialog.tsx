"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

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
  // What the last attempt failed with. The dialog closes itself on success, so
  // anything shown here is a reason the contributor is still looking at it.
  error?: string;
}

type Translate = ReturnType<typeof useTranslations<"competitions.enterCompetitionDialog">>;

function toChoice(opportunity: CompetitionOpportunity, t: Translate): Choice {
  return {
    id: opportunity.competition.id,
    title: opportunity.competition.name,
    subtitle: t("deadline", {
      date: formatDate(opportunity.competition.submission_deadline),
    }),
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
  error,
}: EnterCompetitionDialogProps) {
  const t = useTranslations("competitions.enterCompetitionDialog");
  const [selectedId, setSelectedId] = useState<string | null>(
    opportunities[0]?.competition.id ?? null,
  );
  const [isEntering, setIsEntering] = useState(false);
  // Covers `onEnter` rejecting rather than reporting. Without it a thrown
  // error left the dialog open, idle and silent — indistinguishable from a
  // button that does nothing.
  const [unreportedError, setUnreportedError] = useState("");

  if (opportunities.length === 0) return null;

  const handleEnter = async () => {
    if (!selectedId) return;
    setIsEntering(true);
    setUnreportedError("");
    try {
      await onEnter(selectedId);
    } catch {
      setUnreportedError(t("errors.enterFailed"));
    } finally {
      setIsEntering(false);
    }
  };

  const shownError = error || unreportedError;

  return (
    <Dialog
      isOpen
      onClose={onDismiss}
      labelledBy="enter-competition-title"
    >
      {/* Not "Published": publish() sets PENDING and an admin approves it, so
          saying published at the moment the contributor is paying most
          attention would be a plain untruth. The second line matters as much —
          told only that it will be reviewed, a contributor reasonably assumes
          entering a round has to wait for the verdict. It doesn't. */}
      <h2
        id="enter-competition-title"
        className="text-base font-semibold text-foreground"
      >
        {t("title")}
      </h2>
      <p className="text-sm text-muted-foreground mt-2 mb-4">
        {t("approvalNote", { count: opportunities.length })}
      </p>

      {shownError && (
        <p role="alert" className="text-red-600 text-sm mb-3">
          {shownError}
        </p>
      )}

      <ChoiceList
        name="enter-competition"
        choices={opportunities.map((opportunity) => toChoice(opportunity, t))}
        selectedId={selectedId}
        onSelect={setSelectedId}
      />

      <p className="text-xs text-muted-foreground mt-4 mb-5">
        {t("enterLater")}
      </p>

      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={onDismiss}
          disabled={isEntering}
          className="btn-secondary"
        >
          {t("notNow")}
        </button>
        <button
          type="button"
          onClick={handleEnter}
          disabled={isEntering || selectedId === null}
          className="btn-primary"
        >
          {isEntering ? t("entering") : t("enter")}
        </button>
      </div>
    </Dialog>
  );
}
