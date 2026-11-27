"use client";

import { useTranslations } from "next-intl";

import type { DiscoverTop } from "@/lib/discover-top";
import { CompetitionSlot } from "./CompetitionSlot";
import { DiscoverArticleCard } from "./DiscoverArticleCard";

type Props = Pick<DiscoverTop, "lead" | "second" | "slot">;

// One grid for every width. Side by side, the lead spans the left column with
// the second article above the slot; stacked, CSS `order` moves the slot up
// to sit between the two articles.
export function RecentSection({ lead, second, slot }: Props) {
  const t = useTranslations("projects.recent");
  if (!lead) return null;

  const rightColumnShared = !!second && !!slot;
  // A grid cell stretches to its row, the card inside it does not; this
  // passes the height down so the hairlines under pieces sharing a row land
  // on the same line, with the slack left as page whitespace above the rule.
  const fillCell = "md:[&>article]:h-full";

  return (
    <section aria-labelledby="discover-recent-heading">
      <h2
        id="discover-recent-heading"
        className="mb-4 text-lg font-semibold text-foreground"
      >
        {t("heading")}
      </h2>
      {/* Sharing the right column, the second article keeps its own height
          and the slot takes what the lead leaves over. */}
      <div
        className={`grid grid-cols-1 gap-y-6 md:grid-cols-2 md:gap-x-8 ${rightColumnShared ? "md:grid-rows-[auto_1fr]" : ""}`}
      >
        <div
          data-testid="recent-lead"
          className={`order-1 ${second ? fillCell : ""} ${rightColumnShared ? "md:row-span-2" : ""}`}
        >
          <DiscoverArticleCard article={lead} variant="lead" />
        </div>
        {second && (
          <div
            data-testid="recent-second"
            className={`order-3 md:order-2 ${slot ? "" : fillCell}`}
          >
            <DiscoverArticleCard article={second} variant="grid" />
          </div>
        )}
        {slot && (
          <CompetitionSlot
            slot={slot}
            className={`order-2 md:order-3 ${second ? "" : "md:self-start"}`}
          />
        )}
      </div>
    </section>
  );
}
