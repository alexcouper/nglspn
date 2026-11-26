"use client";

import Link from "next/link";
import type { ArticleListItem } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { ArticleListingImage } from "./ArticleListingImage";

// The fields the card draws. Structural rather than `ArticleListItem` itself
// so a cross-project listing — the profile page's, Discover's — can feed it a
// leaner response that has no visibility fields and only a channel name.
export type ArticleCardItem = Pick<
  ArticleListItem,
  "title" | "summary" | "published_at" | "listing_image_url" | "listing_crop"
> & { channel?: { name: string } | null };

interface Props {
  article: ArticleCardItem;
  // The small label above the headline where the card sits outside its
  // project — on a profile, on Discover: the project's title, or the author's name
  // for an article published under their own name. The project page leaves
  // it out; every card there is the same project.
  flag?: string;
  // A person's channel is a placeholder nobody chose, so a card for an
  // author-owned article leaves it out.
  showChannel?: boolean;
  // Supplied rather than derived from a project slug: a cross-project listing
  // builds its links differently. Omitted where there is nothing to link to —
  // an unpublished draft has no slug, so the authoring preview renders the
  // card inert rather than pointing at /articles/.
  href?: string;
  // `lead` and `grid` are the project page's listing. `row` is a single-column
  // list — image beside the text above `sm`, stacked below — for a list mixing
  // articles with and without images, where a grid of stacked cards leaves
  // holes beside the short ones. `overlay` sets the flag and headline over the
  // image, for a small card beside a lead; without an image it is `grid`.
  variant: "lead" | "grid" | "row" | "overlay";
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

export function ArticleCard({
  article,
  flag,
  showChannel = true,
  href,
  variant: requested,
}: Props) {
  const hasImage = !!article.listing_image_url;
  const variant = requested === "overlay" && !hasImage ? "grid" : requested;
  const isLead = variant === "lead";
  const isRow = variant === "row";
  const shape = hasImage ? "imaged" : "bare";
  const meta = (tone: MetaTone) => (
    <CardMeta
      parts={[flag, showChannel ? article.channel?.name : undefined]}
      publishedAt={article.published_at}
      tone={tone}
    />
  );

  const body = variant === "overlay" ? (
    <div className="relative">
      <ArticleListingImage
        src={article.listing_image_url}
        alt=""
        crop={article.listing_crop}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-[rgba(15,23,42,0.8)] via-[rgba(15,23,42,0.2)] to-transparent" />
      <div
        data-testid="article-card-overlay"
        className="absolute bottom-0 left-0 right-0 p-4"
      >
        {meta("overlay")}
        <h3 className="mt-1 text-base font-semibold text-white line-clamp-2">
          {article.title}
        </h3>
      </div>
    </div>
  ) : (
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
        {meta("light")}
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

type MetaTone = "light" | "overlay";

const META_TONE = {
  light: { label: "text-accent", muted: "text-muted-foreground" },
  overlay: { label: "text-indigo-200", muted: "text-slate-300" },
} as const;

// The line above the headline: flag and channel, then the date.
function CardMeta({
  parts,
  publishedAt,
  tone,
}: {
  parts: (string | undefined)[];
  publishedAt: string | null | undefined;
  tone: MetaTone;
}) {
  const { label, muted } = META_TONE[tone];
  const separator = `${muted} font-normal normal-case tracking-normal`;
  return (
    <div className={`text-xs font-semibold uppercase tracking-wide ${label}`}>
      {parts
        .filter((part): part is string => !!part)
        .map((part, index) => (
          <span key={part}>
            {index > 0 && <span className={separator}>{" · "}</span>}
            {part}
          </span>
        ))}
      {publishedAt && (
        <span className={separator}>
          {" · "}
          {formatDate(publishedAt)}
        </span>
      )}
    </div>
  );
}
