"use client";

import Link from "next/link";
import type { ArticleListItem } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { ArticleListingImage } from "./ArticleListingImage";

interface Props {
  article: ArticleListItem;
  // Supplied rather than derived from a project slug: a cross-project feed
  // builds its links differently.
  href: string;
  variant: "lead" | "grid";
}

// An article needs no image. Without one the card draws no placeholder — the
// headline and summary take the space instead, so the clamps open up.
const HEADLINE = {
  lead: { imaged: "text-2xl line-clamp-3", bare: "text-3xl line-clamp-4" },
  grid: { imaged: "text-base line-clamp-2", bare: "text-base line-clamp-4" },
} as const;

const SUMMARY = {
  lead: { imaged: "line-clamp-2", bare: "line-clamp-4" },
  grid: { imaged: "line-clamp-3", bare: "line-clamp-5" },
} as const;

export function ArticleCard({ article, href, variant }: Props) {
  const isLead = variant === "lead";
  const hasImage = !!article.listing_image_url;
  const shape = hasImage ? "imaged" : "bare";

  return (
    <article className="rounded-lg border border-border bg-white overflow-hidden hover:border-accent/50 transition-colors">
      <Link href={href} className="block">
        <ArticleListingImage
          src={article.listing_image_url}
          alt=""
          // Always 16:9, so a grid of cards stays uniform.
          crop={article.listing_crop}
          priority={isLead}
        />
        <div className={isLead ? "p-5" : "p-4"}>
          {/* An imageless lead card is otherwise a bare block of text at full
              column width, which reads as a card whose image failed to load.
              The rule marks it as a deliberate text-led card; the grid variant
              is small enough not to need one. */}
          {isLead && !hasImage && (
            <div className="mb-3 h-1 w-12 rounded-full bg-accent" />
          )}
          <div className="text-xs font-semibold uppercase tracking-wide text-accent">
            {article.channel.name}
            {article.published_at && (
              <span className="text-muted-foreground font-normal normal-case tracking-normal">
                {" · "}
                {formatDate(article.published_at)}
              </span>
            )}
          </div>
          <h3
            className={`mt-1.5 font-semibold text-foreground ${HEADLINE[variant][shape]}`}
          >
            {article.title}
          </h3>
          {article.summary && (
            <p
              className={`mt-2 text-sm text-muted-foreground ${SUMMARY[variant][shape]}`}
            >
              {article.summary}
            </p>
          )}
        </div>
      </Link>
    </article>
  );
}
