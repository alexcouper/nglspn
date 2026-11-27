"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

import { CompetitionStatusBadge } from "@/components/CompetitionStatusBadge";
import type { CompetitionSlot as Slot } from "@/lib/discover-top";
import { formatKronurAmount } from "@/lib/utils";

interface Props {
  slot: Slot;
  className?: string;
}

// The competition beside Recent, drawn as its state and what a visitor can do
// about it rather than as an article card. Unboxed like the articles around
// it: a hairline underneath, its content at the top, and any height the grid
// gives it left as page whitespace above the rule.
export function CompetitionSlot({ slot, className = "" }: Props) {
  const t = useTranslations("projects.competitionSlot");
  const th = useTranslations("competitions.highlight");
  const { competition } = slot;

  let label: string;
  let headline: string;
  let details: string[];
  let verb: string;
  let imageUrl: string | null | undefined;
  let prize = "";

  switch (slot.state) {
    case "voting":
      label = t("voting.label");
      headline = competition.name;
      details = [
        t("daysLeft", { count: slot.daysLeft }),
        t("entries", { count: competition.project_count }),
      ];
      verb = t("voting.verb");
      imageUrl = competition.image_url;
      break;
    case "accepting": {
      label = t("accepting.label");
      headline = competition.name;
      details = [
        t("daysLeft", { count: slot.daysLeft }),
        t("enteredSoFar", { count: competition.project_count }),
      ];
      verb = t("accepting.verb");
      imageUrl = competition.image_url;
      const amount = formatKronurAmount(competition.prize_amount);
      prize = amount ? th("prize", { amount }) : "";
      break;
    }
    case "closed":
      label = t("closed.label");
      headline = t("closed.wonBy", { project: slot.winner.title });
      details = [competition.name];
      verb = t("closed.verb");
      imageUrl = slot.winner.image_url;
      break;
  }

  return (
    <Link
      href={`/competitions/${competition.slug}`}
      data-testid="competition-slot"
      className={`group flex items-start gap-4 rounded-md border-b border-border pb-5 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent ${className}`}
    >
      {imageUrl && (
        <div className="relative aspect-video w-36 flex-none overflow-hidden rounded-md bg-muted ring-1 ring-black/5 sm:w-56 md:w-44 lg:w-64">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imageUrl}
            alt=""
            loading="lazy"
            className="absolute inset-0 h-full w-full object-cover"
          />
        </div>
      )}
      <div className="min-w-0 flex-1">
        <div>
          <CompetitionStatusBadge
            status={competition.status}
            label={label}
            className="text-xs font-medium px-2.5 py-1"
          />
        </div>
        <h3 className="mt-2 font-semibold text-foreground line-clamp-2 decoration-1 underline-offset-[3px] group-hover:underline">
          {headline}
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">
          {details.join(" · ")}
        </p>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 pt-3">
          <span className="inline-flex items-center rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white transition-colors group-hover:bg-accent-hover">
            {verb}
          </span>
          {prize && (
            <span className="text-sm font-medium text-emerald-600">{prize}</span>
          )}
        </div>
      </div>
    </Link>
  );
}
