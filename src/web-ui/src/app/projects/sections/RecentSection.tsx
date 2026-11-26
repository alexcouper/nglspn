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

  return (
    <section aria-labelledby="discover-recent-heading">
      <h2 id="discover-recent-heading" className="sr-only">
        {t("heading")}
      </h2>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div
          data-testid="recent-lead"
          className={`order-1 ${rightColumnShared ? "md:row-span-2 md:[&>article]:h-full" : ""}`}
        >
          <DiscoverArticleCard article={lead} variant="lead" />
        </div>
        {second && (
          <div data-testid="recent-second" className="order-3 md:order-2">
            {/* Alone in the right column, the overlay card would leave the
                column half empty; the grid card is as tall as the lead. */}
            <DiscoverArticleCard
              article={second}
              variant={slot ? "overlay" : "grid"}
            />
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
