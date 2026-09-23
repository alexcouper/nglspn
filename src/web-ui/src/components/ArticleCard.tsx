"use client";

import Link from "next/link";
import type { ArticleListItem } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { ArticleListingImage } from "./ArticleListingImage";

// The fields the card draws. Structural rather than `ArticleListItem` itself
// so a cross-project listing — the profile page's — can feed it a leaner
// response that has no visibility fields.
export type ArticleCardItem = Pick<
  ArticleListItem,
  "title" | "summary" | "published_at" | "channel" | "listing_image_url" | "listing_crop"
>;

interface Props {
  article: ArticleCardItem;
  // Named where the card sits outside its project — on a profile, a feed. The
  // project page leaves it out; every card there is the same project.
  projectTitle?: string;
  // Supplied rather than derived from a project slug: a cross-project feed
  // builds its links differently. Omitted where there is nothing to link to —
  // an unpublished draft has no slug, so the authoring preview renders the
  // card inert rather than pointing at /articles/.
  href?: string;
  // `lead` and `grid` are the project page's listing. `row` is a single-column
  // list — image beside the text above `sm`, stacked below — for a list mixing
  // articles with and without images, where a grid of stacked cards leaves
  // holes beside the short ones.
  variant: "lead" | "grid" | "row";
}

// An article needs no image. Without one the card draws no placeholder — the
// headline and summary take the space instead, so the clamps open up. A row's
// height is set by its text, so its clamps do not depend on the image.
const HEADLINE = {
  lead: { imaged: "text-2xl line-clamp-3", bare: "text-3xl line-clamp-4" },
  grid: { imaged: "text-base line-clamp-2", bare: "text-base line-clamp-4" },
  row: { imaged: "text-base line-clamp-2", bare: "text-base line-clamp-2" },
} as const;

const SUMMARY = {
  lead: { imaged: "line-clamp-2", bare: "line-clamp-4" },
  grid: { imaged: "line-clamp-3", bare: "line-clamp-5" },
  row: { imaged: "line-clamp-2", bare: "line-clamp-2" },
} as const;

export function ArticleCard({ article, projectTitle, href, variant }: Props) {
  const isLead = variant === "lead";
  const isRow = variant === "row";
  const hasImage = !!article.listing_image_url;
  const shape = hasImage ? "imaged" : "bare";

  const body = (
    <div className={isRow ? "sm:flex sm:items-center" : ""}>
      <ArticleListingImage
        src={article.listing_image_url}
        alt=""
        // Always 16:9, so a grid of cards stays uniform.
        crop={article.listing_crop}
        priority={isLead}
        className={isRow ? "sm:w-[220px] sm:flex-none sm:self-stretch" : ""}
      />
      <div className={`${isLead ? "p-5" : "p-4"} ${isRow ? "min-w-0" : ""}`}>
        {/* An imageless lead card is otherwise a bare block of text at full
            column width, which reads as a card whose image failed to load.
            The rule marks it as a deliberate text-led card; the grid variant
            is small enough not to need one. */}
        {isLead && !hasImage && (
          <div className="mb-3 h-1 w-12 rounded-full bg-accent" />
        )}
        <div className="text-xs font-semibold uppercase tracking-wide text-accent">
          {projectTitle && (
            <>
              {projectTitle}
              <span className="text-muted-foreground font-normal normal-case tracking-normal">
                {" · "}
              </span>
            </>
          )}
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
    </div>
  );

  return (
    <article
      className={`rounded-lg border border-border bg-white overflow-hidden transition-colors ${
        href ? "hover:border-accent/50" : ""
      }`}
    >
      {href ? (
        <Link href={href} className="block">
          {body}
        </Link>
      ) : (
        body
      )}
    </article>
  );
}
