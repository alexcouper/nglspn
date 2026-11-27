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
  // holes beside the short ones.
  variant: "lead" | "grid" | "row";
  // `boxed` draws the card as a white bordered box. `ruled` sets it straight
  // on the page with a hairline underneath, newspaper-front style, so a short
  // item next to a tall one leaves page whitespace rather than an empty box.
  frame?: "boxed" | "ruled";
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
  variant,
  frame = "boxed",
}: Props) {
  const isRuled = frame === "ruled";
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
        className={`${isRow ? "sm:w-[220px] sm:flex-none sm:self-stretch" : ""} ${isRuled ? RULED_IMAGE : ""}`}
      />
      <div className={`${textInset(variant, frame, hasImage)} ${isRow ? "min-w-0" : ""}`}>
        {/* An imageless lead card is otherwise a bare block of text at full
            column width, which reads as a card whose image failed to load.
            The rule marks it as a deliberate text-led card; the grid variant
            is small enough not to need one. */}
        {isLead && !hasImage && (
          <div className="mb-3 h-1 w-12 rounded-full bg-accent" />
        )}
        <div className="text-xs font-semibold uppercase tracking-wide text-accent">
          {[
            flag,
            showChannel ? article.channel?.name : undefined,
          ]
            .filter((part): part is string => !!part)
            .map((part, index) => (
              <span key={part}>
                {index > 0 && (
                  <span className="text-muted-foreground font-normal normal-case tracking-normal">
                    {" · "}
                  </span>
                )}
                {part}
              </span>
            ))}
          {article.published_at && (
            <span className="text-muted-foreground font-normal normal-case tracking-normal">
              {" · "}
              {formatDate(article.published_at)}
            </span>
          )}
        </div>
        <h3
          className={`mt-1.5 font-semibold text-foreground ${HEADLINE[variant][shape]} ${
            isRuled && href ? RULED_HOVER : ""
          }`}
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
    <article className={isRuled ? RULED_FRAME : boxedFrame(!!href)}>
      {href ? (
        <Link
          href={href}
          className={`block ${isRuled ? "group rounded-md focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent" : ""}`}
        >
          {body}
        </Link>
      ) : (
        body
      )}
    </article>
  );
}

function boxedFrame(linked: boolean): string {
  return `rounded-lg border border-border bg-white overflow-hidden transition-colors ${
    linked ? "hover:border-accent/50" : ""
  }`;
}

// No box, so nothing to inset the text from: it lines up with the image's
// left edge and the section heading. The hairline sits under the text.
const RULED_FRAME = "border-b border-border pb-5";

// Free-standing on the grey page, a white-edged screenshot would lose its
// edge; a faint ring keeps the picture's outline without reading as a box.
const RULED_IMAGE = "rounded-md ring-1 ring-black/5";

// Unboxed there is no border to recolour, so hover underlines the headline.
const RULED_HOVER =
  "decoration-1 underline-offset-[3px] group-hover:underline";

function textInset(
  variant: Props["variant"],
  frame: NonNullable<Props["frame"]>,
  hasImage: boolean,
): string {
  if (frame === "boxed") return variant === "lead" ? "p-5" : "p-4";
  if (!hasImage) return "";
  if (variant === "row") return "pt-3 sm:pt-0 sm:pl-4";
  return variant === "lead" ? "pt-4" : "pt-3";
}
